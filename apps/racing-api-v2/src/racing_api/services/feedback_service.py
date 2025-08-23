import hashlib
from fastapi import Depends
import pandas as pd

from ..models.feedback_date import FeedbackDate
from ..models.horse_race_info import RaceDataResponse, RaceDataRow
from ..models.race_details import RaceMetadata
from ..models.race_form import RaceForm, RaceFormResponse
from ..models.race_form_graph import RaceFormGraph, RaceFormGraphResponse
from ..models.race_result import HorsePerformance, RaceResult, RaceResultsResponse
from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.feedback_repository import FeedbackRepository, get_feedback_repository


class FeedbackService:
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
    ):
        self.feedback_repository = feedback_repository

    async def get_horse_race_info(self, race_id: int) -> RaceDataResponse:
        """Get horse race information by race ID"""
        await self.feedback_repository.get_horse_race_info(race_id)

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
        todays_race_date = data["todays_race_date"].iloc[0]
        data = data.sort_values(by=["horse_name", "race_date"])
        projected_data_dicts = []
        for horse in data["horse_name"].unique():
            horse_data = data[data["horse_name"] == horse][
                ["horse_name", "horse_id", "rating", "speed_figure"]
            ]
            if horse_data.empty:
                projected_data = {
                    "unique_id": hashlib.md5(
                        f"{horse}_{todays_race_date}_projected".encode()
                    ).hexdigest(),
                    "race_date": todays_race_date,
                    "horse_name": horse,
                    "horse_id": horse_data["horse_id"].iloc[0],
                    "rating": None,
                    "speed_figure": None,
                }
                projected_data_dicts.append(projected_data)
            else:
                projected_data = {
                    "unique_id": hashlib.md5(
                        f"{horse}_{todays_race_date}_projected".encode()
                    ).hexdigest(),
                    "race_date": todays_race_date,
                    "horse_name": horse,
                    "horse_id": horse_data["horse_id"].iloc[0],
                    "rating": horse_data["rating"].mean().round(0).astype(int),
                    "speed_figure": horse_data["speed_figure"]
                    .mean()
                    .round(0)
                    .astype(int),
                }
                projected_data_dicts.append(projected_data)
        projected_data = pd.DataFrame(projected_data_dicts)
        data = (
            pd.concat([data, projected_data], ignore_index=True)
            .drop(columns=["todays_race_date"])
            .sort_values(by=["horse_id", "race_date"])
        )
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
