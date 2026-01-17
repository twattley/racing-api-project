from datetime import datetime
from typing import Optional

from fastapi import Depends

from ..models.betting_selections import BettingSelection
from ..models.contender_selection import (
    ContenderSelection,
    ContenderSelectionResponse,
    ContenderValue,
    ContenderValuesResponse,
)
from ..models.live_bets_status import BetStatusRow, LiveBetStatus, RanData, ToRunData
from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..models.void_bet_request import VoidBetRequest
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

    async def store_contender_selection(
        self, selection: ContenderSelection
    ) -> ContenderSelectionResponse:
        """Store a contender selection"""
        now = datetime.now()
        payload = {
            "horse_id": selection.horse_id,
            "horse_name": selection.horse_name,
            "race_id": selection.race_id,
            "race_date": selection.race_date,
            "race_time": selection.race_time,
            "status": selection.status,
            "created_at": now,
            "updated_at": now,
        }
        await self.todays_repository.store_contender_selection(payload)
        return ContenderSelectionResponse(
            success=True,
            message=f"Stored {selection.status} selection for {selection.horse_name}",
        )

    async def get_contender_selections_by_race(self, race_id: int) -> list[dict]:
        """Get all contender selections for a race"""
        df = await self.todays_repository.get_contender_selections_by_race(race_id)
        if df.empty:
            return []
        return df.to_dict("records")

    async def delete_contender_selection(
        self, race_id: int, horse_id: int
    ) -> ContenderSelectionResponse:
        """Delete a contender selection"""
        await self.todays_repository.delete_contender_selection(horse_id, race_id)
        return ContenderSelectionResponse(
            success=True,
            message=f"Deleted selection for horse {horse_id} in race {race_id}",
        )

    async def get_contender_values(self, race_id: int) -> ContenderValuesResponse:
        """
        Calculate value percentages for contenders in a race.

        Methodology:
        1. Equal probability: 1 / num_contenders
        2. Normalized market probability: (1 / betfair_sp) / sum_of_contender_probs
        3. Adjusted probability: (equal_prob + normalized_market_prob) / 2
        4. Adjusted odds: 1 / adjusted_prob
        5. Value percentage: ((betfair_sp - adjusted_odds) / adjusted_odds) * 100
        """
        # Get race data with horse SPs
        race_info, _ = await self.get_horse_race_info(race_id)
        horses = race_info.data if race_info else []

        # Get contender selections
        selections_df = await self.todays_repository.get_contender_selections_by_race(
            race_id
        )
        contender_horse_ids = set()
        if not selections_df.empty:
            contender_horse_ids = set(
                selections_df[selections_df["status"] == "contender"][
                    "horse_id"
                ].tolist()
            )

        # Filter to contenders with valid SPs
        contenders = []
        for h in horses:
            if h.horse_id in contender_horse_ids:
                sp = float(h.betfair_win_sp) if h.betfair_win_sp else 0
                if sp > 0:
                    contenders.append(
                        {
                            "horse_id": h.horse_id,
                            "horse_name": h.horse_name,
                            "betfair_sp": sp,
                        }
                    )

        if not contenders:
            return ContenderValuesResponse(
                race_id=race_id,
                contender_count=0,
                total_runners=len(horses),
                values=[],
            )

        num_contenders = len(contenders)
        equal_prob = 1 / num_contenders

        # Calculate sum of contender probabilities for normalization
        sum_contender_probs = sum(1 / c["betfair_sp"] for c in contenders)

        # Calculate value for each contender
        values = []
        for c in contenders:
            sp = c["betfair_sp"]
            market_prob = 1 / sp
            normalized_market_prob = market_prob / sum_contender_probs
            adjusted_prob = (equal_prob + normalized_market_prob) / 2
            adjusted_odds = 1 / adjusted_prob
            value_percentage = ((sp - adjusted_odds) / adjusted_odds) * 100

            values.append(
                ContenderValue(
                    horse_id=c["horse_id"],
                    horse_name=c["horse_name"],
                    betfair_sp=round(sp, 2),
                    equal_prob=round(equal_prob * 100, 1),
                    normalized_market_prob=round(normalized_market_prob * 100, 1),
                    adjusted_prob=round(adjusted_prob * 100, 1),
                    adjusted_odds=round(adjusted_odds, 2),
                    value_percentage=round(value_percentage, 0),
                )
            )

        return ContenderValuesResponse(
            race_id=race_id,
            contender_count=num_contenders,
            total_runners=len(horses),
            values=values,
        )


def get_todays_service(
    todays_repository: TodaysRepository = Depends(get_todays_repository),
):
    return TodaysService(todays_repository)
