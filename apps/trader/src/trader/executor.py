"""
Executor - Handles all side effects: Betfair API calls and database writes.

This module executes the decisions from the decision engine:
- Placing orders via Betfair API
- Cashing out via Betfair API
- Recording invalidations in the database

Flow for placing bets:
1. Check Betfair API - do we already have a bet on this selection?
2. Place bet with Betfair (point of no return)
3. Store in DB (can retry/reconcile if this fails)
4. Reconciliation loop keeps DB in sync with Betfair
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import D, E, I, W

from .bet_store import (
    has_existing_bet_on_betfair,
    has_bet_in_db,
    store_bet_to_db,
    reconcile_bets_from_betfair,
)
from .decision_engine import DecisionResult


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
        "cash_outs": 0,
        "invalidations": 0,
    }

    # 1. Place new orders
    for order in decision.orders:
        result = _place_order(order, betfair_client, postgres_client)
        if result is None:
            summary["orders_skipped"] += 1
        elif result.success:
            summary["orders_placed"] += 1
            if result.size_matched and result.size_matched > 0:
                summary["orders_matched"] += 1
        else:
            summary["orders_failed"] += 1

    # 2. Reconcile DB with Betfair (updates matched amounts, catches missed DB writes)
    if summary["orders_placed"] > 0:
        reconcile_summary = reconcile_bets_from_betfair(betfair_client, postgres_client)
        if reconcile_summary["bets_updated"] > 0:
            I(f"Reconciled {reconcile_summary['bets_updated']} bets from Betfair")

    # 3. Cash out invalidated bets
    if decision.cash_out_market_ids:
        I(
            f"Cashing out {len(decision.cash_out_market_ids)} markets: {decision.cash_out_market_ids}"
        )
        try:
            betfair_client.cash_out_bets(decision.cash_out_market_ids)
            summary["cash_outs"] = len(decision.cash_out_market_ids)
        except Exception as e:
            E(f"Error cashing out markets: {e}")

    # 4. Record invalidations in database
    for unique_id, reason in decision.invalidations:
        _record_invalidation(unique_id, reason, postgres_client)
        summary["invalidations"] += 1

    # Only log summary if something actually happened
    if any(v > 0 for k, v in summary.items() if k != "orders_skipped"):
        I(f"Execution summary: {summary}")

    return summary


def _place_order(
    order: BetFairOrder,
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> OrderResult | None:
    """
    Place a single order and record it in bet_log.

    Flow:
    1. Check Betfair API - do we already have a bet? (source of truth)
    2. Check DB as secondary validation
    3. Place bet with Betfair (point of no return)
    4. Store in DB (can retry/reconcile if this fails)

    Args:
        order: BetFairOrder to place
        betfair_client: Betfair API client
        postgres_client: Database client

    Returns:
        OrderResult from Betfair, or None if skipped due to existing bet
    """
    now = datetime.now(ZoneInfo("Europe/London"))

    # Find the unique_id and selection_type for this selection
    unique_id, selection_type = _get_selection_info_for_order(order, postgres_client)

    if not unique_id:
        W(f"Could not find unique_id for order: {order}")
        return OrderResult(success=False, message="Could not find selection unique_id")

    if not selection_type:
        W(f"[{unique_id}] Could not find selection_type - defaulting to order.side")
        selection_type = order.side  # Fallback to order side (BACK/LAY)

    # 1. Check Betfair API first - this is the SOURCE OF TRUTH
    if has_existing_bet_on_betfair(
        betfair_client, order.market_id, int(order.selection_id)
    ):
        D(f"[{unique_id}] Bet already in market on Betfair - skipping")
        return None

    # 2. Secondary check: DB (might be slightly behind Betfair)
    if has_bet_in_db(postgres_client, unique_id):
        D(f"[{unique_id}] Bet already in DB - skipping")
        return None

    # 3. Place the order with Betfair (POINT OF NO RETURN)
    I(f"[{unique_id}] Placing {order.side} order: {order.size} @ {order.price}")
    result = betfair_client.place_order(order)

    # Determine status
    if not result.success:
        status = "FAILED"
    elif result.size_matched and result.size_matched >= order.size:
        status = "MATCHED"
    elif result.size_matched and result.size_matched > 0:
        status = "EXECUTABLE"  # Partially matched, still in market
    else:
        status = "EXECUTABLE"  # Unmatched, in market

    # 4. Store in DB (can fail - reconciliation will catch up)
    store_bet_to_db(
        unique_id=unique_id,
        order=order,
        selection_type=selection_type,
        result=result,
        status=status,
        now=now,
        postgres_client=postgres_client,
    )

    return result


def _get_selection_info_for_order(
    order: BetFairOrder, postgres_client: PostgresClient
) -> tuple[str | None, str | None]:
    """Look up the unique_id and selection_type for an order based on market_id and selection_id."""
    query = f"""
        SELECT unique_id, selection_type 
        FROM live_betting.selections 
        WHERE market_id = '{order.market_id}'
          AND selection_id = {int(order.selection_id)}
        LIMIT 1
    """
    result = postgres_client.fetch_data(query)
    if result.empty:
        return None, None
    return result.iloc[0]["unique_id"], result.iloc[0]["selection_type"]


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

    This is the ONLY read operation needed for the decision loop.
    """
    query = "SELECT * FROM live_betting.v_selection_state"
    return postgres_client.fetch_data(query)
