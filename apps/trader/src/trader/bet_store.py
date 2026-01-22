"""
Bet Store - Order management helpers for execution.

This module handles the mechanics of order placement:
- Finding existing orders for a selection
- Checking if orders are stale (waiting too long)
- Cancelling orders
- Calculating remaining stake needed

Reconciliation (moving completed orders to bet_log) is handled
by the reconciliation module, not here.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.helpers.logging_config import E, I

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
