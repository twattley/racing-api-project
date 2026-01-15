"""
Bet Sizer - Calculates remaining stake and validates odds for partial/new bets.

This module handles the complex math for:
- BACK bets: simple stake arithmetic
- LAY bets: liability-based calculations

All functions are pure - no side effects, easy to test.
"""

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

import pandas as pd


@dataclass
class BetSizing:
    """Result of bet sizing calculation."""

    should_bet: bool
    remaining_stake: float
    bet_price: float  # Price to use for the order
    reason: str  # Why we should/shouldn't bet


def calculate_sizing(row: pd.Series) -> BetSizing:
    """
    Calculate bet sizing for a single selection.

    Args:
        row: Series from v_selection_state view with columns:
            - selection_type: 'BACK' or 'LAY'
            - calculated_stake: target stake from staking tiers
            - total_matched: sum of matched sizes from bet_log
            - requested_odds: target price (minimum for BACK, maximum for LAY)
            - current_back_price: live back price
            - current_lay_price: live lay price

    Returns:
        BetSizing with should_bet, remaining_stake, bet_price, reason
    """
    selection_type = row["selection_type"]
    target_stake = float(row["calculated_stake"])
    total_matched = float(row.get("total_matched", 0) or 0)
    requested_odds = float(row["requested_odds"])

    if selection_type == "BACK":
        return _calculate_back_sizing(row, target_stake, total_matched, requested_odds)
    else:
        return _calculate_lay_sizing(row, target_stake, total_matched, requested_odds)


def _calculate_back_sizing(
    row: pd.Series,
    target_stake: float,
    total_matched: float,
    requested_odds: float,
) -> BetSizing:
    """
    Calculate sizing for BACK bets.

    BACK is simple: we want to stake X at odds >= requested.
    Remaining = target - already_matched
    """
    current_price = row.get("current_back_price")

    if pd.isna(current_price) or current_price is None:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason="No current back price available",
        )

    current_price = float(current_price)

    # Check if price is acceptable (>= requested for BACK)
    if current_price < requested_odds:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason=f"Back price {current_price} < requested {requested_odds}",
        )

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
    remaining = _round_stake(remaining)

    return BetSizing(
        should_bet=True,
        remaining_stake=remaining,
        bet_price=current_price,
        reason=f"BACK {remaining:.2f} @ {current_price} (matched: {total_matched:.2f}/{target_stake:.2f})",
    )


def _calculate_lay_sizing(
    row: pd.Series,
    target_stake: float,
    total_matched: float,
    requested_odds: float,
) -> BetSizing:
    """
    Calculate sizing for LAY bets.

    LAY works on LIABILITY not stake:
    - Target liability = target_stake * (requested_odds - 1)
    - Matched liability = sum of (size * (price - 1)) for each matched bet
    - Remaining liability = target - matched
    - Remaining stake = remaining_liability / (current_odds - 1)

    We need to track liability across potentially different prices.
    Since we don't have per-bet breakdown, we use average_price_matched from the view
    or estimate from total_matched.
    """
    current_price = row.get("current_lay_price")

    if pd.isna(current_price) or current_price is None:
        return BetSizing(
            should_bet=False,
            remaining_stake=0,
            bet_price=0,
            reason="No current lay price available",
        )

    current_price = float(current_price)

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

    # Calculate target liability
    target_liability = target_stake * (requested_odds - 1)

    # Estimate matched liability
    # If we have matched bets, we need to know at what average price
    # The view should provide this, but we'll use a safe estimate
    average_matched_price = row.get("average_matched_price")
    if pd.isna(average_matched_price) or average_matched_price is None:
        # Assume matched at requested odds (conservative)
        average_matched_price = requested_odds

    average_matched_price = float(average_matched_price)
    if average_matched_price <= 1.0:
        average_matched_price = requested_odds

    matched_liability = total_matched * (average_matched_price - 1)

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


def is_fully_matched(row: pd.Series) -> bool:
    """
    Check if a selection has reached its target exposure.

    For BACK: total_matched >= calculated_stake
    For LAY: matched_liability >= target_liability
    """
    selection_type = row["selection_type"]
    target_stake = float(row["calculated_stake"])
    total_matched = float(row.get("total_matched", 0) or 0)

    if selection_type == "BACK":
        return total_matched >= (target_stake - 0.99)  # Allow for rounding

    else:  # LAY
        requested_odds = float(row["requested_odds"])
        target_liability = target_stake * (requested_odds - 1)

        average_matched_price = row.get("average_matched_price")
        if pd.isna(average_matched_price) or average_matched_price is None:
            average_matched_price = requested_odds
        average_matched_price = float(average_matched_price)
        if average_matched_price <= 1.0:
            average_matched_price = requested_odds

        matched_liability = total_matched * (average_matched_price - 1)
        return matched_liability >= (target_liability - 0.99)
