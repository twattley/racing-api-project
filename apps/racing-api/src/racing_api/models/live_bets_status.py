from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from .base_model import BaseRaceModel


class LiveBetStatus(BaseRaceModel):
    ran: RanData
    to_run: ToRunData


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
    invalidated_at: Optional[datetime]
    invalidated_reason: Optional[str]
    size_matched: float
    average_price_matched: Optional[float]
    cashed_out: bool
    fully_matched: bool
    customer_strategy_ref: str
    created_at: datetime
    processed_at: datetime
    bet_outcome: str
    event_id: Optional[float]
    price_matched: Optional[float]
    profit: Optional[float]
    commission: Optional[float]
    side: str
