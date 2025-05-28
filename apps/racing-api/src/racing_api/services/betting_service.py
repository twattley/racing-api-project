import json

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
        data = data.pipe(self._calculate_dutch_sum)
        return data

    def _calculate_dutch_sum(self, data: pd.DataFrame) -> pd.DataFrame:
        data["betfair_win_sp"] = data["betfair_win_sp"].astype(float)
        data["betfair_place_sp"] = data["betfair_place_sp"].astype(float)
        data["dutch_sum"] = (
            data[data["betting_type"].str.contains("dutch", case=False)]
            .groupby(["race_id", "betting_type"])["betfair_win_sp"]
            .transform(lambda x: (100.0 / x).sum())
        )
        data["calculated_odds"] = np.where(
            data["betting_type"].str.contains("dutch", case=False),
            100.0 / data["dutch_sum"],
            data["betfair_win_sp"].round(2),
        )

        grouped = (
            data.groupby(["race_id", "betting_type"])
            .agg(
                {
                    "calculated_odds": lambda x: (
                        x.max() if "dutch" in x.name.lower() else x.iloc[0]
                    ),
                    "betfair_win_sp": "first",
                }
            )
            .round(2)
            .reset_index()
        )
        grouped.columns = ["race_id", "betting_type", "final_odds", "betfair_win_sp"]
        result = data.merge(
            grouped, on=["race_id", "betting_type"], suffixes=("", "_grouped")
        )
        result["adjusted_final_odds"] = np.select(
            [
                result["betting_type"].str.contains("lay", case=False),
                result["betting_type"].str.contains("back", case=False),
            ],
            [result["final_odds"] * 1.2, result["final_odds"] * 0.8],
            default=result["final_odds"],
        ).round(2)

        result["win"] = result["finishing_position"] == "1"
        result["place"] = (
            (result["number_of_runners"] < 8)
            & (result["finishing_position"].isin(["1", "2"]))
        ) | (
            (result["number_of_runners"] >= 8)
            & (result["finishing_position"].isin(["1", "2", "3"]))
        )
        # fmt: off
        conditions = [
            (result["betting_type"] == "back_mid_price") & (result["finishing_position"] == "1"), # 1
            (result["betting_type"] == "back_mid_price") & (result["finishing_position"] != "1"), # 2
            (result["betting_type"] == "back_outsider") & (result["finishing_position"] == "1"), # 3
            (result["betting_type"] == "back_outsider") & (result["finishing_position"] != "1"), # 4
            (result["betting_type"] == "back_outsider_place") & result["place"], # 5
            (result["betting_type"] == "back_outsider_place") & ~result["place"], # 6
            (result["betting_type"] == "lay_favourite") & (result["finishing_position"] == "1"), # 7
            (result["betting_type"] == "lay_favourite") & (result["finishing_position"] != "1"), # 8
            (result["betting_type"] == "lay_mid_price_place") & result["place"], # 9
            (result["betting_type"] == "lay_mid_price_place") & ~result["place"], # 10
            (result["betting_type"] == "dutch_back") & (result["finishing_position"] == "1"), # 11
            (result["betting_type"] == "dutch_back") & (result["finishing_position"] != "1"), # 12
            (result["betting_type"] == "dutch_lay") & (result["finishing_position"] == "1"), # 13
            (result["betting_type"] == "dutch_lay") & (result["finishing_position"] != "1"), # 14
        ]
        SLIPPAGE = 0.9
        choices = [
            (result["final_odds"] * SLIPPAGE - 1).round(2), # 1 back mid price win
            -1, # 2 back mid price loss
            (result["final_odds"] * SLIPPAGE - 1).round(2), # 3 back outsider win
            -1, # 4 back outsider loss
            (result["betfair_place_sp"] * SLIPPAGE - 1).round(2), # 5 back outsider place win
            -1, # 6 back outsider place loss
            -1, # 7 lay favourite win (loss capped at 1.5)
            ((1/(result["betfair_win_sp"] - 1)) * SLIPPAGE ).round(2), # 8 lay favourite loss (loss capped at 1.5)
            -1, # 9 lay mid price place win you lose
            ((1/(result["betfair_place_sp"] - 1)) * SLIPPAGE ).round(2), # 10 lay mid price place loss you win 
            (result["final_odds"] * SLIPPAGE - 1).round(2), # 11 dutch back win
            -1, # 12 dutch back loss
            (-(result["final_odds"] * SLIPPAGE - 1)).round(2), # 13 dutch lay win
            SLIPPAGE, # 14 dutch lay loss
        ]
        # fmt: on

        result["bet_result"] = np.select(conditions, choices, default=0)

        dutch_back_results = (
            result[result["betting_type"] == "dutch_back"]
            .groupby("race_id")["bet_result"]
            .transform("max")
        )
        dutch_lay_results = (
            result[result["betting_type"] == "dutch_lay"]
            .groupby("race_id")["bet_result"]
            .transform("min")
        )

        result.loc[result["betting_type"] == "dutch_back", "bet_result"] = (
            dutch_back_results
        )
        result.loc[result["betting_type"] == "dutch_lay", "bet_result"] = (
            dutch_lay_results
        )
        result = result.assign(
            bet_result=result["bet_result"].astype(float),
        )
        result = result.sort_values(["betting_type", "created_at"])

        # First, separate dutch and non-dutch bets
        dutch_bets = result[result["betting_type"].str.contains("dutch", case=False)]
        non_dutch_bets = result[
            ~result["betting_type"].str.contains("dutch", case=False)
        ]
        # Drop duplicates for dutch bets
        dutch_bets_deduplicated = dutch_bets.drop_duplicates(
            subset=["race_id"], keep="first"
        )

        result = pd.concat([dutch_bets_deduplicated, non_dutch_bets]).sort_index()
        result = result.assign(
            bet_number=result.groupby("betting_type").cumcount() + 1,
            running_total=result.groupby("betting_type")["bet_result"].cumsum(),
            overall_total=result["bet_result"].cumsum(),
        )
        overall_total = result["overall_total"].iloc[-1]
        number_of_bets = len(result)
        total_investment = number_of_bets * 1
        roi_percentage = (overall_total / total_investment) * 100

        session_results = result[result["session_id"] == self.betting_session_id]
        session_results = session_results.assign(
            overall_total=session_results["bet_result"].cumsum()
        )
        if len(session_results) > 0:
            session_overall_total = session_results["overall_total"].iloc[-1]
            session_number_of_bets = len(session_results)
        else:
            session_overall_total = 0
            session_number_of_bets = 0

        cum_sums = {}
        for bet_type in result["betting_type"].unique():
            cum_sums[bet_type] = result[result["betting_type"] == bet_type][
                "bet_result"
            ].cumsum()

        cum_sums["overall_total"] = result["bet_result"].cumsum()
        result_dict = self.sanitize_nan(result.to_dict(orient="records"))

        return {
            "number_of_bets": number_of_bets,
            "overall_total": overall_total,
            "session_number_of_bets": session_number_of_bets,
            "roi_percentage": roi_percentage,
            "session_overall_total": session_overall_total,
            "bet_type_cum_sum": cum_sums,
            "result_dict": result_dict,
        }

    def create_selection_data(
        self, selections: BetfairSelectionSubmission
    ) -> pd.DataFrame:
        data = pd.DataFrame([selection.dict() for selection in selections])
        if "combinedOdds" not in data.columns:
            data = data.assign(combinedOdds=np.nan, dutchGroupId=np.nan)

        data = data.assign(
            race_time=lambda x: pd.to_datetime(x["race_time"]),
            race_date=lambda x: pd.to_datetime(x["race_date"]),
            selection_type=lambda x: x["selection_type"].str.upper(),
            unique_horse_id=lambda x: x["selection_id"] * x["horse_id"],
            request_id=lambda x: (
                x.groupby(["race_id", "market_id", "selection_type"])["unique_horse_id"]
                .transform("sum")
                .astype(int)
            ),
            requested_odds=lambda x: x["combinedOdds"].fillna(x["adjusted_price"]),
            valid=True,
            invalidated_at=pd.NaT,
            invalidated_reason="",
            size_matched=0.0,
            price_matched=np.nan,
            cashed_out=False,
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
                "request_id",
                "requested_odds",
                "valid",
                "invalidated_at",
                "invalidated_reason",
                "size_matched",
                "price_matched",
                "cashed_out",
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
                "request_id": int,
                "requested_odds": float,
                "valid": bool,
                "invalidated_at": "datetime64[ns]",
                "size_matched": float,
                "price_matched": float,
                "cashed_out": bool,
                "invalidated_reason": str,
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

    def get_live_betting_selections(self) -> pd.DataFrame:
        live_selections: pd.DataFrame = (
            self.betting_repository.get_live_betting_selections()
        )
        matched = live_selections[
            live_selections["execution_status"] == "EXECUTION_COMPLETE"
        ].assign(matched_status="matched")
        unmatched = live_selections[
            live_selections["execution_status"] != "EXECUTION_COMPLETE"
        ].assign(matched_status="unmatched")
        group_cols = ["race_id", "market_id", "selection_type", "selection_id"]
        matched["payoff"] = matched["size_matched"] * matched["average_price_matched"]
        matched["total_stake"] = matched.groupby(group_cols)["size_matched"].transform(
            "sum"
        )
        matched["total_odds"] = matched.groupby(group_cols)["payoff"].transform("sum")
        matched["ave_odds"] = (matched["total_odds"] / matched["total_stake"]).round(2)
        matched = matched.drop_duplicates(subset=group_cols)

        matched = matched[
            [
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
                "placed_date",
                "matched_date",
                "matched_status",
                "size_remaining",
                "total_stake",
                "ave_odds",
            ]
        ].rename(
            columns={"total_stake": "size_matched", "ave_odds": "average_price_matched"}
        )
        unmatched = unmatched[matched.columns]
        data = pd.concat([matched, unmatched])
        return self.sanitize_nan(data.to_dict(orient="records"))


def get_betting_service(
    betting_repository: BettingRepository = Depends(get_betting_repository),
):
    return BettingService(betting_repository)
