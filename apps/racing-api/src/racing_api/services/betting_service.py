from datetime import date
from fastapi import Depends
import numpy as np
import pandas as pd
from ..models.betting_selections import BettingSelection
from .base_service import BaseService
from .feedback_service import FeedbackService, get_feedback_service
from .todays_service import TodaysService, get_todays_service

SLIPPAGE = 0.9


class BettingService(BaseService):
    def __init__(
        self,
        feedback_service: FeedbackService,
        todays_service: TodaysService,
    ):
        super().__init__(feedback_service)
        self.feedback_service = feedback_service
        self.todays_service = todays_service

    async def store_betting_selections(self, selections: BettingSelection) -> None:
        """Store betting selections"""
        race_date = selections.race_date
        if race_date == date.today():
            await self.todays_service.store_betting_selections(selections)
        else:
            await self.feedback_service.store_betting_selections(selections)

    async def get_betting_selections_analysis(self):
        data = await self.betting_repository.get_betting_selections_analysis()
        data = data.pipe(self._calculate_betting_analysis)

        return data

    def _calculate_betting_analysis(self, data: pd.DataFrame) -> dict:
        data = data.assign(
            betfair_win_sp=lambda x: x["betfair_win_sp"].astype(float),
            betfair_place_sp=lambda x: x["betfair_place_sp"].astype(float),
        )

        data = self._calculate_win_place_flags(data)
        data = self._calculate_bet_results(data)
        data = self._add_betting_metrics(data)
        data = data.sort_values(by=["created_at"], ascending=False)

        overall_analysis = self._calculate_overall_analysis(data)

        return {
            **overall_analysis,
            "result_dict": self.sanitize_nan(
                data.sort_values(by=["created_at"], ascending=False).to_dict(
                    orient="records"
                )
            ),
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
        data_sorted = data.sort_values(["created_at"])

        return data_sorted.assign(
            bet_number=range(1, len(data_sorted) + 1),
            running_total=data_sorted["bet_result"].cumsum(),
        )

    def _calculate_overall_analysis(self, data: pd.DataFrame) -> dict:
        data = data.sort_values(by=["created_at"])
        overall_total = data["running_total"].iloc[-1]
        number_of_bets = len(data)
        total_investment = number_of_bets * 1
        roi_percentage = (overall_total / total_investment) * 100

        return {
            "number_of_bets": number_of_bets,
            "bet_number": list(data["bet_number"]),
            "running_total": list(data["running_total"]),
            "overall_total": overall_total,
            "roi_percentage": roi_percentage,
        }


def get_betting_service(
    feedback_service: FeedbackService = Depends(get_feedback_service),
    todays_service: TodaysService = Depends(get_todays_service),
):
    return BettingService(feedback_service, todays_service)
