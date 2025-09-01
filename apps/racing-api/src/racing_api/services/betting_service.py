from datetime import date
from fastapi import Depends

from ..repository.todays_repository import TodaysRepository, get_todays_repository
from ..models.betting_selections import BettingSelection
from ..repository.feedback_repository import FeedbackRepository, get_feedback_repository
from .base_service import BaseService


class BettingService(BaseService):
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
        todays_repository: TodaysRepository,
    ):
        super().__init__(feedback_repository)
        self.feedback_repository = feedback_repository
        self.todays_repository = todays_repository

    async def store_betting_selections(self, selections: BettingSelection) -> None:
        """Store betting selections"""
        race_date = selections.race_date
        if race_date == date.today():
            print(f"Storing today's betting selections: {selections}")
            # await self.todays_repository.store_betting_selections(selections)
        else:
            print(f"Storing feedback betting selections: {selections}")
            # await self.feedback_repository.store_betting_selections(selections)


def get_betting_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
    todays_repository: TodaysRepository = Depends(get_todays_repository),
):
    return BettingService(feedback_repository, todays_repository)
