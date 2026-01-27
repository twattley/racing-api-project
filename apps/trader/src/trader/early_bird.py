"""
Early Bird Trading Strategy.

Places smaller stakes at better prices early in the day to gain queue position.
Orders sit until expires_at (race_time - 2 hours), then switch to normal trading.

Strategy:
- BACK bets: place at higher prices (better for us)
- LAY bets: place at lower prices (better for us)
- Fixed stake sizes, spread across tick offsets
- Optional sleep between orders to look more human
"""

import time
from dataclasses import dataclass
from datetime import datetime

from api_helpers.helpers.logging_config import D, I

from trader.models import SelectionState, SelectionType
from trader.price_ladder import PriceLadder


# ============================================================================
# CONFIGURATION - Easy to adjust
# ============================================================================

# Fixed stake for BACK bets (per order)
BACK_STAKE = 10.0

# Fixed liability for LAY bets (per order)
LAY_LIABILITY = 15.0

# Tick offsets: where to place orders relative to market price
# BACK: positive = higher prices (better for us)
# LAY: negative = lower prices (better for us)
BACK_TICK_OFFSETS = [2, 3, 4]
LAY_TICK_OFFSETS = [-2, -3, -4]

# Sleep range between orders (seconds) - set to (0, 0) to disable
SLEEP_RANGE = (1.0, 3.0)


# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class EarlyBirdOrder:
    """A single early bird order at an offset price."""

    selection: SelectionState
    price: float
    stake: float
    ticks_from_market: int

    @property
    def description(self) -> str:
        direction = "above" if self.ticks_from_market > 0 else "below"
        return f"{self.stake:.2f} @ {self.price} ({abs(self.ticks_from_market)} ticks {direction})"


# ============================================================================
# ORDER GENERATION
# ============================================================================


def generate_early_bird_orders(
    selection: SelectionState,
) -> list[EarlyBirdOrder]:
    """
    Generate early bird orders at offset prices.

    Uses fixed stakes from constants:
    - BACK: £10 per order at 2, 3, 4 ticks above market
    - LAY: £15 liability per order at 2, 3, 4 ticks below market

    Args:
        selection: The selection to bet on

    Returns:
        List of EarlyBirdOrder objects ready for placement

    Example:
        # BACK bet, market at 3.0
        # Generates:
        #   £10 @ 3.10 (2 ticks above)
        #   £10 @ 3.15 (3 ticks above)
        #   £10 @ 3.20 (4 ticks above)
    """
    ladder = PriceLadder()

    # Get current market price and config based on selection type
    if selection.selection_type == SelectionType.BACK:
        market_price = selection.current_back_price
        stake = BACK_STAKE
        offsets = BACK_TICK_OFFSETS
    else:
        market_price = selection.current_lay_price
        stake = LAY_LIABILITY
        offsets = LAY_TICK_OFFSETS

    if market_price is None:
        D(f"[{selection.unique_id}] 🐦 No market price for early bird")
        return []

    I(
        f"[{selection.unique_id}] 🐦 EARLY BIRD: {selection.selection_type.value} @ market {market_price}, "
        f"placing at offsets {offsets}"
    )

    orders = []
    for offset in offsets:
        # Calculate target price
        target_price = ladder.ticks_away(market_price, offset)

        # Skip if price is outside ladder range
        if target_price is None:
            D(f"[{selection.unique_id}] 🐦 Offset {offset} outside ladder range")
            continue

        orders.append(
            EarlyBirdOrder(
                selection=selection,
                price=target_price,
                stake=stake,
                ticks_from_market=offset,
            )
        )
        I(
            f"[{selection.unique_id}] 🐦   → {stake:.2f} @ {target_price} ({offset} ticks)"
        )

    return orders


def sleep_between_orders(sleep_range: tuple[float, float] | None = None) -> None:
    """
    Sleep for a random period between orders.

    Args:
        sleep_range: (min, max) seconds to sleep. None uses SLEEP_RANGE constant.
                    Pass (0, 0) to disable sleeping (for tests).
    """
    import random

    min_sleep, max_sleep = sleep_range or SLEEP_RANGE

    if max_sleep <= 0:
        return

    sleep_time = random.uniform(min_sleep, max_sleep)
    time.sleep(sleep_time)


def is_early_bird_time(selection: SelectionState) -> bool:
    """
    Check if we're still in early bird trading mode.

    Early bird mode: current time < expires_at (race_time - 2 hours)
    Normal mode: current time >= expires_at
    """
    now = datetime.now(selection.expires_at.tzinfo)
    return now < selection.expires_at


def should_use_early_bird(
    selection: SelectionState,
    min_minutes_to_race: float = 180,  # 3 hours
) -> tuple[bool, str]:
    """
    Decide whether to use early bird strategy for this selection.

    Criteria:
    - Must be in early bird time window
    - Race should be far enough away to benefit from queue position
    - No existing bets (don't scatter on top-ups)

    Args:
        selection: The selection to check
        min_minutes_to_race: Minimum minutes until race to use early bird

    Returns:
        Tuple of (should_use, reason_string)
    """
    # Must be before cutoff
    if not is_early_bird_time(selection):
        return False, f"past cutoff (expires_at={selection.expires_at})"

    # Race should be far enough away
    if selection.minutes_to_race < min_minutes_to_race:
        return (
            False,
            f"race too soon ({selection.minutes_to_race:.0f}m < {min_minutes_to_race}m)",
        )

    # Don't scatter on top-ups - only fresh bets
    if selection.has_bet:
        return False, "already has bet (top-up uses normal mode)"

    return (
        True,
        f"eligible ({selection.minutes_to_race:.0f}m to race, expires {selection.expires_at.strftime('%H:%M')})",
    )
