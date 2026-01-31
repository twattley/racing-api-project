"""
Decision Engine - Pure function that reads v_selection_state and returns BetFairOrder objects.

This module contains NO side effects - it only transforms data.
All database reads and API calls happen in the executor.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder, CurrentOrder
from api_helpers.helpers.logging_config import D, I, W

from .bet_sizer import calculate_sizing, BetSizing
from .models import SelectionState, SelectionType

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
    use_fill_or_kill: bool
    within_stake_limit: bool
    target_stake: float  # Total target stake for this selection


@dataclass
class DecisionResult:
    """Result from the decision engine - orders to place and markets to cash out."""

    orders: list[OrderWithState]
    cash_out_market_ids: list[str]
    invalidations: list[tuple[str, str]]  # (unique_id, reason) for logging/updating
    cancel_orders: list[CurrentOrder] = field(
        default_factory=list
    )  # Orders to cancel (e.g., voided selections)


def decide(
    selections: list[SelectionState],
    current_orders: list[CurrentOrder] | None = None,
) -> DecisionResult:
    """
    Pure decision function - takes view data, returns actions.

    Args:
        selections: List of SelectionState objects from v_selection_state view
        current_orders: Current Betfair orders (for duplicate detection)

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
        if not selection.valid:
            reason = selection.invalidated_reason or "Manual void"

            # Check if there are orders to cancel on this selection
            orders_to_cancel: list[CurrentOrder] = _get_orders_to_cancel(
                selection, current_orders
            )
            if orders_to_cancel:
                cancel_orders_list.extend(orders_to_cancel)
                I(
                    f"{_log_prefix(selection)} Voided - cancelling {len(orders_to_cancel)} orders"
                )
                invalidations.append((unique_id, reason))
            elif reason != CASH_OUT_COMPLETED:
                # Only log and record first-time invalidations (not already cashed out)
                I(f"{_log_prefix(selection)} Invalid - {reason}")
                invalidations.append((unique_id, reason))
            # else: Already cashed out - skip silently

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

        # Check if there's already an order on Betfair for this selection
        if _has_existing_order(selection, current_orders):
            I(f"{_log_prefix(selection)} Order already on Betfair, skipping")
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

    # Skip if there's already a pending order on Betfair
    if selection.has_pending_order:
        D(f"[{unique_id}] Pending order exists, waiting for it to match/expire")
        return None, None, None

    # Use bet_sizer to calculate if we should bet and how much
    sizing: BetSizing = calculate_sizing(selection)

    if not sizing.should_bet:
        D(f"[{unique_id}] {sizing.reason}")
        return None, None, None

    # Create order with sizing from bet_sizer
    order: BetFairOrder = _create_order(
        selection, sizing.remaining_stake, sizing.bet_price
    )
    I(f"{_log_prefix(selection)} {sizing.reason}")

    # Wrap with execution state
    order_with_state = OrderWithState(
        order=order,
        use_fill_or_kill=selection.use_fill_or_kill,
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


def _has_existing_order(
    selection: SelectionState,
    current_orders: list[CurrentOrder] | None,
) -> bool:
    """
    Check if there's already an executable order on Betfair for this selection.

    Used to avoid placing duplicate orders.
    """
    if not current_orders:
        return False

    unique_id = selection.unique_id
    market_id = selection.market_id
    selection_id = str(selection.selection_id)

    for order in current_orders:
        if order.execution_status != "EXECUTABLE":
            continue

        # Match by strategy ref (our unique_id)
        if order.customer_strategy_ref == unique_id:
            return True

        # Also match by market_id + selection_id as fallback
        if order.market_id == market_id and str(order.selection_id) == selection_id:
            return True

    return False


def _get_orders_to_cancel(
    selection: SelectionState,
    current_orders: list[CurrentOrder] | None,
) -> list[CurrentOrder]:
    """
    Find orders that need to be cancelled for a voided selection.

    Returns list of orders to cancel.
    """
    if not current_orders:
        return []

    unique_id = selection.unique_id
    market_id = selection.market_id
    selection_id = str(selection.selection_id)

    orders_to_cancel = []
    for order in current_orders:
        if order.execution_status != "EXECUTABLE":
            continue  # Only cancel live orders

        # Match by strategy ref
        if order.customer_strategy_ref == unique_id:
            orders_to_cancel.append(order)
            continue

        # Also match by market_id + selection_id for any orders on this selection
        if (
            not selection.valid
            and order.market_id == market_id
            and str(order.selection_id) == selection_id
        ):
            I(
                f"[{unique_id}] Found order to cancel by market/selection: {order.customer_strategy_ref}"
            )
            orders_to_cancel.append(order)

    return orders_to_cancel
