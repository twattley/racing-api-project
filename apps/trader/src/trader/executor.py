"""
Executor - Handles all side effects: Betfair API calls and database writes.

This module executes the decisions from the decision engine:
- Placing orders via Betfair API
- Cashing out via Betfair API
- Recording invalidations in the database
"""

from datetime import datetime
from time import sleep
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

# Time to wait before checking actual bet status from Betfair
BET_STATUS_CHECK_DELAY_SECONDS = 2


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

    # 1b. Refresh bet status from Betfair (get actual matched amounts)
    if summary["orders_placed"] > 0:
        sleep(BET_STATUS_CHECK_DELAY_SECONDS)
        _refresh_bet_status(betfair_client, postgres_client)

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

    # Find the unique_id and selection_type for this selection
    unique_id, selection_type = _get_selection_info_for_order(order, postgres_client)

    if not unique_id:
        W(f"Could not find unique_id for order: {order}")
        return OrderResult(success=False, message="Could not find selection unique_id")

    if not selection_type:
        W(f"[{unique_id}] Could not find selection_type - defaulting to order.side")
        selection_type = order.side  # Fallback to order side (BACK/LAY)

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
        selection_type=selection_type,
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


def _refresh_bet_status(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> None:
    """
    Refresh bet_log with actual status from Betfair.
    
    Fetches current orders from Betfair and updates any bet_log entries
    that have status EXECUTABLE with the actual matched amounts.
    """
    try:
        current_orders = betfair_client.get_current_orders()
        if current_orders.empty:
            return
        
        # Get our pending bets (EXECUTABLE status means in-market, waiting for match)
        pending_bets = postgres_client.fetch_data("""
            SELECT id, market_id, selection_id 
            FROM live_betting.bet_log 
            WHERE status = 'EXECUTABLE' 
              AND placed_at::date = CURRENT_DATE
        """)
        
        if pending_bets.empty:
            return
        
        # Match Betfair orders to our bet_log entries
        for _, bet in pending_bets.iterrows():
            matching_orders = current_orders[
                (current_orders["market_id"] == bet["market_id"]) &
                (current_orders["selection_id"] == int(bet["selection_id"]))
            ]
            
            if matching_orders.empty:
                # Order not in current orders - might have completed, check if fully matched
                continue
            
            # Sum up all matching orders (could be multiple fills)
            total_matched = matching_orders["size_matched"].sum()
            avg_price = (
                (matching_orders["size_matched"] * matching_orders["average_price_matched"]).sum() 
                / total_matched
            ) if total_matched > 0 else None
            
            # Get Betfair's status (take first, they should be same)
            betfair_status = matching_orders.iloc[0]["execution_status"]
            
            # Map Betfair status to our status
            if betfair_status == "EXECUTION_COMPLETE":
                new_status = "MATCHED"
            else:
                new_status = "EXECUTABLE"  # Still in market
            
            # Update bet_log
            postgres_client.execute_query(
                """
                UPDATE live_betting.bet_log 
                SET matched_size = %(matched_size)s,
                    matched_price = %(matched_price)s,
                    betfair_status = %(betfair_status)s,
                    status = %(status)s,
                    matched_at = CASE WHEN %(status)s = 'MATCHED' THEN NOW() ELSE matched_at END,
                    matched_liability = CASE 
                        WHEN selection_type = 'BACK' THEN %(matched_size)s
                        WHEN selection_type = 'LAY' AND %(matched_price)s > 1 
                            THEN %(matched_size)s * (%(matched_price)s - 1)
                        ELSE %(matched_size)s
                    END
                WHERE id = %(id)s
                """,
                {
                    "id": bet["id"],
                    "matched_size": total_matched,
                    "matched_price": round(avg_price, 2) if avg_price else None,
                    "betfair_status": betfair_status,
                    "status": new_status,
                },
            )
            
            I(f"Updated bet {bet['id']}: {betfair_status} - matched {total_matched}")
            
    except Exception as e:
        W(f"Failed to refresh bet status from Betfair: {e}")
