"""
Executor - Execute trading decisions.

This module handles the actual execution of orders:
1. Early bird orders (scatter at better prices when race is far away)
2. Normal orders (place at market when race is closer)
3. Handle existing/stale orders
4. Cash out invalidated bets
5. Record invalidations

Reconciliation (syncing completed orders to bet_log) is handled
separately by the reconciliation module.
"""

import time

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
    is_order_stale,
    cancel_order,
    calculate_remaining_stake,
    ORDER_TIMEOUT_MINUTES,
)
from .decision_engine import DecisionResult, OrderWithState
from .models import SelectionState
from .reconciliation import (
    get_matched_total_from_log,
    upsert_completed_order,
)


def execute(
    decision: DecisionResult,
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> dict:
    """
    Execute the decisions from the decision engine.

    Args:
        decision: DecisionResult from decide()
        betfair_client: Betfair API client
        postgres_client: Database client

    Returns:
        Summary dict with counts of actions taken
    """
    summary = {
        "orders_placed": 0,
        "orders_matched": 0,
        "orders_failed": 0,
        "orders_skipped": 0,
        "orders_cancelled": 0,
        "early_bird_placed": 0,
        "early_bird_cancelled": 0,
        "cash_outs": 0,
        "invalidations": 0,
    }

    current_orders = betfair_client.get_current_orders()

    # 1. Place new orders (respecting delays for early bird)
    last_delay = 0.0
    for order_with_state in decision.orders:
        # Handle staggered delays for early bird orders
        if order_with_state.delay_seconds > last_delay:
            sleep_time = order_with_state.delay_seconds - last_delay
            I(f"🐦 Sleeping {sleep_time:.1f}s before next early bird order...")
            time.sleep(sleep_time)
            last_delay = order_with_state.delay_seconds

        result = _place_order(
            order_with_state, current_orders, betfair_client, postgres_client
        )
        if result is None:
            summary["orders_skipped"] += 1
        elif result == "cancelled":
            summary["orders_cancelled"] += 1
        elif result.success:
            if order_with_state.is_early_bird:
                summary["early_bird_placed"] += 1
            else:
                summary["orders_placed"] += 1
            if result.size_matched and result.size_matched > 0:
                summary["orders_matched"] += 1
        else:
            summary["orders_failed"] += 1

    # 2. Cancel early bird orders (when transitioning to normal trading)
    if decision.cancel_orders:
        I(f"Cancelling {len(decision.cancel_orders)} early bird orders")
        for order in decision.cancel_orders:
            if cancel_order(betfair_client, order):
                summary["early_bird_cancelled"] += 1

    # 3. Cash out invalidated bets
    if decision.cash_out_market_ids:
        I(f"Cashing out {len(decision.cash_out_market_ids)} markets")
        try:
            betfair_client.cash_out_bets(decision.cash_out_market_ids)
            summary["cash_outs"] = len(decision.cash_out_market_ids)
        except Exception as e:
            E(f"Error cashing out markets: {e}")

    # 4. Record invalidations in database
    for unique_id, reason in decision.invalidations:
        _record_invalidation(unique_id, reason, postgres_client)
        summary["invalidations"] += 1

    if any(v > 0 for k, v in summary.items() if k != "orders_skipped"):
        I(f"Execution summary: {summary}")

    return summary


def _place_order(
    order_with_state: OrderWithState,
    current_orders: list[CurrentOrder],
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> OrderResult | str | None:
    """
    Place a single order, handling existing orders and staleness.

    Returns:
        - OrderResult if order was placed
        - "cancelled" if stale order was cancelled (will retry next loop)
        - None if skipped (active order exists)
    """
    order = order_with_state.order
    unique_id = order.strategy

    if not unique_id:
        W(f"Order missing strategy/unique_id: {order}")
        return OrderResult(success=False, message="Missing unique_id")

    # Find any existing order for this selection
    existing_order = find_order_for_selection(current_orders, unique_id)

    if existing_order:
        if existing_order.execution_status == "EXECUTION_COMPLETE":
            # Already done - shouldn't happen often, reconciliation handles this
            D(f"[{unique_id}] Order already complete")
            return None

        # EXECUTABLE order exists
        if is_order_stale(existing_order):
            # Stale - cancel it
            I(f"[{unique_id}] Order stale (>{ORDER_TIMEOUT_MINUTES} mins), cancelling")

            # Log any matched portion before cancelling (upsert to bet_log)
            if existing_order.size_matched > 0:
                upsert_completed_order(existing_order, postgres_client)

            cancel_order(betfair_client, existing_order)
            # Return special value - next loop will pick up and place new order
            return "cancelled"
        else:
            # Not stale - wait for it
            D(f"[{unique_id}] Active order exists, waiting for match")
            return None

    # No existing order - calculate how much we need
    matched_in_log = get_matched_total_from_log(postgres_client, unique_id)
    remaining_stake = calculate_remaining_stake(
        target_stake=order.size,
        current_order=None,  # No current order
        matched_in_log=matched_in_log,
    )

    if remaining_stake <= 0:
        D(f"[{unique_id}] Already fully staked ({matched_in_log} matched)")
        return None

    # Adjust order size if we only need partial
    if remaining_stake < order.size:
        I(
            f"[{unique_id}] Adjusting stake: {order.size} → {remaining_stake} (already have {matched_in_log})"
        )
        order = BetFairOrder(
            size=remaining_stake,
            price=order.price,
            selection_id=order.selection_id,
            market_id=order.market_id,
            side=order.side,
            strategy=order.strategy,
        )

    # Place the order - use fill-or-kill if flagged (< 2 mins to race)
    if order_with_state.use_fill_or_kill:
        I(
            f"[{unique_id}] Placing FILL-OR-KILL {order.side} order: {order.size} @ {order.price}"
        )
        result = betfair_client.place_order_immediate(order)
    else:
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
    """Update the selections table to mark a selection as invalid."""
    query = """
        UPDATE live_betting.selections 
        SET valid = FALSE,
            invalidated_at = NOW(),
            invalidated_reason = %(reason)s
        WHERE unique_id = %(unique_id)s
          AND valid = TRUE
    """
    try:
        postgres_client.execute_query(
            query,
            {"unique_id": unique_id, "reason": reason},
        )
        I(f"[{unique_id}] Marked invalid: {reason}")
    except Exception as e:
        E(f"[{unique_id}] Failed to record invalidation: {e}")


def fetch_selection_state(postgres_client: PostgresClient) -> pd.DataFrame:
    """
    Fetch the current state of all selections from v_selection_state.
    """
    query = """
        SELECT * 
        FROM live_betting.v_selection_state 
        WHERE race_time::date = current_date
        """
    return postgres_client.fetch_data(query)
