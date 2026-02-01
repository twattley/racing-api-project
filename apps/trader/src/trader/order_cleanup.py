"""
Order Cleanup - Cancel stale orders based on time to race.

This module runs at the start of each trader loop and cancels orders
that have been sitting too long. The timeout depends on how close the
race is:

- Race < 5 mins away: Cancel immediately (no time to wait for match)
- Otherwise: Cancel after ORDER_STALE_MINUTES of sitting

This replaces the old fill-or-kill logic with a simpler approach:
we always place normal orders, and this cleanup handles cancellation.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import D, I

# How long to let orders sit before cancelling (when race is far away)
ORDER_STALE_MINUTES = 5

# When race is this close, cancel any pending orders immediately
RACE_IMMINENT_MINUTES = 5


def run(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> dict:
    """
    Cancel stale orders based on time to race.

    Returns summary of actions taken.
    """
    summary = {
        "cancelled_stale": 0,
        "cancelled_imminent": 0,
    }

    # Get current orders from Betfair
    current_orders: list[CurrentOrder] = betfair_client.get_current_orders()

    if not current_orders:
        return summary

    # Get race times for our selections
    race_times: dict[str, datetime] = _get_race_times(postgres_client)

    now: datetime = datetime.now(ZoneInfo("UTC"))

    for order in current_orders:
        if order.execution_status != "EXECUTABLE":
            continue

        # Skip if not one of our trader orders
        if not _is_trader_order(order):
            continue

        unique_id = _get_base_unique_id(order.customer_strategy_ref)
        race_time: str = race_times.get(unique_id)

        if race_time is None:
            D(f"[{unique_id}] No race time found, skipping cleanup")
            continue

        # Make race_time timezone-aware if needed
        if race_time.tzinfo is None:
            race_time = race_time.replace(tzinfo=ZoneInfo("UTC"))

        minutes_to_race = (race_time - now).total_seconds() / 60

        # Rule 1: Race imminent - cancel immediately
        if minutes_to_race < RACE_IMMINENT_MINUTES:
            I(f"[{unique_id}] Race in {minutes_to_race:.1f}m - cancelling order")
            if _cancel_order(betfair_client, order):
                summary["cancelled_imminent"] += 1
            continue

        # Rule 2: Order too old - cancel if stale
        if _is_order_stale(order, now):
            I(f"[{unique_id}] Order stale (>{ORDER_STALE_MINUTES}m old) - cancelling")
            if _cancel_order(betfair_client, order):
                summary["cancelled_stale"] += 1

    if summary["cancelled_stale"] or summary["cancelled_imminent"]:
        I(f"Order cleanup: {summary}")

    return summary


def _get_race_times(postgres_client: PostgresClient) -> dict[str, datetime]:
    """Get race times for all today's selections."""
    query = """
        SELECT unique_id, race_time 
        FROM live_betting.selections 
        WHERE race_date = CURRENT_DATE
    """
    df = postgres_client.fetch_data(query)

    if df.empty:
        return {}

    return {row["unique_id"]: row["race_time"] for _, row in df.iterrows()}


def _is_trader_order(order: CurrentOrder) -> bool:
    """Check if this is an order placed by the trader (not UI)."""
    ref = order.customer_strategy_ref
    if not ref:
        return False
    # Trader orders are 11-char hashes, UI orders start with "UI_"
    return not ref.startswith("UI_") and len(ref) >= 11


def _get_base_unique_id(strategy_ref: str | None) -> str | None:
    """Extract the base unique_id (first 11 chars) from strategy ref."""
    if not strategy_ref:
        return None
    return strategy_ref[:11]


def _is_order_stale(order: CurrentOrder, now: datetime) -> bool:
    """Check if an order has been sitting too long."""
    if order.placed_date is None:
        return False

    placed_date = pd.to_datetime(order.placed_date)

    # Make placed_date timezone-aware if needed
    if placed_date.tzinfo is None:
        placed_date = placed_date.replace(tzinfo=ZoneInfo("UTC"))

    age_minutes = (now - placed_date).total_seconds() / 60
    return age_minutes > ORDER_STALE_MINUTES


def _cancel_order(betfair_client: BetFairClient, order: CurrentOrder) -> bool:
    """Cancel a single order. Returns True if successful."""
    try:
        betfair_client.trading_client.betting.cancel_orders(
            market_id=order.market_id,
            instructions=[{"betId": order.bet_id}],
        )
        return True
    except Exception as e:
        I(f"Failed to cancel order {order.bet_id}: {e}")
        return False
