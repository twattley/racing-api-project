"""
Decision Engine - Pure function that reads v_selection_state and returns BetFairOrder objects.

This module contains NO side effects - it only transforms data.
All database reads and API calls happen in the executor.
"""

from dataclasses import dataclass

import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder
from api_helpers.helpers.logging_config import D, I


@dataclass
class DecisionResult:
    """Result from the decision engine - orders to place and markets to cash out."""

    orders: list[BetFairOrder]
    cash_out_market_ids: list[str]
    invalidations: list[tuple[str, str]]  # (unique_id, reason) for logging/updating


# Price drift tolerance - how much worse can the current price be vs requested
BACK_DRIFT_TOLERANCE = 0.05  # 5% worse odds acceptable for backs
LAY_DRIFT_TOLERANCE = 0.05  # 5% worse odds acceptable for lays


def decide(view_df: pd.DataFrame) -> DecisionResult:
    """
    Pure decision function - takes view data, returns actions.

    Args:
        view_df: DataFrame from v_selection_state view

    Returns:
        DecisionResult with orders to place, markets to cash out, and invalidation reasons
    """
    orders: list[BetFairOrder] = []
    cash_out_market_ids: list[str] = []
    invalidations: list[tuple[str, str]] = []

    for _, row in view_df.iterrows():
        order, cash_out, invalidation = _decide_row(row)

        if order:
            orders.append(order)
        if cash_out:
            cash_out_market_ids.append(cash_out)
        if invalidation:
            invalidations.append(invalidation)

    # Deduplicate market IDs for cash out
    return DecisionResult(
        orders=orders,
        cash_out_market_ids=list(set(cash_out_market_ids)),
        invalidations=invalidations,
    )


def _decide_row(row: pd.Series) -> tuple[BetFairOrder | None, str | None, tuple | None]:
    """
    Decide what to do for a single selection.

    Returns:
        Tuple of (order_to_place, market_id_to_cash_out, invalidation_tuple)
    """
    unique_id = row["unique_id"]

    # Already invalid - skip entirely
    if not row["valid"]:
        D(f"[{unique_id}] Already invalid: {row.get('invalidated_reason', 'unknown')}")
        return None, None, None

    # Already fully matched - nothing to do
    if row["fully_matched"]:
        D(f"[{unique_id}] Already fully matched")
        return None, None, None

    # Runner has been removed - invalidate if we have a bet
    if row["runner_status"] == "REMOVED":
        reason = "Runner removed from market"
        I(f"[{unique_id}] {reason}")
        if row["has_bet"]:
            return None, row["market_id"], (unique_id, reason)
        return None, None, (unique_id, reason)

    # 8-to-<8 runner rule - only affects PLACE bets
    if _check_8_to_less_than_8(row):
        reason = f"8→{int(row['current_runners'])} runners - PLACE bet invalid"
        I(f"[{unique_id}] {reason}")
        if row["has_bet"]:
            return None, row["market_id"], (unique_id, reason)
        return None, None, (unique_id, reason)

    # Short price removal check
    short_price_reason = _check_short_price_removal(row)
    if short_price_reason:
        I(f"[{unique_id}] {short_price_reason}")
        if row["has_bet"]:
            return None, row["market_id"], (unique_id, short_price_reason)
        return None, None, (unique_id, short_price_reason)

    # Price drift check - don't place new bets if price has drifted too far
    if not row["has_bet"]:
        drift_reason = _check_price_drift(row)
        if drift_reason:
            D(f"[{unique_id}] {drift_reason} - waiting")
            return None, None, None  # Don't invalidate, just wait

    # All checks passed - create order if we haven't bet yet
    if not row["has_bet"]:
        order = _create_order(row)
        I(
            f"[{unique_id}] Creating order: {row['selection_type']} {row['market_type']} @ {row['requested_odds']} stake={row['calculated_stake']}"
        )
        return order, None, None

    # We have a bet and it's still valid - nothing to do
    D(f"[{unique_id}] Has bet, still valid, waiting for match")
    return None, None, None


def _check_8_to_less_than_8(row: pd.Series) -> bool:
    """Check if runners dropped from exactly 8 to less than 8 (invalidates PLACE bets)."""
    if row["market_type"] != "PLACE":
        return False

    original = row.get("original_runners")
    current = row.get("current_runners")

    if pd.isna(original) or pd.isna(current):
        return False

    return original == 8 and current < 8


def _check_short_price_removal(row: pd.Series) -> str | None:
    """
    Check if a short-priced horse has been removed from the market.

    If a horse with odds < 12 is removed, the market dynamics change significantly
    and all bets in that race should be invalidated.

    Returns:
        Reason string if invalidation needed, None otherwise
    """
    # This would require checking other runners in the same race
    # For now, we handle the simple case where our selection is removed
    # The full implementation would need market-level data
    # TODO: Implement full short-price removal check with market context
    return None


def _check_price_drift(row: pd.Series) -> str | None:
    """
    Check if price has drifted beyond acceptable tolerance.

    For BACK bets: current_back_price should be >= requested_odds * (1 - tolerance)
    For LAY bets: current_lay_price should be <= requested_odds * (1 + tolerance)

    Returns:
        Reason string if price has drifted too far, None if acceptable
    """
    selection_type = row["selection_type"]
    requested = row["requested_odds"]

    if selection_type == "BACK":
        current = row.get("current_back_price")
        if pd.isna(current):
            return "No current back price available"

        min_acceptable = requested * (1 - BACK_DRIFT_TOLERANCE)
        if current < min_acceptable:
            return f"Back price drifted: {current} < {min_acceptable:.2f} (requested {requested})"

    else:  # LAY
        current = row.get("current_lay_price")
        if pd.isna(current):
            return "No current lay price available"

        max_acceptable = requested * (1 + LAY_DRIFT_TOLERANCE)
        if current > max_acceptable:
            return f"Lay price drifted: {current} > {max_acceptable:.2f} (requested {requested})"

    return None


def _create_order(row: pd.Series) -> BetFairOrder:
    """Create a BetFairOrder from a view row."""
    return BetFairOrder(
        size=float(row["calculated_stake"]),
        price=float(row["requested_odds"]),
        selection_id=str(int(row["selection_id"])),
        market_id=str(row["market_id"]),
        side=row["selection_type"],
        strategy=row.get("customer_strategy_ref", "trader"),
    )
