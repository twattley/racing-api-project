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


class BettingSelection(BaseModel):
    bet_type: BetType
    clicked: Optional[Clicked] = None
    horse_id: int
    market_id_win: Optional[int] = None
    market_id_place: Optional[int] = None
    market_state: List[MarketRunner] = Field(default_factory=list)
    number_of_runners: int
    race_date: date
    race_id: int
    ts: datetime
