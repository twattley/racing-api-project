from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ContenderSelection(BaseModel):
    horse_id: int
    horse_name: str
    race_id: int
    race_date: date
    race_time: Optional[str] = None
    status: Literal["contender", "not-contender"]
    timestamp: datetime


class ContenderSelectionResponse(BaseModel):
    success: bool
    message: str
