from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class BetType(BaseModel):
    back_lay: Literal["back", "lay"]
    market: str


class Clicked(BaseModel):
    price: Optional[Decimal] = None
    type: Optional[str] = None


class MarketRunner(BaseModel):
    horse_id: int
    betfair_win_sp: Optional[Decimal] = None
    selection_id: Optional[int] = None


class BettingSelection(BaseModel):
    bet_type: BetType
    clicked: Optional[Clicked] = None
    horse_id: int
    market_id_win: Optional[str] = None
    market_id_place: Optional[str] = None
    selection_id: Optional[int] = None
    market_state: List[MarketRunner] = Field(default_factory=list)
    number_of_runners: int
    race_date: date
    race_time: datetime
    race_id: int
    ts: datetime
