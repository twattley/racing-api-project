"""
Bet Store - Simplified bet storage using Betfair as source of truth.

This module provides reliable bet storage:
- Betfair API is the source of truth for bet state
- DB is a record/cache that can be reconciled from Betfair
- No local Parquet needed - we query Betfair to prevent duplicates

Flow:
1. Before placing: check Betfair API for existing bets on this selection
2. Place bet with Betfair
3. Store in DB (can retry if fails, Betfair is truth)
4. Reconciliation loop updates DB from Betfair state
"""

from datetime import datetime, timedelta

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W


# ============================================================================
# DUPLICATE PREVENTION - Check Betfair before placing
# ============================================================================


def has_existing_bet_on_betfair(
    betfair_client: BetFairClient,
    market_id: str,
    selection_id: int,
) -> bool:
    """
    Check if we already have an ACTIVE (EXECUTABLE) bet on this selection via Betfair API.

    This is the source of truth check - prevents duplicate bets even if
    our DB is out of sync.

    Note: Only considers EXECUTABLE orders (still in market waiting to be matched).
    EXECUTION_COMPLETE orders are done and don't block new bets.
    """
    try:
        current_orders = betfair_client.get_current_orders(market_ids=[market_id])
        if current_orders.empty:
            return False

        # Check if any EXECUTABLE order matches this selection
        # EXECUTION_COMPLETE means the order is done (matched or lapsed) - doesn't block
        matching = current_orders[
            (current_orders["selection_id"] == int(selection_id))
            & (current_orders["execution_status"] == "EXECUTABLE")
        ]

        if not matching.empty:
            # Log what we found for debugging
            for _, order in matching.iterrows():
                I(
                    f"Active order on Betfair: sel={selection_id}, "
                    f"size_matched={order.get('size_matched', 0)}, "
                    f"size_remaining={order.get('size_remaining', 0)}"
                )
            return True

        return False
    except Exception as e:
        W(f"Error checking Betfair for existing bets: {e}")
        # If we can't check, be conservative and assume no existing bet
        # The place_order call will fail if there's an issue
        return False


def has_bet_in_db(
    postgres_client: PostgresClient,
    selection_unique_id: str,
) -> bool:
    """
    Check if we have an ACTIVE (EXECUTABLE/PENDING) bet for this selection in DB today.

    Secondary check - DB might be slightly behind Betfair.
    Only blocks on active bets, not completed ones.
    """
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT 1 FROM live_betting.bet_log 
            WHERE selection_unique_id = '{selection_unique_id}'
              AND placed_at::date = CURRENT_DATE
              AND status IN ('EXECUTABLE', 'PENDING')
            LIMIT 1
            """
        )
        return not result.empty
    except Exception as e:
        W(f"Error checking DB for existing bet: {e}")
        return False


# ============================================================================
# STORE BET - After Betfair placement succeeds
# ============================================================================


def _calculate_matched_liability(
    selection_type: str,
    matched_size: float | None,
    matched_price: float | None,
) -> float | None:
    """
    Calculate matched liability from size and price.

    BACK: liability = stake (matched_size)
    LAY: liability = matched_size * (matched_price - 1)
    """
    if matched_size is None or matched_size == 0:
        return None

    if selection_type == "BACK":
        return matched_size
    elif selection_type == "LAY":
        if matched_price is None or matched_price <= 1:
            return None
        return matched_size * (matched_price - 1)
    return None


def store_bet_to_db(
    unique_id: str,
    order: BetFairOrder,
    selection_type: str,
    result: OrderResult,
    status: str,
    now: datetime,
    postgres_client: PostgresClient,
) -> bool:
    """
    Store bet in database after Betfair placement.

    Returns True if successful, False otherwise.
    The caller should log failures but can continue - Betfair is the truth,
    and reconciliation will catch up.
    """
    matched_price = result.average_price_matched if result.success else None
    matched_size = result.size_matched if result.success else None
    matched_liability = _calculate_matched_liability(
        selection_type, matched_size, matched_price
    )

    data = pd.DataFrame(
        [
            {
                "selection_unique_id": unique_id,
                "market_id": order.market_id,
                "selection_id": int(order.selection_id),
                "side": order.side,
                "selection_type": selection_type,
                "requested_price": order.price,
                "requested_size": order.size,
                "matched_price": matched_price,
                "matched_size": matched_size,
                "matched_liability": matched_liability,
                "status": status,
                "placed_at": now,
                "expires_at": now + timedelta(minutes=5),
            }
        ]
    )

    try:
        postgres_client.store_data(
            data=data,
            table="bet_log",
            schema="live_betting",
        )
        I(
            f"[{unique_id}] Stored bet: {status} - matched {matched_size or 0}/{order.size}"
        )
        return True
    except Exception as e:
        E(f"[{unique_id}] Failed to store bet to DB: {e}")
        E(f"[{unique_id}] Bet IS placed on Betfair - reconciliation will catch up")
        return False


# ============================================================================
# RECONCILIATION - Sync DB state from Betfair
# ============================================================================


def reconcile_bets_from_betfair(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> dict:
    """
    Reconcile our DB with Betfair's actual state.

    This should be called periodically to:
    1. Update matched amounts for EXECUTABLE bets
    2. Mark bets as MATCHED when fully matched
    3. Detect any bets on Betfair that aren't in our DB (edge case recovery)

    Returns summary of actions taken.
    """
    summary = {
        "bets_updated": 0,
        "bets_completed": 0,
        "bets_missing_from_db": 0,
    }

    try:
        # Get all current orders from Betfair (orders still in market)
        current_orders = betfair_client.get_current_orders()

        # Get our pending/executable bets from DB
        pending_bets = postgres_client.fetch_data(
            """
            SELECT id, market_id, selection_id, selection_unique_id, selection_type,
                   matched_size as db_matched_size, requested_size
            FROM live_betting.bet_log 
            WHERE status IN ('EXECUTABLE', 'PENDING')
              AND placed_at::date = CURRENT_DATE
            """
        )

        if pending_bets.empty:
            return summary

        # Update DB records from Betfair state
        for _, bet in pending_bets.iterrows():
            matching_orders = None
            if not current_orders.empty:
                matching_orders = current_orders[
                    (current_orders["market_id"] == bet["market_id"])
                    & (current_orders["selection_id"] == int(bet["selection_id"]))
                ]
                if matching_orders.empty:
                    matching_orders = None

            if matching_orders is None:
                # Order not in current orders - fully matched or lapsed
                # Mark as complete - the bet left the market
                _mark_bet_complete(
                    postgres_client,
                    bet["id"],
                    bet["selection_unique_id"],
                    bet["db_matched_size"],
                    bet["requested_size"],
                )
                summary["bets_completed"] += 1
                continue

            # Update from Betfair state
            total_matched = matching_orders["size_matched"].sum()
            avg_price = _calculate_weighted_avg_price(matching_orders)
            betfair_status = matching_orders.iloc[0]["execution_status"]

            # Determine our status
            if betfair_status == "EXECUTION_COMPLETE":
                new_status = "MATCHED"
                summary["bets_completed"] += 1
            else:
                new_status = "EXECUTABLE"

            # Update if matched size changed
            if total_matched != bet["db_matched_size"]:
                _update_bet_from_betfair(
                    postgres_client=postgres_client,
                    bet_id=bet["id"],
                    selection_type=bet["selection_type"],
                    matched_size=total_matched,
                    matched_price=avg_price,
                    betfair_status=betfair_status,
                    status=new_status,
                )
                summary["bets_updated"] += 1

        # Check for Betfair orders we don't have in DB (recovery case)
        if not current_orders.empty:
            # Filter to only our trader orders
            trader_orders = current_orders[
                current_orders["customer_strategy_ref"] == "trader"
            ]

            for _, order in trader_orders.iterrows():
                # Check if we have this in DB
                exists = postgres_client.fetch_data(
                    f"""
                    SELECT 1 FROM live_betting.bet_log
                    WHERE market_id = '{order["market_id"]}'
                      AND selection_id = {int(order["selection_id"])}
                      AND placed_at::date = CURRENT_DATE
                    LIMIT 1
                    """
                )

                if exists.empty:
                    W(
                        f"Found bet on Betfair not in DB: {order['market_id']}/{order['selection_id']}"
                    )
                    summary["bets_missing_from_db"] += 1
                    # Could insert here, but need unique_id from selections table
                    # For now just log - manual review needed

        return summary

    except Exception as e:
        E(f"Error reconciling bets from Betfair: {e}")
        return summary


def _calculate_weighted_avg_price(orders_df: pd.DataFrame) -> float | None:
    """Calculate weighted average price from multiple order fills."""
    total_matched = orders_df["size_matched"].sum()
    if total_matched == 0:
        return None

    weighted_sum = (
        orders_df["size_matched"] * orders_df["average_price_matched"]
    ).sum()

    return round(weighted_sum / total_matched, 2)


def _update_bet_from_betfair(
    postgres_client: PostgresClient,
    bet_id: int,
    selection_type: str,
    matched_size: float,
    matched_price: float | None,
    betfair_status: str,
    status: str,
) -> None:
    """Update a bet record with data from Betfair."""
    matched_liability = _calculate_matched_liability(
        selection_type, matched_size, matched_price
    )

    postgres_client.execute_query(
        """
        UPDATE live_betting.bet_log 
        SET matched_size = :matched_size,
            matched_price = :matched_price,
            matched_liability = :matched_liability,
            betfair_status = :betfair_status,
            status = :status,
            matched_at = CASE WHEN :status = 'MATCHED' THEN NOW() ELSE matched_at END
        WHERE id = :id
        """,
        {
            "id": bet_id,
            "matched_size": matched_size,
            "matched_price": matched_price,
            "matched_liability": matched_liability,
            "betfair_status": betfair_status,
            "status": status,
        },
    )


def _mark_bet_complete(postgres_client: PostgresClient, bet_id: int) -> None:
    """Mark a bet as complete when it's no longer on Betfair."""
    postgres_client.execute_query(
        """
        UPDATE live_betting.bet_log 
        SET status = 'MATCHED',
            matched_at = NOW()
        WHERE id = :id
          AND status != 'MATCHED'
        """,
        {"id": bet_id},
    )
