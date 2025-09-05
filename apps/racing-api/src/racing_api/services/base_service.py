import hashlib
from typing import Optional

import pandas as pd

from racing_api.models.race_form_graph import RaceFormGraph, RaceFormGraphResponse

from ..models.race_details import RaceDetailsResponse
from ..repository.base_repository import BaseRepository
from ..models.race_form import RaceForm, RaceFormResponse, RaceFormResponseFull

from ..models.horse_race_info import RaceDataResponse, RaceDataRow


class BaseService:
    def __init__(
        self,
        repository: BaseRepository,
    ):
        self.repository = repository

    async def get_horse_race_info(self, race_id: int) -> pd.DataFrame:
        """Get horse race information by race ID"""
        data = await self.repository.get_horse_race_info(race_id)
        race_info = RaceDataResponse(
            race_id=race_id,
            data=[RaceDataRow(**row.to_dict()) for _, row in data.iterrows()],
        )
        active_runners = data[data["status"] == "ACTIVE"]["horse_id"].tolist()
        return race_info, active_runners

    async def get_race_details(self, race_id: int) -> RaceDetailsResponse:
        """Get race details by race ID"""
        data = await self.repository.get_race_details(race_id)
        if data.empty:
            return None
        return RaceDetailsResponse(**data.iloc[0].to_dict())

    async def get_race_form_graph(
        self, race_id: int, active_runners: list
    ) -> pd.DataFrame:
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
        active_runners_graph = data[data["horse_id"].isin(active_runners)]

        form_data = [
            RaceFormGraph(**row.to_dict()) for _, row in active_runners_graph.iterrows()
        ]
        return RaceFormGraphResponse(race_id=race_id, data=form_data)

    async def get_race_form(self, race_id: int, active_runners: list) -> pd.DataFrame:
        """Get race form data by race ID"""
        data = await self.repository.get_race_form(race_id)
        active_race_form = data[data["horse_id"].isin(active_runners)]

        return RaceFormResponse(
            race_id=race_id,
            data=[RaceForm(**row.to_dict()) for _, row in active_race_form.iterrows()],
        )

    async def get_full_race_data(self, race_id: str) -> Optional[RaceFormResponseFull]:

        race_info, active_runners = self.get_horse_race_info(race_id)
        race_form = self.get_race_form(race_id, active_runners)
        race_form_graph = self.get_race_form_graph(race_id, active_runners)
        race_details = self.get_race_details(race_id)

        return RaceFormResponseFull(
            race_form=race_form,
            race_info=race_info,
            race_form_graph=race_form_graph,
            race_details=race_details,
        )

    def _format_todays_races(self, data: pd.DataFrame) -> pd.DataFrame:
        return (
            data.assign(
                race_class=data["race_class"].fillna(0).astype(int).replace(0, None),
                hcap_range=data["hcap_range"].fillna(0).astype(int).replace(0, None),
                betfair_win_sp=data["betfair_win_sp"].round(1),
            )
            .pipe(self._add_all_skip_flags)
            .drop_duplicates(subset=["race_id"])
        )

    def _add_all_skip_flags(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add all skip flag conditions as separate columns, then combine into final skip_flag"""
        races_to_ignore = [
            "shergar",
            "maiden",
            "novice",
            "hurdle",
            "chase",
            "hunter",
            "heritage",
            "bumper",
            "racing league",
            "lady riders",
        ]

        # Flag 1: Race title contains ignored words
        data["skip_race_type"] = (
            data["race_title"]
            .str.lower()
            .str.contains("|".join(races_to_ignore), na=False)
        )

        # Flag 2: Minimum SP per race > 4
        min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
        data["skip_min_sp"] = data["race_id"].map(min_sp_per_race > 4)

        # Flag 3: >10 runners AND favorite > 4
        min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
        max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
        condition = (max_runners_per_race > 10) & (min_sp_per_race > 4)
        data["skip_runners_fav"] = data["race_id"].map(condition)

        # Flag 4: Races with ≤4 runners
        max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
        data["skip_few_runners"] = data["race_id"].map(max_runners_per_race <= 4)

        # Flag 5: Minimum SP per race ≤ 2.5
        min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
        data["skip_short_price"] = data["race_id"].map(min_sp_per_race <= 2.28)

        # Flag 6: Races where all horses are 2 years old
        max_age_per_race = data.groupby("race_id")["age"].max()
        data["skip_all_two_year_olds"] = data["race_id"].map(max_age_per_race == 2)

        # Flag 7: Races where all horses are 3 years old AND more than 8 runners
        max_age_per_race = data.groupby("race_id")["age"].max()
        max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
        condition = (max_age_per_race == 3) & (max_runners_per_race > 8)
        data["skip_all_three_year_olds_big_field"] = data["race_id"].map(condition)

        # Final skip flag: True if ANY of the conditions are True
        data["skip_flag"] = (
            data["skip_race_type"]
            | data["skip_min_sp"]
            | data["skip_runners_fav"]
            | data["skip_few_runners"]
            | data["skip_short_price"]
            | data["skip_all_two_year_olds"]
            | data["skip_all_three_year_olds_big_field"]
        )
        return data.drop(
            columns=[
                "skip_race_type",
                "skip_min_sp",
                "skip_runners_fav",
                "skip_few_runners",
                "skip_short_price",
                "skip_all_two_year_olds",
                "skip_all_three_year_olds_big_field",
            ]
        ).drop_duplicates(subset=["race_id"])
