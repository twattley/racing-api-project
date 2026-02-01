"""
Executor - Execute trading decisions.

This module handles the actual execution of orders:
1. Place orders at market
2. Handle existing orders (skip if one exists, replace if better price)
3. Cash out invalidated bets
4. Record invalidations

Order cleanup (cancelling stale orders) is handled separately by order_cleanup module.
Reconciliation (syncing completed orders to bet_log) is handled by reconciliation module.
"""

from dataclasses import dataclass

import pandas as pd
from api_helpers.clients.betfair_client import (
    BetFairClient,
    BetFairOrder,
    CurrentOrder,
    OrderResult,
)
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import D, E, I, W

from .bet_store import (
    find_order_for_selection,
    cancel_order,
)
from .decision_engine import DecisionResult, OrderWithState
from .models import SelectionState, SelectionType
from .reconciliation import (
    get_matched_total_from_log,
    upsert_completed_order,
)


@dataclass
class ExecutionSummary:
    """Summary of execution actions taken."""

    orders_placed: int = 0
    orders_matched: int = 0
    orders_failed: int = 0
    orders_skipped: int = 0
    orders_cancelled: int = 0
    cash_outs: int = 0
    invalidations: int = 0

    @property
    def has_activity(self) -> bool:
        """Return True if any meaningful activity occurred (excluding skips)."""
        return (
            self.orders_placed > 0
            or self.orders_matched > 0
            or self.orders_failed > 0
            or self.orders_cancelled > 0
            or self.cash_outs > 0
            or self.invalidations > 0
        )

    def __str__(self) -> str:
        """Human-readable summary."""
        parts = []
        if self.orders_placed:
            parts.append(f"placed={self.orders_placed}")
        if self.orders_matched:
            parts.append(f"matched={self.orders_matched}")
        if self.orders_failed:
            parts.append(f"failed={self.orders_failed}")
        if self.orders_skipped:
            parts.append(f"skipped={self.orders_skipped}")
        if self.orders_cancelled:
            parts.append(f"cancelled={self.orders_cancelled}")
        if self.cash_outs:
            parts.append(f"cash_outs={self.cash_outs}")
        if self.invalidations:
            parts.append(f"invalidations={self.invalidations}")
        return f"ExecutionSummary({', '.join(parts) or 'no activity'})"


def execute(
    decision: DecisionResult,
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> ExecutionSummary:
    """
    Execute the decisions from the decision engine.

    Args:
        decision: DecisionResult from decide()
        betfair_client: Betfair API client
        postgres_client: Database client

    Returns:
        ExecutionSummary with counts of actions taken
    """
    summary = ExecutionSummary()

    current_orders: list[CurrentOrder] = betfair_client.get_current_orders()

    # 1. Place new orders
    for order_with_state in decision.orders:
        result: OrderResult | str | None = _place_order(
            order_with_state, current_orders, betfair_client, postgres_client
        )
        if result is None:
            summary.orders_skipped += 1
        elif result == "cancelled":
            summary.orders_cancelled += 1
        elif result.success:
            summary.orders_placed += 1
            if result.size_matched and result.size_matched > 0:
                summary.orders_matched += 1
        else:
            summary.orders_failed += 1

    # 2. Cancel orders (for voided selections)
    if decision.cancel_orders:
        I(f"Cancelling {len(decision.cancel_orders)} orders")
        for order in decision.cancel_orders:
            if cancel_order(betfair_client, order):
                summary.orders_cancelled += 1

    # 3. Cash out invalidated bets
    if decision.cash_out_market_ids:
        I(f"Cashing out {len(decision.cash_out_market_ids)} markets")
        try:
            betfair_client.cash_out_bets(market_ids=decision.cash_out_market_ids)
            summary.cash_outs = len(decision.cash_out_market_ids)
        except Exception as e:
            E(f"Error cashing out markets: {e}")

    # 4. Record invalidations in database
    for unique_id, reason in decision.invalidations:
        # If this was a manual cash out, mark it as completed so we don't retry
        if reason == "Manual Cash Out":
            reason = "Cashed Out"
        _record_invalidation(unique_id, reason, postgres_client)
        summary.invalidations += 1

    if summary.has_activity:
        I(f"Execution: {summary}")

    return summary


def _place_order(
    order_with_state: OrderWithState,
    current_orders: list[CurrentOrder],
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> OrderResult | str | None:
    """
    Place a single order, handling existing orders.

    Returns:
        - OrderResult if order was placed
        - "cancelled" if existing order was cancelled for better price (will retry next loop)
        - None if skipped (active order exists)
    """
    order: BetFairOrder = order_with_state.order
    unique_id: str = order.strategy

    if not unique_id:
        W(f"Order missing strategy/unique_id: {order}")
        return OrderResult(success=False, message="Missing unique_id")

    # Find any existing EXECUTABLE order for this selection
    existing_order: CurrentOrder | None = find_order_for_selection(
        current_orders, unique_id
    )

    # If order is complete, treat as no active order - we may need more stake
    if existing_order and existing_order.execution_status == "EXECUTION_COMPLETE":
        existing_order = None

    if existing_order:
        # Check if new order has a better price - if so, cancel and replace
        # BACK: lower price is better (we pay less for same odds)
        # LAY: higher price is better (we accept worse odds = less liability)
        existing_price: int | float = existing_order.price
        new_price: int | float = order.price
        should_replace = False

        if (order.side == SelectionType.BACK) and (new_price < existing_price):
            I(
                f"[{unique_id}] Better BACK price available: {existing_price} → {new_price}, replacing"
            )
            should_replace = True
        elif (order.side == SelectionType.LAY) and (new_price > existing_price):
            I(
                f"[{unique_id}] Better LAY price available: {existing_price} → {new_price}, replacing"
            )
            should_replace = True

        if should_replace:
            # Log any matched portion before cancelling
            if existing_order.size_matched > 0:
                upsert_completed_order(existing_order, postgres_client)
            cancel_order(betfair_client, existing_order)
            return "cancelled"
        else:
            # Price not better - wait for existing order to match
            D(
                f"[{unique_id}] Active order exists at {existing_price}, waiting for match"
            )
            return None

    # No existing order - verify against bet_log before placing (source of truth)
    matched_in_log = get_matched_total_from_log(postgres_client, unique_id)
    target_stake = order_with_state.target_stake

    # Calculate remaining based on what's actually in bet_log
    remaining_stake = target_stake - matched_in_log

    I(
        f"[{unique_id}] Target: {target_stake}, Matched in log: {matched_in_log}, Remaining: {remaining_stake}"
    )

    if remaining_stake <= 0:
        I(f"[{unique_id}] Already fully staked ({matched_in_log} matched in bet_log)")
        return None

    # Use the smaller of: what decision engine calculated OR what we actually need
    actual_stake = min(order.size, remaining_stake)

    if actual_stake < order.size:
        I(
            f"[{unique_id}] Adjusting stake: {order.size} → {actual_stake} (bet_log shows {matched_in_log})"
        )
        order = BetFairOrder(
            size=actual_stake,
            price=order.price,
            selection_id=order.selection_id,
            market_id=order.market_id,
            side=order.side,
            strategy=order.strategy,
        )

    # Place the order
    I(f"[{unique_id}] Placing {order.side} order: {order.size} @ {order.price}")
    result = betfair_client.place_order(order)

    if not result.success:
        E(f"[{unique_id}] Order failed: {result.message}")

    return result


def _record_invalidation(
    unique_id: str,
    reason: str,
    postgres_client: PostgresClient,
) -> None:
    """Update the selections table to mark a selection as invalid or update the reason."""
    query = """
        UPDATE live_betting.selections 
        SET valid = FALSE,
            invalidated_at = COALESCE(invalidated_at, NOW()),
            invalidated_reason = :reason
        WHERE unique_id = :unique_id
    """
    try:
        postgres_client.execute_query(
            query,
            {"unique_id": unique_id, "reason": reason},
        )
        I(f"[{unique_id}] Marked invalid: {reason}")
    except Exception as e:
        E(f"[{unique_id}] Failed to record invalidation: {e}")


def fetch_selection_state(postgres_client: PostgresClient) -> list[SelectionState]:
    """
    Fetch the current state of all selections from v_selection_state.
    """
    query = """
        SELECT * 
        FROM live_betting.v_selection_state 
        WHERE race_time::date = current_date
        """
    data: pd.DataFrame = postgres_client.fetch_data(query)

    return SelectionState.from_dataframe(df=data)
