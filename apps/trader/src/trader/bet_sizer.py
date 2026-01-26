"""
Bet Sizer - Calculates remaining stake and validates odds for partial/new bets.

This module handles the complex math for:
- BACK bets: simple stake arithmetic
- LAY bets: liability-based calculations

All functions are pure - no side effects, easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING

from api_helpers.helpers.logging_config import I

if TYPE_CHECKING:
    from .models import SelectionState

from .models import SelectionType


@dataclass
class BetSizing:
    """Result of bet sizing calculation."""

    should_bet: bool
    remaining_stake: float
    bet_price: float  # Price to use for the order
    reason: str  # Why we should/shouldn't bet


def calculate_sizing(selection: SelectionState) -> BetSizing:
    """
    Calculate bet sizing for a single selection.

    Args:
        selection: SelectionState from v_selection_state view

    Returns:
        BetSizing with should_bet, remaining_stake, bet_price, reason
    """
    target_stake = selection.calculated_stake
    total_matched = selection.total_matched
    requested_odds = selection.requested_odds

    if selection.selection_type == SelectionType.BACK:
        return _calculate_back_sizing(
            selection, target_stake, total_matched, requested_odds
        )
    else:
        return _calculate_lay_sizing(
            selection, target_stake, total_matched, requested_odds
        )


def _calculate_back_sizing(
    selection: SelectionState,
    target_stake: float,
    total_matched: float,
    requested_odds: float,
) -> BetSizing:
    """
    Calculate sizing for BACK bets.

    BACK is simple: we want to stake X at odds >= requested.
    Remaining = target - already_matched
    """
    current_price = selection.current_back_price

    if current_price is None:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason="No current back price available",
        )

    # Check if price is acceptable (>= requested for BACK)
    if current_price < requested_odds:
        bet_sizing = BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Back price {current_price} < requested {requested_odds}",
        )
        I(bet_sizing)
        return bet_sizing

    # Calculate remaining stake
    remaining = target_stake - total_matched

    if remaining < 1.0:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Fully matched: {total_matched:.2f} of {target_stake:.2f}",
        )

    # Round down to 2 decimal places
    remaining: float = _round_stake(remaining)

    return BetSizing(
        should_bet=True,
        remaining_stake=remaining,
        bet_price=current_price,
        reason=f"BACK {remaining:.2f} @ {current_price} (matched: {total_matched:.2f}/{target_stake:.2f})",
    )


def _calculate_lay_sizing(
    selection: SelectionState,
    target_stake: float,
    total_matched: float,
    requested_odds: float,
) -> BetSizing:
    """
    Calculate sizing for LAY bets.

    LAY works on LIABILITY not stake:
    - Target liability = target_stake (we use stake as liability target)
    - Matched liability tracked in selection.total_liability
    - Remaining liability = target - matched
    - Remaining stake = remaining_liability / (current_odds - 1)
    """
    current_price = selection.current_lay_price

    if current_price is None:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason="No current lay price available",
        )

    # Check if price is acceptable (<= requested for LAY)
    if current_price > requested_odds:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Lay price {current_price} > requested {requested_odds}",
        )

    # Can't lay at odds of 1.0 or below
    if current_price <= 1.0:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Invalid lay price: {current_price}",
        )

    # For LAY bets, target_stake IS the target liability (amount we risk)
    target_liability = target_stake

    # Use total_liability from the view (already calculated correctly)
    matched_liability = selection.total_liability

    # Calculate remaining liability
    remaining_liability = target_liability - matched_liability

    if remaining_liability < 1.0:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Liability filled: {matched_liability:.2f} of {target_liability:.2f}",
        )

    # Convert remaining liability to stake at current price
    remaining_stake = remaining_liability / (current_price - 1)
    remaining_stake = _round_stake(remaining_stake)

    if remaining_stake < 1.0:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Remaining stake {remaining_stake:.2f} below minimum",
        )

    return BetSizing(
        should_bet=True,
        remaining_stake=remaining_stake,
        bet_price=current_price,
        reason=f"LAY {remaining_stake:.2f} @ {current_price} (liability: {matched_liability:.2f}/{target_liability:.2f})",
    )


def _round_stake(stake: float) -> float:
    """Round stake down to 2 decimal places (Betfair requirement)."""
    return float(Decimal(str(stake)).quantize(Decimal("0.01"), rounding=ROUND_DOWN))


def is_fully_matched(selection: SelectionState) -> bool:
    """
    Check if a selection has reached its target exposure.

    For BACK: total_matched >= calculated_stake
    For LAY: total_liability >= target_liability
    """
    target_stake = selection.calculated_stake
    total_matched = selection.total_matched

    if selection.selection_type == SelectionType.BACK:
        return total_matched >= (target_stake - 0.99)  # Allow for rounding

    else:  # LAY
        # For LAY, target_stake IS the target liability
        target_liability = target_stake
        matched_liability = selection.total_liability
        return matched_liability >= (target_liability - 0.99)
