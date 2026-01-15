"""
Executor - Handles all side effects: Betfair API calls and database writes.

This module executes the decisions from the decision engine:
- Placing orders via Betfair API
- Cashing out via Betfair API
- Recording invalidations in the database
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W

from .bet_store import (
    generate_bet_attempt_id,
    has_bet_in_parquet,
    store_bet_to_db,
    update_bet_result,
    write_pending_bet,
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
        "cash_outs": 0,
        "invalidations": 0,
    }

    # 1. Place new orders
    for order in decision.orders:
        result = _place_order(order, betfair_client, postgres_client)
        if result.success:
            summary["orders_placed"] += 1
            if result.size_matched and result.size_matched > 0:
                summary["orders_matched"] += 1
        else:
            summary["orders_failed"] += 1

    # 2. Cash out invalidated bets
    if decision.cash_out_market_ids:
        I(
            f"Cashing out {len(decision.cash_out_market_ids)} markets: {decision.cash_out_market_ids}"
        )
        try:
            betfair_client.cash_out_bets(decision.cash_out_market_ids)
            summary["cash_outs"] = len(decision.cash_out_market_ids)
        except Exception as e:
            E(f"Error cashing out markets: {e}")

    # 3. Record invalidations in database
    for unique_id, reason in decision.invalidations:
        _record_invalidation(unique_id, reason, postgres_client)
        summary["invalidations"] += 1

    return summary


def _place_order(
    order: BetFairOrder,
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> OrderResult:
    """
    Place a single order and record it in bet_log.

    Flow:
    1. Write to Parquet (local backup)
    2. Place bet with Betfair
    3. Update Parquet with result
    4. Write to database

    Args:
        order: BetFairOrder to place
        betfair_client: Betfair API client
        postgres_client: Database client

    Returns:
        OrderResult from Betfair
    """
    now = datetime.now(ZoneInfo("Europe/London"))

    # Find the unique_id for this selection
    unique_id = _get_unique_id_for_order(order, postgres_client)

    if not unique_id:
        W(f"Could not find unique_id for order: {order}")
        return OrderResult(success=False, message="Could not find selection unique_id")

    # Check Parquet - this is our source of truth if DB sync failed
    if has_bet_in_parquet(unique_id):
        W(f"[{unique_id}] Already have bet in Parquet - skipping to prevent duplicate")
        return OrderResult(success=False, message="Bet already exists in Parquet")

    # Generate unique bet attempt ID
    bet_attempt_id = generate_bet_attempt_id()

    # 1. Write to Parquet FIRST (local backup before placing bet)
    write_pending_bet(
        bet_attempt_id=bet_attempt_id,
        unique_id=unique_id,
        order=order,
        now=now,
    )

    # 2. Place the order with Betfair
    result = betfair_client.place_order(order)

    # Determine final status
    if not result.success:
        status = "FAILED"
    elif result.size_matched and result.size_matched >= order.size:
        status = "EXECUTION_COMPLETE"
    elif result.size_matched and result.size_matched > 0:
        status = "EXECUTABLE"
    else:
        status = "EXECUTABLE"

    # 3. Update Parquet with result
    update_bet_result(bet_attempt_id, status, result)

    # 4. Record in database
    store_bet_to_db(
        bet_attempt_id=bet_attempt_id,
        unique_id=unique_id,
        order=order,
        result=result,
        status=status,
        now=now,
        postgres_client=postgres_client,
    )

    return result


def _get_unique_id_for_order(
    order: BetFairOrder, postgres_client: PostgresClient
) -> str | None:
    """Look up the unique_id for an order based on market_id and selection_id."""
    query = f"""
        SELECT unique_id 
        FROM live_betting.selections 
        WHERE market_id = '{order.market_id}'
          AND selection_id = {int(order.selection_id)}
        LIMIT 1
    """
    result = postgres_client.fetch_data(query)
    if result.empty:
        return None
    return result.iloc[0]["unique_id"]


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
