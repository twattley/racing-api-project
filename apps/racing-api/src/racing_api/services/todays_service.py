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
                bet_type=selections.bet_type.back_lay,
                market=selections.bet_type.market,
                selection_id=selections.selection_id,
                market_id=market_id,
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
        selections, past_orders, current_orders = (
            await self.todays_repository.get_live_betting_selections()
        )

        # Early exits
        if selections.empty:
            return LiveBetStatus(ran=RanData(list=[]), to_run=ToRunData(list=[]))

        # Only keep valid selections
        selections = selections[selections["valid"] == True].copy()
        if selections.empty:
            return LiveBetStatus(ran=RanData(list=[]), to_run=ToRunData(list=[]))

        # ---------- To Run: selections x current orders ----------
        to_run_df = pd.DataFrame()
        if not current_orders.empty:
            co = current_orders[
                current_orders["execution_status"] == "EXECUTION_COMPLETE"
            ].copy()
            if not co.empty:
                co = (
                    co.groupby(
                        ["market_id", "selection_id", "selection_type"], as_index=False
                    )
                    .agg({"size_matched": "sum", "average_price_matched": "mean"})
                    .round(2)
                )
                co = co.assign(
                    bet_outcome="TO_BE_RUN",
                    profit=np.where(
                        co["selection_type"].str.upper() == "BACK",
                        -co["size_matched"],
                        -co["size_matched"] * (co["average_price_matched"] - 1),
                    ),
                    commission=0,
                    price_matched=co["average_price_matched"],
                    side=co["selection_type"].str.upper(),
                )
                # Merge only rows that have current orders (inner join)
                to_run_df = (
                    selections.merge(
                        co[
                            [
                                "market_id",
                                "selection_id",
                                "bet_outcome",
                                "price_matched",
                                "profit",
                                "commission",
                                "side",
                                "size_matched",
                                "average_price_matched",
                            ]
                        ],
                        on=["market_id", "selection_id"],
                        how="inner",
                    )
                    .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
                    .reset_index(drop=True)
                )
                if not to_run_df.empty and "size_matched_x" in to_run_df.columns:
                    to_run_df = to_run_df.drop(
                        columns=["size_matched_x", "average_price_matched_x"]
                    ).rename(
                        columns={
                            "size_matched_y": "size_matched",
                            "average_price_matched_y": "average_price_matched",
                        }
                    )

        # ---------- Ran: selections x past orders ----------
        ran_df = pd.DataFrame()
        if not past_orders.empty:
            po = past_orders.copy()
            # Sum PnL at (event, market, selection) level
            po["grouped_pnl"] = po.groupby(["event_id", "market_id", "selection_id"])[
                "profit"
            ].transform("sum")
            po_pruned = (
                po[
                    [
                        "bet_outcome",
                        "event_id",
                        "market_id",
                        "price_matched",
                        "grouped_pnl",
                        "commission",
                        "selection_id",
                        "side",
                    ]
                ]
                .drop_duplicates(subset=["selection_id", "market_id"])
                .rename(columns={"grouped_pnl": "profit"})
            )
            ran_df = (
                selections.merge(
                    po_pruned,
                    on=["selection_id", "market_id"],
                    how="inner",
                )
                .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
                .reset_index(drop=True)
            )

            if not ran_df.empty and "size_matched_x" in ran_df.columns:
                ran_df = ran_df.drop(
                    columns=["size_matched_x", "average_price_matched_x"]
                ).rename(
                    columns={
                        "size_matched_y": "size_matched",
                        "average_price_matched_y": "average_price_matched",
                    }
                )

        # Build response
        ran_list = BetStatusRow.from_dataframe(ran_df) if not ran_df.empty else []
        to_run_list = (
            BetStatusRow.from_dataframe(to_run_df) if not to_run_df.empty else []
        )

        return LiveBetStatus(
            ran=RanData(list=ran_list), to_run=ToRunData(list=to_run_list)
        )

    async def void_betting_selection(self, void_request: VoidBetRequest) -> dict:
        """Cash out a specific betting selection using Betfair API and mark as invalid in database."""

        try:
            cash_out_result = None
            if void_request.size_matched > 0:

                cash_out_result = self.todays_repository.cash_out_bets_for_selection(
                    market_ids=[str(void_request.market_id)],
                    selection_ids=[str(void_request.selection_id)],
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
                "betfair_cash_out": (
                    cash_out_result.to_dict("records")
                    if cash_out_result is not None and not cash_out_result.empty
                    else []
                ),
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
