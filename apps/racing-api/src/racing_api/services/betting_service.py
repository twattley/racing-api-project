from datetime import date
from fastapi import Depends

from ..models.betting_selections import BettingSelection
from .base_service import BaseService
from .feedback_service import FeedbackService, get_feedback_service
from .todays_service import TodaysService, get_todays_service


class BettingService(BaseService):
    def __init__(
        self,
        feedback_service: FeedbackService,
        todays_service: TodaysService,
    ):
        super().__init__(feedback_service)
        self.feedback_service = feedback_service
        self.todays_service = todays_service

    async def store_betting_selections(self, selections: BettingSelection) -> None:
        """Store betting selections"""
        race_date = selections.race_date
        if race_date == date.today():
            print(f"Storing today's betting selections: {selections}")
            await self.todays_service.store_betting_selections(selections)
        else:
            print(f"Storing feedback betting selections: {selections}")
            await self.feedback_service.store_betting_selections(selections)


def get_betting_service(
    feedback_service: FeedbackService = Depends(get_feedback_service),
    todays_service: TodaysService = Depends(get_todays_service),
):
    return BettingService(feedback_service, todays_service)
