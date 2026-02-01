"""
Decision Engine - Pure function that reads v_selection_state and returns BetFairOrder objects.

This module contains NO side effects - it only transforms data.
All database reads and API calls happen in the executor.
"""

from dataclasses import dataclass

from api_helpers.clients.betfair_client import BetFairOrder, CurrentOrder
from api_helpers.helpers.logging_config import D, I

from .bet_sizer import BetSizing, calculate_sizing
from .models import SelectionState

# Reason that indicates cash out is COMPLETED - skip re-processing
# Note: "Manual Cash Out" is the TRIGGER, "Cashed Out" is the RESULT
CASH_OUT_COMPLETED = "Cashed Out"


def _log_prefix(selection: SelectionState) -> str:
    """Format log prefix with horse name and race time."""
    race_time_str = selection.race_time.strftime("%H:%M")
    return f"[{race_time_str} {selection.horse_name}]"


@dataclass
class OrderWithState:
    """Order paired with its selection state for execution decisions."""

    order: BetFairOrder
    within_stake_limit: bool
    target_stake: float  # Total target stake for this selection


@dataclass
class DecisionResult:
    """Result from the decision engine - orders to place and markets to cash out."""

    orders: list[OrderWithState]
    cash_out_market_ids: list[str]
    invalidations: list[tuple[str, str]]  # (unique_id, reason) for logging/updating


def decide(
    selections: list[SelectionState],
    current_orders: list[CurrentOrder] | None = None,
) -> DecisionResult:
    """
    Pure decision function - takes view data, returns actions.

    Note: current_orders should be empty/minimal after reconciliation cancels
    all executable orders. It's kept as a parameter for safety checks.

    Args:
        selections: List of SelectionState objects from v_selection_state view
        current_orders: Current Betfair orders (should be empty after reconciliation)

    Returns:
        DecisionResult with orders to place, markets to cash out, and invalidation reasons
    """

    orders: list[OrderWithState] = []
    cash_out_market_ids: list[str] = []
    invalidations: list[tuple[str, str]] = []

    for selection in selections:
        unique_id = selection.unique_id

        # PRIORITY 1: Check for voided/invalid selections
        if not selection.valid:
            reason = selection.invalidated_reason or "Manual void"

            if reason != CASH_OUT_COMPLETED:
                # Only log and record first-time invalidations (not already cashed out)
                I(f"{_log_prefix(selection)} Invalid - {reason}")
                invalidations.append((unique_id, reason))

            # If there's matched money, trigger cash out ONCE
            # Skip only if already completed ("Cashed Out")
            if (
                selection.cash_out_requested
                and selection.has_bet
                and selection.total_matched > 0
                and reason != CASH_OUT_COMPLETED
            ):
                I(f"{_log_prefix(selection)} Cash out requested - {reason}")
                cash_out_market_ids.append(selection.market_id)

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

    # Runner has been removed - invalidate and cash out if we have a bet
    if selection.runner_status == "REMOVED":
        reason = "Runner removed from market"
        I(f"{_log_prefix(selection)} {reason}")
        if selection.has_bet:
            return None, selection.market_id, (unique_id, reason)
        return None, None, (unique_id, reason)

    # 8-to-<8 runner rule - PLACE bets invalid when field drops from 8 to fewer
    if selection.place_terms_changed:
        reason = f"8→{selection.current_runners} runners - PLACE bet invalid"
        I(f"{_log_prefix(selection)} {reason}")
        if selection.has_bet:
            return None, selection.market_id, (unique_id, reason)
        return None, None, (unique_id, reason)

    # Short price removal check - any horse <10.0 odds removed from race
    if selection.short_price_removed:
        reason = "Short-priced runner (<10.0) removed from race"
        I(f"{_log_prefix(selection)} {reason}")
        if selection.has_bet:
            return None, selection.market_id, (unique_id, reason)
        return None, None, (unique_id, reason)

    # Check stake limit failsafe
    if not selection.within_stake_limit:
        D(f"[{unique_id}] At stake limit, skipping")
        return None, None, None

    # Use bet_sizer to calculate if we should bet and how much
    sizing: BetSizing = calculate_sizing(selection)

    if not sizing.should_bet:
        D(f"[{unique_id}] {sizing.reason}")
        # Also log at INFO level in verbose mode for debugging
        if sizing.reason:
            I(f"[{unique_id}] Skipping: {sizing.reason}")
        return None, None, None

    # Create order with sizing from bet_sizer
    order: BetFairOrder = _create_order(
        selection, sizing.remaining_stake, sizing.bet_price
    )
    I(f"{_log_prefix(selection)} {sizing.reason}")

    # Wrap with execution state
    order_with_state = OrderWithState(
        order=order,
        within_stake_limit=selection.within_stake_limit,
        target_stake=selection.calculated_stake,
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
