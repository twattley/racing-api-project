from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import Field

from .base_model import BaseRaceModel


class LiveBetStatus(BaseRaceModel):
    ran: Optional[RanData]
    to_run: Optional[ToRunData]


class RanData(BaseRaceModel):
    list: list[BetStatusRow] = Field(
        default_factory=list, description="List of betting status rows"
    )


class ToRunData(BaseRaceModel):
    list: list[BetStatusRow] = Field(
        default_factory=list, description="List of betting status rows"
    )


class BetStatusRow(BaseRaceModel):
    """Model for a single row returned by the live bets status query"""

    unique_id: str
    race_id: int
    race_time: datetime
    race_date: date
    horse_id: int
    horse_name: str
    selection_type: str
    market_type: str
    market_id: str
    selection_id: int
    requested_odds: float
    valid: bool
    invalidated_at: Optional[datetime] = None
    invalidated_reason: Optional[str] = None
    size_matched: float
    average_price_matched: Optional[float] = None
    cashed_out: bool
    fully_matched: bool
    customer_strategy_ref: str
    created_at: datetime
    processed_at: datetime
    bet_outcome: str
    event_id: Optional[float] = None
    price_matched: Optional[float] = None
    profit: Optional[float] = None
    commission: Optional[float] = None
    side: str
