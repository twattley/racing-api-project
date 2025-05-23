from .base_entity import BaseEntity


class DateRequest(BaseEntity):
    date: str


class TodaysFeedbackDateResponse(BaseEntity):
    today_date: str
    success: bool
    message: str
