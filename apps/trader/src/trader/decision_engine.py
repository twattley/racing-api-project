"""
Decision Engine - Pure function that reads v_selection_state and returns BetFairOrder objects.

This module contains NO side effects - it only transforms data.
All database reads and API calls happen in the executor.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder, CurrentOrder
from api_helpers.helpers.logging_config import D, I, W

from .bet_sizer import calculate_sizing
from .models import SelectionState, SelectionType
from .price_ladder import PriceLadder


@dataclass
class OrderWithState:
    """Order paired with its selection state for execution decisions."""

    order: BetFairOrder
    use_fill_or_kill: bool
    within_stake_limit: bool
    delay_seconds: float = 0.0  # Delay before placing (for early bird scatter)
    is_early_bird: bool = False  # Flag to identify early bird orders


@dataclass
class DecisionResult:
    """Result from the decision engine - orders to place and markets to cash out."""

    orders: list[OrderWithState]
    cash_out_market_ids: list[str]
    invalidations: list[tuple[str, str]]  # (unique_id, reason) for logging/updating
    cancel_orders: list[CurrentOrder] = field(
        default_factory=list
    )  # Early bird orders to cancel


# ============================================================================
# EARLY BIRD CONFIGURATION
# ============================================================================

# Fixed total stake for early bird scatter (not from staking tiers)
# These are deliberately small - markets are thin early, trader tops up later
EARLY_BIRD_BACK_STAKE = 10.0  # Total £10 scattered across tick offsets for BACK
EARLY_BIRD_LAY_LIABILITY = (
    15.0  # Total £15 LIABILITY scattered for LAY (stake calculated from odds)
)

# Tick offsets: where to place orders relative to requested price
# BACK: positive = higher prices (better for us - we get paid more if matched)
# LAY: negative = lower prices (better for us - less liability if matched)
BACK_TICK_OFFSETS = [2, 3, 4, 5]
LAY_TICK_OFFSETS = [
    -2,
    -3,
    -4,
    -5,
]  # Negative ticks BELOW lay price (lower = less liability)

# Delay range between orders (seconds) - randomised to avoid pattern detection
EARLY_BIRD_DELAY_MIN = 1.5
EARLY_BIRD_DELAY_MAX = 4.0

# Minimum stake per order - Betfair allows down to £0.10 for subsequent bets
# Keep low to allow liability-based LAY orders through (stake = liability / (odds-1))
MIN_STAKE_PER_ORDER = 0.50


def decide(
    selections: list[SelectionState],
    current_orders: list[CurrentOrder] | None = None,
) -> DecisionResult:
    """
    Pure decision function - takes view data, returns actions.

    Splits selections by time:
    - > 2 hours to race: Early bird mode (scatter orders at offset prices)
    - <= 2 hours to race: Normal trading mode (cancel early birds, trade at market)

    Args:
        view_df: DataFrame from v_selection_state view
        current_orders: Current Betfair orders (for early bird duplicate detection)

    Returns:
        DecisionResult with orders to place, markets to cash out, and invalidation reasons
    """

    orders: list[OrderWithState] = []
    cash_out_market_ids: list[str] = []
    invalidations: list[tuple[str, str]] = []
    cancel_orders_list: list[CurrentOrder] = []

    for selection in selections:
        unique_id = selection.unique_id

        # PRIORITY 1: Check for voided/invalid selections - cancel any pending orders
        # This handles manual voids from the frontend during early bird window
        if not selection.valid:
            reason = selection.invalidated_reason or "Manual void"

            # Check if there are early bird orders to cancel
            eb_cancels: list[CurrentOrder] = _get_early_bird_orders_to_cancel(
                selection, current_orders
            )
            if eb_cancels:
                cancel_orders_list.extend(eb_cancels)
                I(
                    f"[{unique_id}] Voided - cancelling {len(eb_cancels)} early bird orders"
                )
                invalidations.append((unique_id, reason))

            # If there's matched money, also trigger cash out
            if (
                selection.cash_out_requested
                and selection.has_bet
                and selection.total_matched > 0
            ):
                I(f"[{unique_id}] Cash out requested - {reason}")
                cash_out_market_ids.append(selection.market_id)

            continue

        # Check time window first
        now = datetime.now(selection.expires_at.tzinfo)
        in_early_bird_window = (
            now < selection.expires_at
        )  # Before cutoff (race_time - 2h)

        if in_early_bird_window:
            # Early bird time window (>2h to race)
            if _should_place_early_bird(selection, current_orders):
                # Place new early bird orders
                eb_orders = _decide_early_bird(selection)
                orders.extend(eb_orders)
            # Otherwise: eb orders already exist - do nothing, let them sit
            continue

        # Normal trading mode (<=2 hours)
        # First, check if we need to cancel early bird orders for this selection
        eb_cancels = _get_early_bird_orders_to_cancel(selection, current_orders)
        if eb_cancels:
            cancel_orders_list.extend(eb_cancels)
            I(
                f"[{selection.unique_id}] Cancelling {len(eb_cancels)} early bird orders for normal trading"
            )
            # Skip normal decision this cycle - let cancellation happen first
            continue

        # Normal trading decision
        order_with_state, cash_out, invalidation = _decide_selection(selection)

        if order_with_state:
            orders.append(order_with_state)
        if cash_out:
            cash_out_market_ids.append(cash_out)
        if invalidation:
            invalidations.append(invalidation)

    # Deduplicate market IDs for cash out
    return DecisionResult(
        orders=orders,
        cash_out_market_ids=list(set(cash_out_market_ids)),
        invalidations=invalidations,
        cancel_orders=cancel_orders_list,
    )


def _decide_selection(
    selection: SelectionState,
) -> tuple[OrderWithState | None, str | None, tuple[str, str] | None]:
    """
    Decide what to do for a single selection.

    Returns:
        Tuple of (order_with_state, market_id_to_cash_out, invalidation_tuple)
    """
    unique_id = selection.unique_id

    # Already invalid - skip (cash out requests handled at top of decide() loop)
    if not selection.valid:
        D(f"[{unique_id}] Already invalid: {selection.invalidated_reason or 'unknown'}")
        return None, None, None

    # Already fully matched - nothing to do
    if selection.fully_matched:
        D(f"[{unique_id}] Already fully matched")
        return None, None, None

    # Runner has been removed - invalidate and cash out if we have a bet
    if selection.runner_status == "REMOVED":
        reason = "Runner removed from market"
        I(f"[{unique_id}] {reason}")
        if selection.has_bet:
            return None, selection.market_id, (unique_id, reason)
        return None, None, (unique_id, reason)

    # 8-to-<8 runner rule - PLACE bets invalid when field drops from 8 to fewer
    if selection.place_terms_changed:
        reason = f"8→{selection.current_runners} runners - PLACE bet invalid"
        I(f"[{unique_id}] {reason}")
        if selection.has_bet:
            return None, selection.market_id, (unique_id, reason)
        return None, None, (unique_id, reason)

    # Short price removal check - any horse <10.0 odds removed from race
    if selection.short_price_removed:
        reason = "Short-priced runner (<10.0) removed from race"
        I(f"[{unique_id}] {reason}")
        if selection.has_bet:
            return None, selection.market_id, (unique_id, reason)
        return None, None, (unique_id, reason)

    # Check stake limit failsafe
    if not selection.within_stake_limit:
        D(f"[{unique_id}] At stake limit, skipping")
        return None, None, None

    # Use bet_sizer to calculate if we should bet and how much
    sizing = calculate_sizing(selection)

    if not sizing.should_bet:
        D(f"[{unique_id}] {sizing.reason}")
        return None, None, None

    # Create order with sizing from bet_sizer
    order = _create_order(selection, sizing.remaining_stake, sizing.bet_price)
    I(f"[{unique_id}] {sizing.reason}")

    # Wrap with execution state
    order_with_state = OrderWithState(
        order=order,
        use_fill_or_kill=selection.use_fill_or_kill,
        within_stake_limit=selection.within_stake_limit,
    )
    return order_with_state, None, None


def _create_order(
    selection: SelectionState, stake: float, price: float
) -> BetFairOrder:
    """Create a BetFairOrder from a SelectionState with calculated stake and price."""
    return BetFairOrder(
        size=stake,
        price=price,
        selection_id=str(selection.selection_id),
        market_id=selection.market_id,
        side=selection.selection_type,
        strategy=selection.unique_id,
    )


# ============================================================================
# EARLY BIRD - "Spray and Pray" scatter orders at offset prices
# ============================================================================


def _should_place_early_bird(
    selection: SelectionState,
    current_orders: list[CurrentOrder] | None,
) -> bool:
    """
    Check if we should PLACE early bird orders for this selection.

    Called only when we're in the early bird time window (>2h to race).
    Returns True if we should place new scatter orders.
    Returns False if orders already exist or selection is invalid.
    """
    unique_id = selection.unique_id

    # Basic validation
    if not selection.valid:
        return False

    if selection.fully_matched:
        return False

    # Don't scatter if we already have matched bets (top-up uses normal mode)
    if selection.has_bet:
        D(f"[{unique_id}] Already has bet - skipping early bird")
        return False

    # Check if early bird orders already placed (fire once only)
    if current_orders:
        eb_prefix = f"{unique_id}_eb"
        for order in current_orders:
            if order.customer_strategy_ref and order.customer_strategy_ref.startswith(
                eb_prefix
            ):
                D(f"[{unique_id}] Early bird orders already placed - letting them sit")
                return False

    I(
        f"[{unique_id}] 🐦 EARLY BIRD eligible - {selection.minutes_to_race:.0f}m to race"
    )
    return True


def _get_early_bird_orders_to_cancel(
    selection: SelectionState,
    current_orders: list[CurrentOrder] | None,
) -> list[CurrentOrder]:
    """
    Find early bird orders that need to be cancelled for normal trading.

    Called when selection is within 2 hours of race start.
    Returns list of early bird orders (those with _eb suffix) to cancel.
    """
    if not current_orders:
        return []

    unique_id = selection.unique_id
    eb_prefix = f"{unique_id}_eb"

    return [
        order
        for order in current_orders
        if order.customer_strategy_ref
        and order.customer_strategy_ref.startswith(eb_prefix)
        and order.execution_status == "EXECUTABLE"  # Only cancel live orders
    ]


def _decide_early_bird(selection: SelectionState) -> list[OrderWithState]:
    """
    Generate early bird scatter orders with random stake splits and delays.

    Places orders at offset prices (2, 3, 4, 5 ticks ABOVE the requested price).
    We use requested_odds (not current market) because that's where we've
    determined there's value - anything above that is even better.

    Stakes are randomly split to avoid pattern detection.
    Orders have staggered delays between placements.
    """
    ladder = PriceLadder()
    unique_id = selection.unique_id

    # Base price: use the BETTER of requested vs current market price
    # For BACK: higher is better (MAX) - if market is 3.6 and we wanted 3.0, use 3.6
    # For LAY: lower is better (MIN) - if market is 2.8 and we wanted 3.0, use 2.8
    # Then scatter from there to potentially get even better odds
    if selection.selection_type == SelectionType.BACK:
        current_price = selection.current_back_price
        if current_price and current_price > selection.requested_odds:
            base_price = current_price
            I(
                f"[{selection.unique_id}] 🐦 Market already better ({current_price}) than requested ({selection.requested_odds}), using market price"
            )
        else:
            base_price = selection.requested_odds
    else:
        current_price = selection.current_lay_price
        if current_price and current_price < selection.requested_odds:
            base_price = current_price
            I(
                f"[{selection.unique_id}] 🐦 Market already better ({current_price}) than requested ({selection.requested_odds}), using market price"
            )
        else:
            base_price = selection.requested_odds

    # Use hardcoded stakes - markets are thin early, trader tops up later
    if selection.selection_type == SelectionType.BACK:
        tick_offsets = BACK_TICK_OFFSETS
        target_amount = EARLY_BIRD_BACK_STAKE  # This IS the stake for BACK
        is_liability = False
    else:
        tick_offsets = LAY_TICK_OFFSETS
        target_amount = (
            EARLY_BIRD_LAY_LIABILITY  # This is LIABILITY for LAY (not stake)
        )
        is_liability = True

    if target_amount < MIN_STAKE_PER_ORDER:
        I(f"[{unique_id}] 🐦 Amount too small for early bird: £{target_amount:.2f}")
        return []

    # Random split of amount across tick offsets
    # For LAY, this splits the LIABILITY; we'll convert to stake per-order below
    amounts: list[int | float] = _random_stake_split(
        target_amount, len(tick_offsets), MIN_STAKE_PER_ORDER
    )

    I(
        f"[{unique_id}] 🐦 EARLY BIRD: {selection.selection_type.value} @ base {base_price} (requested {selection.requested_odds}), "
        f"scatter £{target_amount:.2f} {'liability' if is_liability else 'stake'} as {[f'£{s:.2f}' for s in amounts]}"
    )

    orders: list[OrderWithState] = []
    cumulative_delay = 0.0

    for offset, amount in zip(tick_offsets, amounts):
        # Calculate target price (ticks away from base - negative for LAY, positive for BACK)
        target_price = ladder.ticks_away(base_price, offset)

        if target_price is None:
            D(f"[{unique_id}] 🐦 Offset {offset} outside ladder range")
            continue

        # For LAY: convert liability to stake
        # Liability = stake × (odds - 1), so stake = liability / (odds - 1)
        if is_liability:
            stake = amount / (target_price - 1)
        else:
            stake = amount

        if stake < MIN_STAKE_PER_ORDER:
            D(
                f"[{unique_id}] 🐦 Skipping offset {offset} - stake £{stake:.2f} too small"
            )
            continue

        # Random delay before this order
        delay = random.uniform(EARLY_BIRD_DELAY_MIN, EARLY_BIRD_DELAY_MAX)
        cumulative_delay += delay

        # Create order with unique strategy ref for tracking
        # Use absolute offset value to stay within 15 char Betfair limit
        order = BetFairOrder(
            size=round(stake, 2),
            price=target_price,
            selection_id=str(selection.selection_id),
            market_id=selection.market_id,
            side=selection.selection_type.value,
            strategy=f"{unique_id}_eb{abs(offset)}",
        )

        orders.append(
            OrderWithState(
                order=order,
                use_fill_or_kill=False,  # Early bird sits and waits
                within_stake_limit=True,
                delay_seconds=cumulative_delay,
                is_early_bird=True,
            )
        )

        liability_info = f" (liability £{amount:.2f})" if is_liability else ""
        I(
            f"[{unique_id}] 🐦   → £{stake:.2f} @ {target_price}{liability_info} "
            f"({offset} ticks, delay {cumulative_delay:.1f}s)"
        )

    return orders


def _random_stake_split(
    total: float,
    n_parts: int,
    min_stake: float = MIN_STAKE_PER_ORDER,
) -> list[float]:
    """
    Split total stake into n random parts.

    Each part is at least min_stake (if possible).
    Randomised to avoid pattern detection in the market.

    Example: £10 split 4 ways might give [3.20, 2.80, 2.10, 1.90]
    """
    if total < min_stake:
        return [total]

    # Calculate how many parts we can afford
    max_parts = int(total / min_stake)
    n_parts = min(n_parts, max_parts)

    if n_parts <= 1:
        return [total]

    # Generate random proportions
    proportions = [
        random.random() + 0.5 for _ in range(n_parts)
    ]  # 0.5-1.5 range for less variance
    total_prop = sum(proportions)

    # Scale to target total
    stakes = [(p / total_prop) * total for p in proportions]

    # Round to 2 decimal places
    stakes = [round(s, 2) for s in stakes]

    # Adjust last one to ensure sum equals total (handle rounding errors)
    stakes[-1] = round(total - sum(stakes[:-1]), 2)

    # Shuffle so we don't always have the adjustment at the end
    random.shuffle(stakes)

    return stakes
