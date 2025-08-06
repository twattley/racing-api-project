from fastapi import Depends

from ..models.feedback_date import FeedbackDate
from ..models.horse_race_info import RaceDataResponse, RaceDataRow
from ..models.race_details import RaceMetadata
from ..models.race_form import RaceForm, RaceFormResponse
from ..models.race_form_graph import RaceFormGraph, RaceFormGraphResponse
from ..models.race_result import RaceResult, RaceResultsResponse
from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.feedback_repository import FeedbackRepository, get_feedback_repository
from .base_service import BaseService


class FeedbackService(BaseService):
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
    ):
        self.feedback_repository = feedback_repository

    async def get_horse_race_info(self, race_id: int) -> RaceDataResponse:
        """Get horse race information by race ID"""
        data = await self.feedback_repository.get_horse_race_info(race_id)
        race_data = [RaceDataRow(**row.to_dict()) for _, row in data.iterrows()]
        return RaceDataResponse(race_id=race_id, data=race_data)

    async def get_race_details(self, race_id: int) -> RaceMetadata:
        """Get race details by race ID"""
        data = await self.feedback_repository.get_race_details(race_id)
        if data.empty:
            return None
        return RaceMetadata(**data.iloc[0].to_dict())

    async def get_race_form_graph(self, race_id: int) -> RaceFormGraphResponse:
        """Get race form graph data by race ID"""
        data = await self.feedback_repository.get_race_form_graph(race_id)
        form_data = [RaceFormGraph(**row.to_dict()) for _, row in data.iterrows()]
        return RaceFormGraphResponse(race_id=race_id, data=form_data)

    async def get_race_form(self, race_id: int) -> RaceFormResponse:
        """Get race form data by race ID"""
        data = await self.feedback_repository.get_race_form(race_id)
        form_data = [RaceForm(**row.to_dict()) for _, row in data.iterrows()]
        return RaceFormResponse(race_id=race_id, data=form_data)

    async def get_todays_race_times(self) -> RaceTimesResponse:
        """Get today's race times"""
        data = await self.feedback_repository.get_todays_race_times()
        race_times = [RaceTimeEntry(**row.to_dict()) for _, row in data.iterrows()]
        return RaceTimesResponse(data=race_times)

    async def get_current_date_today(self) -> FeedbackDate:
        """Get current feedback date"""
        data = await self.feedback_repository.get_current_date_today()
        if data.empty:
            return FeedbackDate()
        return FeedbackDate(**data.iloc[0].to_dict())

    async def store_current_date_today(self, date: str):
        """Store current date"""
        return await self.feedback_repository.store_current_date_today(date)

    async def get_race_result_by_id(self, race_id: int) -> RaceResultsResponse:
        """Get race results by race ID"""
        data = await self.feedback_repository.get_race_result_by_id(race_id)
        results = [RaceResult(**row.to_dict()) for _, row in data.iterrows()]
        return RaceResultsResponse(race_id=race_id, data=results)


def get_feedback_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
):
    return FeedbackService(feedback_repository)
