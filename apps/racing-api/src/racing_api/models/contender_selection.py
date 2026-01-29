from __future__ import annotations

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class ContenderSelection(BaseModel):
    horse_id: int
    horse_name: str
    race_id: int
    race_date: date
    race_time: Optional[str] = None
    selection_id: Optional[int] = None
    contender: bool
    timestamp: datetime


class ContenderSelectionResponse(BaseModel):
    success: bool
    message: str


class ContenderValue(BaseModel):
    horse_id: int
    horse_name: str
    betfair_sp: float
    equal_prob: float
    normalized_market_prob: float
    adjusted_prob: float
    adjusted_odds: float
    value_percentage: float


class ContenderValuesResponse(BaseModel):
    race_id: int
    contender_count: int
    total_runners: int
    values: List[ContenderValue]
