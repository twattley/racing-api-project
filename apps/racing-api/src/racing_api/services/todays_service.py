import asyncio
from dataclasses import dataclass
from typing import Optional
from fastapi import Depends
import numpy as np
import pandas as pd
import hashlib

from racing_api.models.race_form import RaceForm, RaceFormResponse, RaceFormResponseFull

from ..models.betting_selections import BettingSelection
from ..models.horse_race_info import RaceDataResponse, RaceDataRow

from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.todays_repository import TodaysRepository, get_todays_repository
from .base_service import BaseService


@dataclass
class BetRequest:
    race_id: str
    horse_id: str
    bet_type: str  # Literal['back', 'lay'] = Field(..., description
    market: str  # e.g., 'WIN' or 'PLACE'
    selection_id: int
    market_id: str


class TodaysService(BaseService):
    def __init__(
        self,
        todays_repository: TodaysRepository,
    ):
        super().__init__(todays_repository)
        self.todays_repository = todays_repository

    async def get_todays_race_times(self) -> Optional[RaceTimesResponse]:
        """Get today's race times"""
        data = await self.todays_repository.get_todays_race_times()
        if data.empty:
            return None
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

    async def store_betting_selections(self, selections: BettingSelection) -> None:
        """Store today's betting selections"""
        print(f"Storing betting selections: {selections}")
        if selections.bet_type.market.upper() == "WIN":
            market_id = selections.market_id_win
        else:
            market_id = selections.market_id_place
        unique_id = self._create_unique_bet_request_id(
            BetRequest(
                race_id=selections.race_id,
                horse_id=selections.horse_id,
                bet_type=selections.bet_type.back_lay,
                market=selections.bet_type.market,
                selection_id=selections.selection_id,
                market_id=market_id,
            )
        )
        market_state = self._create_market_state(selections, unique_id)
        selections = self._create_selections(selections, unique_id, market_id)
        await self.todays_repository.store_betting_selections(selections, market_state)

    async def get_full_race_data(self, race_id: str) -> Optional[RaceFormResponseFull]:

        race_info = self.get_horse_race_info(race_id)
        active_race_infos = race_info[race_info["status"] == "ACTIVE"]
        active_runners = active_race_infos["horse_id"].tolist()

        race_form = self.get_race_form(race_id)
        active_race_form = race_form[race_form["horse_id"].isin(active_runners)]

        race_form_graph = self.get_race_form_graph(race_id)
        active_race_form_graph = race_form_graph[
            race_form_graph["horse_id"].isin(active_runners)
        ]

        race_details = self.get_race_details(race_id)

        return RaceFormResponseFull(
            race_form=RaceFormResponse(
                race_id=race_id,
                data=[
                    RaceForm(**row.to_dict()) for _, row in active_race_form.iterrows()
                ],
            ),
            race_info=RaceDataResponse(
                race_id=race_id,
                data=[
                    RaceDataRow(**row.to_dict())
                    for _, row in active_race_infos.iterrows()
                ],
            ),
            race_form_graph=active_race_form_graph,
            race_details=race_details,
        )

    def _create_unique_bet_request_id(self, data: BetRequest) -> str:
        return hashlib.md5(
            (
                str(data.race_id)
                + "-"
                + str(data.horse_id)
                + "-"
                + str(data.bet_type)
                + "-"
                + str(data.market)
                + "-"
                + str(data.selection_id)
                + "-"
                + str(data.market_id)
            ).encode()
        ).hexdigest()

    def _create_market_state(
        self, selections: BettingSelection, unique_id: str
    ) -> list[dict]:
        """Create market state from betting selections"""
        return [
            {
                "bet_selection_id": selections.selection_id,
                "bet_type": selections.bet_type.back_lay.upper(),
                "market_type": selections.bet_type.market.upper(),
                "race_id": selections.race_id,
                "race_date": selections.race_date,
                "market_id_win": selections.market_id_win,
                "market_id_place": selections.market_id_place,
                "number_of_runners": selections.number_of_runners,
                "back_price_win": mr.betfair_win_sp,
                "horse_id": mr.horse_id,
                "selection_id": mr.selection_id,
                "created_at": selections.ts,
                "unique_id": unique_id,
            }
            for mr in selections.market_state
        ]

    def _create_selections(
        self, selections: BettingSelection, unique_id: str, market_id: str
    ) -> dict:
        """Create selections from betting selections"""

        extra_fields = {
            "valid": True,
            "invalidated_at": pd.NaT,
            "invalidated_reason": "",
            "size_matched": 0.0,
            "average_price_matched": np.nan,
            "fully_matched": False,
            "cashed_out": False,
            "customer_strategy_ref": "selection",
        }
        base_fields = {
            "unique_id": unique_id,
            "processed_at": selections.ts,
            "requested_odds": selections.clicked.price,
            "market_id": market_id,
            "unique_horse_id": int(selections.selection_id) * int(selections.horse_id),
            "selection_type": selections.bet_type.back_lay,
            "race_time": selections.race_time,
            "race_date": selections.race_date,
        }

        return {
            **base_fields,
            **extra_fields,
        }


def get_todays_service(
    todays_repository: TodaysRepository = Depends(get_todays_repository),
):
    return TodaysService(todays_repository)
