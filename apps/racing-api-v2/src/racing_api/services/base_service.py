import hashlib

import pandas as pd

from ..models.horse_race_info import RaceDataResponse, RaceDataRow
from ..models.race_details import RaceDetailsResponse
from ..models.race_form import RaceForm, RaceFormResponse
from ..models.race_form_graph import RaceFormGraph, RaceFormGraphResponse
from ..repository.base_repository import BaseRepository


class BaseService:
    def __init__(
        self,
        repository: BaseRepository,
    ):
        self.repository = repository

    async def get_horse_race_info(self, race_id: int) -> RaceDataResponse:
        """Get horse race information by race ID"""
        data = await self.repository.get_horse_race_info(race_id)
        race_data = [RaceDataRow(**row.to_dict()) for _, row in data.iterrows()]
        return RaceDataResponse(race_id=race_id, data=race_data)

    async def get_race_details(self, race_id: int) -> RaceDetailsResponse:
        """Get race details by race ID"""
        data = await self.repository.get_race_details(race_id)
        if data.empty:
            return None
        return RaceDetailsResponse(**data.iloc[0].to_dict())

    async def get_race_form_graph(self, race_id: int) -> RaceFormGraphResponse:
        """Get race form graph data by race ID"""
        data = await self.repository.get_race_form_graph(race_id)
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
        data = await self.repository.get_race_form(race_id)
        return RaceFormResponse(
            race_id=race_id,
            data=[RaceForm(**row.to_dict()) for _, row in data.iterrows()],
        )
