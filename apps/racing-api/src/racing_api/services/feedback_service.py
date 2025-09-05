from fastapi import Depends

from ..models.betting_selections import BettingSelection

from ..models.feedback_date import FeedbackDate
from ..models.race_result import HorsePerformance, RaceResult, RaceResultsResponse
from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.feedback_repository import FeedbackRepository, get_feedback_repository
from .base_service import BaseService


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
        print(f"Storing betting selections: {selections}")
        market_state = await self._create_market_state(selections)
        selections = await self._create_selections(selections)

        await self.feedback_repository.store_betting_selections(
            selections, market_state
        )

    async def _create_market_state(self, selections: BettingSelection) -> list[dict]:
        """Create market state from betting selections"""
        market_state = []
        for runner in selections.market_state:
            market_state.append(
                {
                    "horse_id": runner.horse_id,
                    "betfair_win_sp": runner.betfair_win_sp,
                    "selection_id": runner.selection_id,
                }
            )
        return market_state

    async def _create_selections(self, selections: BettingSelection) -> list[dict]:
        """Create selections from betting selections"""
        return [
            {
                "horse_id": selections.horse_id,
                "market_id_win": selections.market_id_win,
                "market_id_place": selections.market_id_place,
                "number_of_runners": selections.number_of_runners,
                "race_date": selections.race_date,
                "race_id": selections.race_id,
                "ts": selections.ts,
            }
        ]


def get_feedback_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
):
    return FeedbackService(feedback_repository)
