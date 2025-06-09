import json
from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import Depends

from ..models.betting_selections import (
    BetfairSelectionSubmission,
    BettingSelections,
    MarketState,
)
from ..repository.betting_repository import BettingRepository, get_betting_repository
from .base_service import BaseService


class BettingService(BaseService):
    def __init__(
        self,
        betting_repository: BettingRepository,
    ):
        self.betting_repository = betting_repository
        self._get_betting_session_id()

    def _get_betting_session_id(self):
        with open(
            "./racing_api/cache/betting_session.json",
            "r",
        ) as f:
            session_id = json.load(f)["session_id"]
            self.betting_session_id = int(session_id) + 1

    async def store_betting_selections(self, selections: BettingSelections):
        await self.betting_repository.store_betting_selections(
            selections, self.betting_session_id
        )

    async def store_live_betting_selections(
        self, selections: BetfairSelectionSubmission
    ):
        selection_data = self.create_selection_data(selections.selections)
        market_state_data = self.create_market_state_data(selections.market_state)
        await self.betting_repository.store_live_betting_selections(selection_data)
        await self.betting_repository.store_market_state(market_state_data)

    async def get_betting_selections_analysis(self):
        data = await self.betting_repository.get_betting_selections_analysis()
        data = data.pipe(self._calculate_betting_analysis)
        return data

    def _calculate_betting_analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            betfair_win_sp=lambda x: x["betfair_win_sp"].astype(float),
            betfair_place_sp=lambda x: x["betfair_place_sp"].astype(float),
        )

        data = self._calculate_win_place_flags(data)
        data = self._calculate_bet_results(data)
        data = self._add_betting_metrics(data)

        session_analysis = self._calculate_session_analysis(data)
        overall_analysis = self._calculate_overall_analysis(data)
        cum_sums = self._calculate_cumulative_sums(data)

        return {
            **overall_analysis,
            **session_analysis,
            "bet_type_cum_sum": cum_sums,
            "result_dict": self.sanitize_nan(data.to_dict(orient="records")),
        }

    def _calculate_win_place_flags(self, data: pd.DataFrame) -> pd.DataFrame:
        data["win"] = data["finishing_position"] == "1"
        data["place"] = (
            (data["number_of_runners"] < 8)
            & (data["finishing_position"].isin(["1", "2"]))
        ) | (
            (data["number_of_runners"] >= 8)
            & (data["finishing_position"].isin(["1", "2", "3"]))
        )
        return data

    def _calculate_bet_results(self, data: pd.DataFrame) -> pd.DataFrame:
        conditions = [
            (data["betting_type"] == "back_mid_price")
            & (data["finishing_position"] == "1"),
            (data["betting_type"] == "back_mid_price")
            & (data["finishing_position"] != "1"),
            (data["betting_type"] == "back_outsider")
            & (data["finishing_position"] == "1"),
            (data["betting_type"] == "back_outsider")
            & (data["finishing_position"] != "1"),
            (data["betting_type"] == "back_outsider_place") & data["place"],
            (data["betting_type"] == "back_outsider_place") & ~data["place"],
            (data["betting_type"] == "lay_favourite")
            & (data["finishing_position"] == "1"),
            (data["betting_type"] == "lay_favourite")
            & (data["finishing_position"] != "1"),
            (data["betting_type"] == "lay_mid_price_place") & data["place"],
            (data["betting_type"] == "lay_mid_price_place") & ~data["place"],
        ]

        SLIPPAGE = 0.9
        choices = [
            (data["betfair_win_sp"] * SLIPPAGE - 1),  # back mid price win
            -1,  # back mid price loss
            (data["betfair_win_sp"] * SLIPPAGE - 1),  # back outsider win
            -1,  # back outsider loss
            (data["betfair_place_sp"] * SLIPPAGE - 1),  # back outsider place win
            -1,  # back outsider place loss
            -1,  # lay favourite win
            ((1 / (data["betfair_win_sp"] - 1)) * SLIPPAGE),  # lay favourite loss
            -1,  # lay mid price place win
            (
                (1 / (data["betfair_place_sp"] - 1)) * SLIPPAGE
            ),  # lay mid price place loss
        ]

        return data.assign(
            bet_result=np.select(conditions, choices, default=0).round(2)
        )

    def _add_betting_metrics(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.sort_values(["betting_type", "created_at"])
        return data.assign(
            bet_number=data.groupby("betting_type").cumcount() + 1,
            running_total=data.groupby("betting_type")["bet_result"].cumsum(),
            overall_total=data["bet_result"].cumsum(),
        )

    def _calculate_session_analysis(self, data: pd.DataFrame) -> dict:
        session_results = data[data["session_id"] == self.betting_session_id]
        if len(session_results) > 0:
            session_results = session_results.assign(
                overall_total=session_results["bet_result"].cumsum()
            )
            return {
                "session_overall_total": session_results["overall_total"].iloc[-1],
                "session_number_of_bets": len(session_results),
            }
        return {
            "session_overall_total": 0,
            "session_number_of_bets": 0,
        }

    def _calculate_overall_analysis(self, data: pd.DataFrame) -> dict:
        overall_total = data["overall_total"].iloc[-1]
        number_of_bets = len(data)
        total_investment = number_of_bets * 1
        roi_percentage = (overall_total / total_investment) * 100

        return {
            "number_of_bets": number_of_bets,
            "overall_total": overall_total,
            "roi_percentage": roi_percentage,
        }

    def _calculate_cumulative_sums(self, data: pd.DataFrame) -> dict:
        cum_sums = {}
        for bet_type in data["betting_type"].unique():
            cum_sums[bet_type] = data[data["betting_type"] == bet_type][
                "bet_result"
            ].cumsum()
        cum_sums["overall_total"] = data["bet_result"].cumsum()
        return cum_sums

    def create_selection_data(
        self, selections: BetfairSelectionSubmission
    ) -> pd.DataFrame:
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

        data = pd.DataFrame([selection.dict() for selection in selections])
        if "combinedOdds" not in data.columns:
            data = data.assign(combinedOdds=np.nan, dutchGroupId=np.nan)

        data = data.assign(
            race_time=lambda x: pd.to_datetime(x["race_time"]),
            race_date=lambda x: pd.to_datetime(x["race_date"]),
            selection_type=lambda x: x["selection_type"].str.upper(),
            unique_horse_id=lambda x: x["selection_id"] * x["horse_id"],
            requested_odds=lambda x: x["combinedOdds"].fillna(x["adjusted_price"]),
            processed_at=datetime.now().replace(second=0, microsecond=0),
            **extra_fields,
        ).filter(
            items=[
                "id",
                "timestamp",
                "race_id",
                "race_time",
                "race_date",
                "horse_id",
                "horse_name",
                "selection_type",
                "market_type",
                "market_id",
                "selection_id",
                "requested_odds",
                "valid",
                "invalidated_at",
                "invalidated_reason",
                "size_matched",
                "average_price_matched",
                "cashed_out",
                "fully_matched",
                "customer_strategy_ref",
                "processed_at",
            ]
        )

        data = data.astype(
            {
                "id": str,
                "race_id": int,
                "horse_id": int,
                "horse_name": str,
                "selection_type": str,
                "market_type": str,
                "market_id": str,
                "selection_id": int,
                "requested_odds": float,
                "valid": bool,
                "invalidated_at": "datetime64[ns]",
                "size_matched": float,
                "average_price_matched": float,
                "cashed_out": bool,
                "fully_matched": bool,
                "invalidated_reason": str,
                "customer_strategy_ref": str,
                "processed_at": "datetime64[ns]",
            }
        )
        return data

    def create_market_state_data(self, market_state: MarketState) -> pd.DataFrame:
        win_data = pd.DataFrame(
            [
                {
                    "horse_name": price.horse_name,
                    "selection_id": price.selection_id,
                    "back_price": price.back_price,
                    "lay_price": price.lay_price,
                }
                for price in market_state.win
            ]
        )
        place_data = pd.DataFrame(
            [
                {
                    "horse_name": price.horse_name,
                    "selection_id": price.selection_id,
                    "back_price": price.back_price,
                    "lay_price": price.lay_price,
                }
                for price in market_state.place
            ]
        )
        data = pd.merge(
            win_data,
            place_data,
            on=["horse_name", "selection_id"],
            how="left",
            suffixes=("_win", "_place"),
        )
        data = data.assign(
            race_id=market_state.race_id,
            race_date=market_state.race_date,
            race_time=market_state.race_time,
            market_id_win=market_state.market_id_win,
            market_id_place=market_state.market_id_place,
            number_of_runners=len(data),
        )
        return data

    async def get_live_betting_selections(self) -> dict:
        data: pd.DataFrame = await self.betting_repository.get_live_betting_selections()
        if data.empty:
            return {"ran": [], "to_run": []}
        conditions = [
            data["cashed_out"] == True,
        ]

        data = data.assign(
            profit=np.select(conditions, [np.nan], default=data["profit"]),
            bet_outcome=np.select(
                [data["cashed_out"] == True, data["race_time"] > pd.Timestamp.now(tz='UTC')],
                ["CASHED_OUT", "TO_BE_RUN"],
                default=data["bet_outcome"],
            ),
            price_matched=np.select(
                conditions, [np.nan], default=data["price_matched"]
            ),
            side=np.select(conditions, ["CASHED_OUT"], default=data["side"]),
            commission=np.select(conditions, [np.nan], default=data["commission"]),
        )

        # Split data based on bet_outcome
        ran_data = data[data["bet_outcome"] != "TO_BE_RUN"]
        to_run_data = data[data["bet_outcome"] == "TO_BE_RUN"]

        return self.sanitize_nan(
            {
                "ran": self.sanitize_nan(ran_data.to_dict(orient="records")),
                "to_run": self.sanitize_nan(to_run_data.to_dict(orient="records")),
            }
        )


def get_betting_service(
    betting_repository: BettingRepository = Depends(get_betting_repository),
):
    return BettingService(betting_repository)
