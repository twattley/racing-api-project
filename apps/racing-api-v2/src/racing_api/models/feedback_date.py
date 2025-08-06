from datetime import date
from typing import Optional

from pydantic import Field

from .base_model import BaseRaceModel


class DateRequest(BaseRaceModel):
    """Model for date request"""

    date: str = Field(..., description="Date in ISO format")


class FeedbackDate(BaseRaceModel):
    """Model for feedback date response"""

    today_date: Optional[date] = Field(None, description="Current feedback date")


class TodaysFeedbackDateResponse(BaseRaceModel):
    """Response model for today's feedback date"""

    today_date: str = Field(..., description="Today's date as string")
    success: bool = Field(True, description="Success status")
    message: str = Field("Date fetched successfully", description="Response message")
