from fastapi import Depends

from ..models.betting_selections import BettingSelection

from ..models.feedback_date import FeedbackDate
from ..models.race_result import HorsePerformance, RaceResult, RaceResultsResponse
from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.feedback_repository import FeedbackRepository, get_feedback_repository
from .base_service import BaseService, BetRequest
from datetime import datetime
import pandas as pd


class FeedbackService(BaseService):
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
    ):
        super().__init__(feedback_repository)
        self.feedback_repository = feedback_repository

    async def get_todays_race_times(self) -> RaceTimesResponse:
        """Get today's race times"""
        data = await self.feedback_repository.get_todays_race_times()
        data = self._format_todays_races(data)
        races = []
        for course in data["course"].unique():
            course_races = data[data["course"] == course]
            races.append(
                {
                    "course": course,
                    "races": [
                        RaceTimeEntry(**row.to_dict())
                        for _, row in course_races.iterrows()
                    ],
                }
            )
        return RaceTimesResponse(data=races)

    async def get_current_date_today(self) -> FeedbackDate:
        """Get current feedback date"""
        data = await self.feedback_repository.get_current_date_today()
        if data.empty:
            return FeedbackDate()
        return FeedbackDate(**data.iloc[0].to_dict())

    async def store_current_date_today(self, date: str):
        """Store current date"""
        return await self.feedback_repository.store_current_date_today(date)

    async def get_race_result(self, race_id: int) -> RaceResultsResponse:
        """Get race results by race ID"""
        race_data = await self.feedback_repository.get_race_result_info(race_id)
        performance_data = (
            await self.feedback_repository.get_race_result_horse_performance_data(
                race_id
            )
        )
        return RaceResultsResponse(
            race_id=race_id,
            race_data=RaceResult(**race_data.to_dict("records")[0]),
            horse_performance_data=[
                HorsePerformance(**row.to_dict())
                for _, row in performance_data.iterrows()
            ],
        )

    async def store_betting_selections(self, selections: BettingSelection) -> None:
        """Store betting selections"""
        unique_id = self.create_unique_bet_request_id(
            BetRequest(
                race_id=selections.race_id,
                horse_id=selections.horse_id,
                bet_type=selections.bet_type.back_lay,
                market=selections.bet_type.market,
                selection_id="feedback",
                market_id="feedback",
            )
        )
        selections = self._create_selections(selections, unique_id)

        await self.feedback_repository.store_betting_selections(selections)

    def _create_selections(self, selections: BettingSelection, unique_id: str) -> dict:
        """Create selections from betting selections"""

        extra_fields = {
            "valid": True,
            "invalidated_at": None,
            "invalidated_reason": "",
            "size_matched": 0.0,
            "average_price_matched": selections.clicked.price,
            "fully_matched": False,
            "cashed_out": False,
            "customer_strategy_ref": "selection",
        }
        base_fields = {
            "unique_id": unique_id,
            "race_id": selections.race_id,
            "race_time": selections.race_time,
            "race_date": selections.race_date,
            "horse_id": selections.horse_id,
            "horse_name": selections.horse_name,
            "selection_id": selections.selection_id,
            "selection_type": selections.bet_type.back_lay.upper(),
            "market_type": selections.bet_type.market.upper(),
            "processed_at": selections.ts,
            "requested_odds": selections.clicked.price,
            "market_id": "feedback",
            "created_at": datetime.now(),
            "processed_at": datetime.now(),
        }

        return {
            **base_fields,
            **extra_fields,
        }


def get_feedback_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
):
    return FeedbackService(feedback_repository)
