from fastapi import Depends

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


def get_feedback_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
):
    return FeedbackService(feedback_repository)
