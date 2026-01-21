"""
Bet Store - Simplified: Betfair is the source of truth.

Flow:
1. Query Betfair current_orders to see what's live
2. bet_log only written when EXECUTION_COMPLETE (for history/reporting)
3. No pending_orders table - Betfair tracks that

Key Functions:
- find_order_for_selection(): Find order by customer_strategy_ref
- is_order_stale(): Check if order is older than timeout
- get_matched_from_log(): Get total matched from bet_log for a selection
- store_completed_bet(): Write to bet_log when fully done
- process_completed_orders(): Move EXECUTION_COMPLETE to bet_log
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import D, E, I, W

# How long to leave orders on Betfair before cancelling
ORDER_TIMEOUT_MINUTES = 5


# ============================================================================
# BETFAIR ORDER HELPERS
# ============================================================================


def find_order_for_selection(
    current_orders: list[CurrentOrder],
    unique_id: str,
) -> CurrentOrder | None:
    """
    Find an order for a selection by its unique_id (customer_strategy_ref).

    Returns the order if found, None otherwise.
    """
    for order in current_orders:
        if order.customer_strategy_ref == unique_id:
            return order
    return None


def is_order_stale(
    order: CurrentOrder,
    timeout_minutes: int = ORDER_TIMEOUT_MINUTES,
) -> bool:
    """
    Check if an order has been sitting for longer than the timeout.

    Uses Betfair's placed_date as the source of truth.
    """
    if order.placed_date is None:
        return False

    placed_date = pd.to_datetime(order.placed_date)
    now = datetime.now(ZoneInfo("UTC"))

    # Make placed_date timezone-aware if it isn't
    if placed_date.tzinfo is None:
        placed_date = placed_date.replace(tzinfo=ZoneInfo("UTC"))

    cutoff = now - timedelta(minutes=timeout_minutes)
    return placed_date < cutoff


def cancel_order(
    betfair_client: BetFairClient,
    order: CurrentOrder,
) -> bool:
    """
    Cancel a specific order on Betfair.

    Returns True if cancelled successfully.
    """
    try:
        betfair_client.trading_client.betting.cancel_orders(
            market_id=order.market_id,
            instructions=[{"betId": order.bet_id}],
        )
        I(f"Cancelled order {order.bet_id} in market {order.market_id}")
        return True
    except Exception as e:
        E(f"Error cancelling order {order.bet_id}: {e}")
        return False


# ============================================================================
# BET LOG - Historical record of matched bets
# ============================================================================


def get_matched_from_log(
    postgres_client: PostgresClient,
    unique_id: str,
) -> float:
    """
    Get total matched amount from bet_log for a selection.

    This is used to calculate remaining stake needed.
    """
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT COALESCE(SUM(matched_size), 0) as total_matched
            FROM live_betting.bet_log 
            WHERE selection_unique_id = '{unique_id}'
            """
        )
        if result.empty:
            return 0.0
        return float(result.iloc[0]["total_matched"])
    except Exception as e:
        W(f"Error getting matched from log for {unique_id}: {e}")
        return 0.0


def bet_already_in_log(
    postgres_client: PostgresClient,
    unique_id: str,
    placed_at: datetime,
) -> bool:
    """Check if this specific bet is already logged (avoid duplicates)."""
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT 1 FROM live_betting.bet_log 
            WHERE selection_unique_id = '{unique_id}'
              AND placed_at = '{placed_at}'
            LIMIT 1
            """
        )
        return not result.empty
    except Exception as e:
        W(f"Error checking bet_log: {e}")
        return False


def store_completed_bet(
    unique_id: str,
    market_id: str,
    selection_id: int,
    side: str,
    matched_size: float,
    matched_price: float,
    placed_at: datetime,
    matched_at: datetime | None,
    postgres_client: PostgresClient,
) -> bool:
    """
    Store a completed bet in bet_log.

    Called when:
    - Order is EXECUTION_COMPLETE (fully matched)
    - Stale order cancelled with partial match (log the matched portion)
    """
    # Calculate liability
    if side == "BACK":
        matched_liability = matched_size
    elif side == "LAY" and matched_price and matched_price > 1:
        matched_liability = matched_size * (matched_price - 1)
    else:
        matched_liability = None

    # Get selection_type from selections table
    selection_info = postgres_client.fetch_data(
        f"""
        SELECT selection_type FROM live_betting.selections 
        WHERE unique_id = '{unique_id}'
        LIMIT 1
        """
    )
    selection_type = (
        selection_info.iloc[0]["selection_type"] if not selection_info.empty else side
    )

    data = pd.DataFrame(
        [
            {
                "selection_unique_id": unique_id,
                "market_id": market_id,
                "selection_id": selection_id,
                "side": side,
                "selection_type": selection_type,
                "matched_price": matched_price,
                "matched_size": matched_size,
                "matched_liability": matched_liability,
                "status": "MATCHED",
                "placed_at": placed_at,
                "matched_at": matched_at or placed_at,
            }
        ]
    )

    try:
        postgres_client.store_data(
            data=data,
            table="bet_log",
            schema="live_betting",
        )
        I(f"[{unique_id}] Stored in bet_log: {matched_size} @ {matched_price}")
        return True
    except Exception as e:
        E(f"[{unique_id}] Failed to store in bet_log: {e}")
        return False


# ============================================================================
# RECONCILIATION - Move completed orders to bet_log
# ============================================================================


def process_completed_orders(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> dict:
    """
    Process EXECUTION_COMPLETE orders from Betfair and store in bet_log.

    Called at start of each trading loop.
    Returns summary of actions taken.
    """
    summary = {"completed_moved_to_log": 0}

    try:
        current_orders = betfair_client.get_current_orders()

        if not current_orders:
            return summary

        # Filter to our trader orders (not UI) that are complete
        completed = [
            o
            for o in current_orders
            if o.customer_strategy_ref != "UI"
            and o.execution_status == "EXECUTION_COMPLETE"
            and o.size_matched > 0
        ]

        for order in completed:
            unique_id = order.customer_strategy_ref
            placed_at = pd.to_datetime(order.placed_date)

            # Skip if already in log
            if bet_already_in_log(postgres_client, unique_id, placed_at):
                continue

            # Store in bet_log
            stored = store_completed_bet(
                unique_id=unique_id,
                market_id=order.market_id,
                selection_id=order.selection_id,
                side=order.side,
                matched_size=order.size_matched,
                matched_price=order.average_price_matched,
                placed_at=placed_at,
                matched_at=(
                    pd.to_datetime(order.matched_date) if order.matched_date else None
                ),
                postgres_client=postgres_client,
            )

            if stored:
                summary["completed_moved_to_log"] += 1

        return summary

    except Exception as e:
        E(f"Error processing completed orders: {e}")
        return summary


# ============================================================================
# STAKING CALCULATION
# ============================================================================


def calculate_remaining_stake(
    target_stake: float,
    current_order: CurrentOrder | None,
    matched_in_log: float,
) -> float:
    """
    Calculate how much more we need to stake.

    Args:
        target_stake: What the model wants us to stake
        current_order: Active order on Betfair (if any)
        matched_in_log: Amount already matched (from bet_log)

    Returns:
        Amount still needed to stake (0 if fully staked)
    """
    # Total already committed = matched in log + matched in current + remaining in current
    already_matched = matched_in_log

    if current_order:
        already_matched += current_order.size_matched
        # Also count what's still sitting in the order
        already_matched += current_order.size_remaining

    remaining = target_stake - already_matched

    return max(0.0, round(remaining, 2))
