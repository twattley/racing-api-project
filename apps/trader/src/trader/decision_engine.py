"""
Decision Engine - Pure function that reads v_selection_state and returns BetFairOrder objects.

This module contains NO side effects - it only transforms data.
All database reads and API calls happen in the executor.
"""

from dataclasses import dataclass

import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder
from api_helpers.helpers.logging_config import D, I, W

from .bet_sizer import calculate_sizing
from .models import SelectionState


@dataclass
class OrderWithState:
    """Order paired with its selection state for execution decisions."""

    order: BetFairOrder
    use_fill_or_kill: bool
    within_stake_limit: bool


@dataclass
class DecisionResult:
    """Result from the decision engine - orders to place and markets to cash out."""

    orders: list[OrderWithState]
    cash_out_market_ids: list[str]
    invalidations: list[tuple[str, str]]  # (unique_id, reason) for logging/updating


def decide(view_df: pd.DataFrame) -> DecisionResult:
    """
    Pure decision function - takes view data, returns actions.

    Args:
        view_df: DataFrame from v_selection_state view

    Returns:
        DecisionResult with orders to place, markets to cash out, and invalidation reasons
    """
    selections = SelectionState.from_dataframe(view_df)

    orders: list[OrderWithState] = []
    cash_out_market_ids: list[str] = []
    invalidations: list[tuple[str, str]] = []

    for selection in selections:
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

    # Already invalid - skip entirely
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
        W(f"[{unique_id}] FAILSAFE: Exceeded stake limit, skipping")
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


def _create_order(selection: SelectionState, stake: float, price: float) -> BetFairOrder:
    """Create a BetFairOrder from a SelectionState with calculated stake and price."""
    return BetFairOrder(
        size=stake,
        price=price,
        selection_id=str(selection.selection_id),
        market_id=selection.market_id,
        side=selection.selection_type,
        strategy=selection.unique_id,
    )
