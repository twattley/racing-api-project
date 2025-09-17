from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from fastapi import Depends
import numpy as np
import pandas as pd

from ..models.live_bets_status import BetStatusRow, LiveBetStatus, RanData, ToRunData
from ..models.void_bet_request import VoidBetRequest

from ..models.betting_selections import BettingSelection

from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.todays_repository import TodaysRepository, get_todays_repository
from .base_service import BaseService, BetRequest


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
        if selections.bet_type.market.upper() == "WIN":
            market_id = selections.market_id_win
        else:
            market_id = selections.market_id_place
        unique_id = self.create_unique_bet_request_id(
            BetRequest(
                race_id=selections.race_id,
                horse_id=selections.horse_id,
                market=selections.bet_type.market,
                selection_id=selections.selection_id,
                market_id=market_id,
                stake_points=selections.stake_points,
            )
        )
        market_state = self._create_market_state(selections, unique_id)
        selections = self._create_selections(selections, unique_id, market_id)
        await self.todays_repository.store_betting_selections(selections, market_state)

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
                "race_time": selections.race_time,
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
            "invalidated_at": None,
            "invalidated_reason": "",
            "size_matched": 0.0,
            "average_price_matched": None,
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
            "requested_odds ": selections.clicked.price,
            "stake_points": selections.stake_points,
            "selection_type": selections.bet_type.back_lay.upper(),
            "market_type": selections.bet_type.market.upper(),
            "processed_at": selections.ts,
            "requested_odds": selections.clicked.price,
            "market_id": market_id,
            "created_at": datetime.now(),
            "processed_at": datetime.now(),
        }

        return {
            **base_fields,
            **extra_fields,
        }

    async def get_live_betting_selections(self) -> LiveBetStatus:
        current_orders, past_orders = (
            await self.todays_repository.get_live_betting_selections()
        )
        # Build BetStatusRow lists from DataFrames and wrap in RanData/ToRunData
        ran_records = [
            {str(k): v for k, v in r.items()} for r in past_orders.to_dict("records")
        ]
        to_run_records = [
            {str(k): v for k, v in r.items()} for r in current_orders.to_dict("records")
        ]

        ran_list = [BetStatusRow(**row) for row in ran_records]
        to_run_list = [BetStatusRow(**row) for row in to_run_records]

        return LiveBetStatus(
            ran=RanData(list=ran_list),
            to_run=ToRunData(list=to_run_list),
        )

    async def void_betting_selection(self, void_request: VoidBetRequest) -> dict:
        """Cash out a specific betting selection using Betfair API and mark as invalid in database."""

        void_request_unique_id = self.create_void_bet_request_id(void_request)
        try:
            if void_request.size_matched > 0:
                void_request_data = void_request.to_dataframe()
                void_request_data["unique_id"] = void_request_unique_id
                await self.todays_repository.cash_out_bets_for_selection(
                    void_request=void_request_data,
                )
            await self.todays_repository.mark_selection_as_invalid(void_request)

            return {
                "success": True,
                "message": f"Successfully voided {void_request.selection_type} bet on {void_request.horse_name}"
                + (
                    f" (£{void_request.size_matched} matched)"
                    if void_request.size_matched > 0
                    else " (no money matched)"
                ),
                "betfair_cash_out": "Stored cash out request",
                "database_updated": True,
                "selection_id": void_request.selection_id,
                "market_id": void_request.market_id,
                "size_matched": void_request.size_matched,
            }

        except Exception as e:
            raise Exception(f"Void failed: {str(e)}")


def get_todays_service(
    todays_repository: TodaysRepository = Depends(get_todays_repository),
):
    return TodaysService(todays_repository)
