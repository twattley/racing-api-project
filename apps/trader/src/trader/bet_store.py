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

# How long to leave normal orders on Betfair before cancelling
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
    early_bird_expiry: datetime | None = None,
    timeout_minutes: int = ORDER_TIMEOUT_MINUTES,
) -> bool:
    """
    Check if an order should be cancelled.

    Uses max(early_bird_expiry, placed_date + timeout) to automatically
    handle switchover between early bird and normal trading:
    - Orders placed early: persist until early_bird_expiry (race_time - 2h)
    - Orders placed after cutoff: use short timeout (5 mins)

    Args:
        order: The Betfair order to check
        early_bird_expiry: Race time minus cutoff (e.g., race_time - 2 hours)
        timeout_minutes: Short timeout for normal trading mode

    Returns:
        True if order should be cancelled (stale)

    Usage:
        # Pass early_bird_expiry - max() handles the mode automatically
        expiry = calculate_early_bird_expiry(race_time)
        is_order_stale(order, early_bird_expiry=expiry)

        # Order at 10am, race 8pm: hangs until 6pm (early bird)
        # Order at 6:30pm, race 8pm: expires at 6:35pm (normal)
    """
    if order.placed_date is None:
        return False

    now = datetime.now(ZoneInfo("UTC"))
    placed_date = pd.to_datetime(order.placed_date)

    # Make placed_date timezone-aware if it isn't
    if placed_date.tzinfo is None:
        placed_date = placed_date.replace(tzinfo=ZoneInfo("UTC"))

    timeout_expiry = placed_date + timedelta(minutes=timeout_minutes)

    # No early bird - just use timeout
    if early_bird_expiry is None:
        return now > timeout_expiry

    # Make early_bird_expiry timezone-aware if it isn't
    if early_bird_expiry.tzinfo is None:
        early_bird_expiry = early_bird_expiry.replace(tzinfo=ZoneInfo("UTC"))

    # max() automatically picks the right mode:
    # - Early orders: early_bird_expiry wins (later)
    # - Late orders: timeout_expiry wins (later)
    expiry = max(early_bird_expiry, timeout_expiry)
    return now > expiry


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
