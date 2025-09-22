from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep
from typing import Literal

import betfairlightweight
import numpy as np
import pandas as pd
import requests
from api_helpers.helpers.logging_config import D, I
from api_helpers.helpers.time_utils import get_uk_time_now, make_uk_time_aware


@dataclass(frozen=True)
class BetFairCancelOrders:
    market_ids: list[str]


@dataclass(frozen=True)
class BetFairOrder:
    size: float
    price: float
    selection_id: str
    market_id: str
    side: str
    strategy: str


@dataclass
class BetfairCredentials:
    username: str
    password: str
    app_key: str
    certs_path: str


@dataclass
class BetfairHistoricalDataParams:
    from_day: int
    from_month: int
    from_year: int
    to_day: int
    to_month: int
    to_year: int
    market_types_collection: list[str]
    countries_collection: list[str]
    file_type_collection: list[str]


@dataclass
class OrderResult:
    success: bool
    message: str
    size_matched: float | None = None
    average_price_matched: float | None = None

    def __bool__(self) -> bool:
        """Allow the result to be used in boolean contexts"""
        return self.success


class BetFairCashOut:
    def cash_out(self, data: pd.DataFrame) -> list[BetFairOrder | None]:
        cash_out_orders = []
        for selection in data["selection_id"].unique():
            selection_df = data[data["selection_id"] == selection]
            if list(selection_df["selection_type"].unique()) == ["BACK", "LAY"]:
                cash_out_orders.extend(
                    self._handle_back_and_lay_matched_bets(selection_df)
                )
            elif list(selection_df["selection_type"].unique()) == ["BACK"]:
                cash_out_orders.extend(
                    self._handle_single_matched_back_bets(selection_df)
                )
            elif list(selection_df["selection_type"].unique()) == ["LAY"]:
                cash_out_orders.extend(
                    self._handle_single_matched_lay_bets(selection_df)
                )
            else:
                raise ValueError("Unidentified bet type")
        return cash_out_orders

    @staticmethod
    def _create_average_lay_odds(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            ave_lay_odds=(
                (
                    (data["lay_price_1"] * data["lay_price_1_depth"])
                    + (data["lay_price_2"] * data["lay_price_2_depth"])
                )
                / (data["lay_price_1_depth"] + data["lay_price_2_depth"])
            ).round(2),
        )
        return data

    @staticmethod
    def _create_average_back_odds(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            ave_back_odds=(
                (
                    (data["back_price_1"] * data["back_price_1_depth"])
                    + (data["back_price_2"] * data["back_price_2_depth"])
                )
                / (data["back_price_1_depth"] + data["back_price_2_depth"])
            ).round(2),
        )
        return data

    @staticmethod
    def _create_cash_out_odds(data: pd.DataFrame) -> pd.DataFrame:
        if "ave_back_odds" in data.columns and "ave_lay_odds" in data.columns:
            return data.assign(
                cash_out_odds=np.where(
                    data["selection_type"] == "BACK",
                    data["ave_back_odds"],
                    data["ave_lay_odds"],
                )
            )
        elif "ave_back_odds" not in data.columns and "ave_lay_odds" in data.columns:
            return data.assign(cash_out_odds=data["ave_lay_odds"])
        elif "ave_back_odds" in data.columns and "ave_lay_odds" not in data.columns:
            return data.assign(cash_out_odds=data["ave_back_odds"])
        else:
            raise ValueError("No average odds found")

    @staticmethod
    def _merge_back_and_lay_data(data: pd.DataFrame) -> pd.DataFrame:
        return pd.merge(
            data[data["selection_type"] == "BACK"][
                [
                    "market_id",
                    "selection_id",
                    "back_price_2",
                    "average_price_matched",
                    "size_matched",
                    "cash_out_odds",
                ]
            ],
            data[data["selection_type"] == "LAY"][
                [
                    "market_id",
                    "selection_id",
                    "lay_price_2",
                    "average_price_matched",
                    "size_matched",
                    "cash_out_odds",
                ]
            ],
            on=[
                "market_id",
                "selection_id",
            ],
            how="left",
            suffixes=["_back", "_lay"],
        )

    @staticmethod
    def _create_bet_side(data: pd.DataFrame) -> pd.DataFrame:
        return data.assign(
            lay_liability=(
                (data["average_price_matched_lay"] - 1) * data["size_matched_lay"]
            )
            - data["size_matched_back"],
            back_winnings=(
                (data["average_price_matched_back"] - 1) * data["size_matched_back"]
            )
            - data["size_matched_lay"],
            risk_diff=lambda x: x["back_winnings"] - x["lay_liability"],
            cash_out_selection_type=lambda x: np.where(
                x["risk_diff"] > 0, "LAY", "BACK"
            ),
        ).drop(columns=["risk_diff", "lay_liability", "back_winnings"])

    @staticmethod
    def _alternate_bet_side(data: pd.DataFrame) -> pd.DataFrame:
        return data.assign(
            cash_out_selection_type=np.where(
                data["selection_type"] == "LAY", "BACK", "LAY"
            ),
        )

    @staticmethod
    def _get_cash_out_stake_back_and_lay(data: pd.DataFrame) -> pd.DataFrame:
        return data.assign(
            cash_out_stake=np.select(
                [
                    data["cash_out_selection_type"] == "LAY",
                    data["cash_out_selection_type"] == "BACK",
                ],
                [
                    (
                        (
                            (
                                data["size_matched_back"]
                                * (data["average_price_matched_back"] - 1)
                                - data["size_matched_lay"]
                                * (data["average_price_matched_lay"] - 1)
                            )
                            + (data["size_matched_back"] - data["size_matched_lay"])
                        )
                        / data["cash_out_odds_lay"]
                    ).round(2),
                    (
                        (
                            (
                                data["size_matched_lay"]
                                * (data["average_price_matched_lay"] - 1)
                                - data["size_matched_back"]
                                * (data["average_price_matched_back"] - 1)
                            )
                            + (data["size_matched_lay"] - data["size_matched_back"])
                        )
                        / data["cash_out_odds_back"]
                    ).round(2),
                ],
                default=np.nan,
            ),
        )

    @staticmethod
    def _get_cash_out_stake(data: pd.DataFrame) -> pd.DataFrame:
        return data.assign(
            cash_out_stake=(
                (data["size_matched"] * data["average_price_matched"])
                / data["cash_out_odds"]
            ).round(2),
        )

    @staticmethod
    def _get_cash_out_odds(data: pd.DataFrame) -> pd.DataFrame:
        return data.assign(
            cash_out_odds=np.select(
                [
                    data["cash_out_selection_type"] == "LAY",
                    data["cash_out_selection_type"] == "BACK",
                ],
                [data["lay_price_2"], data["back_price_2"]],
                default=np.nan,
            ),
        )

    @staticmethod
    def _create_bet_orders(data: pd.DataFrame) -> list[BetFairOrder]:
        data = data[data["cash_out_stake"] > 2]
        return [
            BetFairOrder(
                size=float(data_dict["cash_out_stake"]),
                price=float(data_dict["cash_out_odds"]),
                selection_id=str(data_dict["selection_id"]),
                market_id=str(data_dict["market_id"]),
                side=str(data_dict["cash_out_selection_type"]),
                strategy="cash_out",
            )
            for data_dict in data.to_dict("records")
        ]

    @staticmethod
    def _handle_back_and_lay_matched_bets(data: pd.DataFrame) -> list[BetFairOrder]:
        return (
            data.pipe(BetFairCashOut._create_average_back_odds)
            .pipe(BetFairCashOut._create_average_lay_odds)
            .pipe(BetFairCashOut._create_cash_out_odds)
            .pipe(BetFairCashOut._merge_back_and_lay_data)
            .pipe(BetFairCashOut._create_bet_side)
            .pipe(BetFairCashOut._get_cash_out_stake_back_and_lay)
            .pipe(BetFairCashOut._get_cash_out_odds)
            .pipe(BetFairCashOut._create_bet_orders)
        )

    @staticmethod
    def _handle_single_matched_back_bets(data: pd.DataFrame) -> list[BetFairOrder]:
        return (
            data.pipe(BetFairCashOut._create_average_lay_odds)
            .pipe(BetFairCashOut._create_cash_out_odds)
            .pipe(BetFairCashOut._alternate_bet_side)
            .pipe(BetFairCashOut._get_cash_out_stake)
            .pipe(BetFairCashOut._get_cash_out_odds)
            .pipe(BetFairCashOut._create_bet_orders)
        )

    @staticmethod
    def _handle_single_matched_lay_bets(data: pd.DataFrame) -> list[BetFairOrder]:
        return (
            data.pipe(BetFairCashOut._create_average_back_odds)
            .pipe(BetFairCashOut._create_cash_out_odds)
            .pipe(BetFairCashOut._alternate_bet_side)
            .pipe(BetFairCashOut._get_cash_out_stake)
            .pipe(BetFairCashOut._get_cash_out_odds)
            .pipe(BetFairCashOut._create_bet_orders)
        )
