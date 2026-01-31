"""
Domain models for the trader.

These dataclasses represent the core data structures used throughout the trading system.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pandas as pd


class SelectionType(str, Enum):
    """Type of bet: back or lay."""

    BACK = "BACK"
    LAY = "LAY"


class MarketType(str, Enum):
    """Type of market: win or place."""

    WIN = "WIN"
    PLACE = "PLACE"


@dataclass
class SelectionState:
    """
    State of a single selection from v_selection_state view.

    This is the single source of truth for what the decision engine sees.
    All fields map directly to view columns.
    """

    # Identity
    unique_id: str
    race_id: int
    race_time: datetime
    race_date: datetime
    horse_id: int
    horse_name: str

    # Bet details
    selection_type: SelectionType
    market_type: MarketType
    requested_odds: float
    stake_points: float

    # Betfair identifiers
    market_id: str
    selection_id: int

    # Validation state
    valid: bool
    invalidated_reason: str | None

    # Original market snapshot
    original_runners: int
    original_price: float

    # Current live prices
    current_back_price: float | None
    current_lay_price: float | None

    # Runner status
    runner_status: str  # ACTIVE / REMOVED
    current_runners: int

    # Betting progress
    total_matched: float
    total_liability: float
    bet_count: int
    has_bet: bool
    has_pending_order: bool  # Order sitting on Betfair waiting to be matched
    fully_matched: bool

    # Calculated stake (from staking tiers)
    calculated_stake: float

    # Time-based
    minutes_to_race: float
    expires_at: datetime  # race_time - 2 hours (trading cutoff for view)

    # Validation flags (computed by view)
    short_price_removed: bool
    place_terms_changed: bool
    cash_out_requested: bool  # Manual void with matched money

    # Execution flags (computed by view)
    use_fill_or_kill: bool
    within_stake_limit: bool

    @classmethod
    def from_row(cls, row: pd.Series) -> "SelectionState":
        """Create SelectionState from a DataFrame row."""
        return cls(
            unique_id=row["unique_id"],
            race_id=row["race_id"],
            race_time=row["race_time"],
            race_date=row["race_date"],
            horse_id=row["horse_id"],
            horse_name=row["horse_name"],
            selection_type=SelectionType(row["selection_type"]),
            market_type=MarketType(row["market_type"]),
            requested_odds=float(row["requested_odds"]),
            stake_points=float(row.get("stake_points", 1.0) or 1.0),
            market_id=str(row["market_id"]),
            selection_id=int(row["selection_id"]),
            valid=bool(row["valid"]),
            invalidated_reason=row.get("invalidated_reason"),
            original_runners=int(row.get("original_runners", 0) or 0),
            original_price=float(row.get("original_price", 0) or 0),
            current_back_price=_to_float_or_none(row.get("current_back_price")),
            current_lay_price=_to_float_or_none(row.get("current_lay_price")),
            runner_status=row.get("runner_status", "ACTIVE") or "ACTIVE",
            current_runners=int(row.get("current_runners", 0) or 0),
            total_matched=float(row.get("total_matched", 0) or 0),
            total_liability=float(row.get("total_liability", 0) or 0),
            bet_count=int(row.get("bet_count", 0) or 0),
            has_bet=bool(row.get("has_bet", False)),
            has_pending_order=bool(row.get("has_pending_order", False)),
            fully_matched=bool(row.get("fully_matched", False)),
            calculated_stake=float(row.get("calculated_stake", 0) or 0),
            minutes_to_race=float(row.get("minutes_to_race", 60) or 60),
            expires_at=row["expires_at"],
            short_price_removed=bool(row.get("short_price_removed", False)),
            place_terms_changed=bool(row.get("place_terms_changed", False)),
            cash_out_requested=bool(row.get("cash_out_requested", False)),
            use_fill_or_kill=bool(row.get("use_fill_or_kill", False)),
            within_stake_limit=bool(row.get("within_stake_limit", True)),
        )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> list["SelectionState"]:
        """Convert DataFrame to list of SelectionState objects."""
        return [cls.from_row(row) for _, row in df.iterrows()]


def _to_float_or_none(value) -> float | None:
    """Convert value to float, returning None for NaN/None."""
    if value is None or pd.isna(value):
        return None
    return float(value)
