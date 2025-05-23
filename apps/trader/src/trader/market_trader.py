from dataclasses import dataclass

import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder
from api_helpers.clients.s3_client import S3Client
from api_helpers.helpers.data_utils import combine_dataframes
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr

from .fetch_requests import RawBettingData


@dataclass
class ValidBets:
    invalidated_bets: pd.DataFrame
    valid_bets: pd.DataFrame


@dataclass
class MatchedBets:
    fully_matched_bets: pd.DataFrame
    partially_matched_bets: pd.DataFrame


class MarketTrader:
    def __init__(
        self, s3_client: S3Client, betfair_client: BetFairClient, stake_size: int
    ):
        self.s3_client = s3_client
        self.betfair_client = betfair_client
        self.stake_size = stake_size
        self.folder = None

    def trade_markets(
        self,
        requests_data: pd.DataFrame,
        betting_data: RawBettingData,
        now_timestamp: pd.Timestamp,
    ):
        self.folder = f"today/{now_timestamp.strftime('%Y_%m_%d')}/trader_data"
        self._store_current_orders()

        upcoming_bets = self._check_bets_in_next_hour(requests_data)
        if upcoming_bets.empty:
            I("No bets to place in the next hour.")
            return

        validated_bets = self._split_valid_bets(upcoming_bets, now_timestamp)

        valid_bets = self._handle_validation(betting_data, validated_bets)

        if valid_bets.empty:
            return

        matched_bets = self._split_matched_bets(valid_bets)

        partially_matched_valid_bets = self._handle_partial_matching(
            betting_data, matched_bets
        )

        bets = partially_matched_valid_bets.pipe(self._set_new_size_and_price).pipe(
            self._check_odds_available
        )

        if bets.empty:
            I("No valid bets to place.")
            return

        self._place_bets(bets)

    def _handle_partial_matching(
        self, betting_data: RawBettingData, matched_bets: MatchedBets
    ):
        if not matched_bets.fully_matched_bets.empty:
            partially_matched_valid_bets = self._handle_matched_bets(
                matched_bets=matched_bets,
                betting_data=betting_data,
            )
        else:
            partially_matched_valid_bets = matched_bets.partially_matched_bets
        return partially_matched_valid_bets

    def _handle_validation(
        self, betting_data: RawBettingData, validated_bets: ValidBets
    ) -> pd.DataFrame:
        if not validated_bets.invalidated_bets.empty:
            cash_out_data = self.betfair_client.cash_out_bets(
                validated_bets.invalidated_bets["market_id"].unique()
            )
            valid_bets = self._handle_invalid_bets(
                cash_out_data=cash_out_data,
                validated_data=validated_bets,
                betting_data=betting_data,
            )
        else:
            valid_bets = validated_bets.valid_bets
        return valid_bets

    def _split_matched_bets(self, data: pd.DataFrame) -> MatchedBets:
        data = data.assign(
            staked_minus_target=np.select(
                [
                    (data["selection_type"] == "BACK"),
                    (data["selection_type"] == "LAY"),
                ],
                [
                    (self.stake_size - data["size_matched"]),
                    (
                        (self.stake_size * 1.5)
                        - (data["size_matched"] * (data["average_price_matched"] - 1))
                    ),
                ],
                default=0,
            )
        )
        data = data.assign(
            fully_matched=np.where(data["staked_minus_target"] > 1, False, True)
        )

        return MatchedBets(
            fully_matched_bets=data[data["fully_matched"] == True],
            partially_matched_bets=data[data["fully_matched"] == False],
        )

    def _check_bets_in_next_hour(self, requests_data: pd.DataFrame) -> pd.DataFrame:
        return requests_data[(requests_data["minutes_to_race"] < 60)]

    def _set_new_size_and_price(self, data: pd.DataFrame) -> pd.DataFrame:
        conditions = [
            (data["selection_type"] == "BACK") & (data["size_matched"] > 0),
            (data["selection_type"] == "LAY") & (data["size_matched"] > 0),
            (data["selection_type"] == "BACK") & (data["size_matched"] == 0),
            (data["selection_type"] == "LAY") & (data["size_matched"] == 0),
        ]

        data = data.assign(
            remaining_size=np.select(
                conditions,
                [
                    self.stake_size - data["size_matched"],
                    (
                        (self.stake_size * 1.5)
                        - (data["average_price_matched"] - 1) * data["size_matched"]
                    )
                    / (data["lay_price_1"] - 1),
                    self.stake_size,
                    (self.stake_size * 1.5) / (data["lay_price_1"] - 1),
                ],
            ),
            amended_average_price=np.select(
                conditions,
                [
                    (
                        (
                            (data["average_price_matched"] * data["size_matched"])
                            + (
                                data["back_price_1"]
                                * (self.stake_size - data["size_matched"])
                            )
                        )
                        / self.stake_size
                    ),
                    (
                        (self.stake_size * 1.5)
                        / (
                            (
                                (
                                    (self.stake_size * 1.5)
                                    - (data["average_price_matched"] - 1)
                                    * data["size_matched"]
                                )
                                / (data["lay_price_1"] - 1)
                            )
                            + data["size_matched"]
                        )
                        + 1
                    ).round(2),
                    data["back_price_1"],
                    data["lay_price_1"],
                ],
            ),
        )
        data = data.assign(
            remaining_size=data["remaining_size"].round(2),
            amended_average_price=data["amended_average_price"].round(2),
        )

        return data

    def _check_odds_available(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            available_odds=np.select(
                [
                    (data["selection_type"] == "BACK")
                    & (data["amended_average_price"] >= data["requested_odds"])
                    & (data["back_price_1_depth"] >= data["remaining_size"]),
                    (data["selection_type"] == "LAY")
                    & (data["amended_average_price"] <= data["requested_odds"])
                    & (data["lay_price_1_depth"] >= data["remaining_size"]),
                ],
                [True, True],
                default=False,
            )
        )
        return data[data["available_odds"] == True]

    def _place_bets(self, valid_bets: pd.DataFrame):
        valid_bets = valid_bets[valid_bets["remaining_size"] > 1]
        if valid_bets.empty:
            I("No valid bets to place.")
            return
        for i in valid_bets.itertuples():
            if i.selection_type == "BACK":
                self.betfair_client.place_order(
                    BetFairOrder(
                        size=i.remaining_size,
                        price=i.back_price_1,
                        market_id=i.market_id,
                        selection_id=i.selection_id,
                        side=i.selection_type,
                        strategy="mvp",
                    )
                )
            elif i.selection_type == "LAY":
                self.betfair_client.place_order(
                    BetFairOrder(
                        size=i.remaining_size,
                        price=i.lay_price_1,
                        market_id=i.market_id,
                        selection_id=i.selection_id,
                        side=i.selection_type,
                        strategy="mvp",
                    )
                )
            else:
                raise ValueError(f"Invalid selection type: {i.selection_type}")
        I("Bets placed successfully.")

    def _handle_matched_bets(
        self,
        matched_bets: MatchedBets,
        betting_data: RawBettingData,
    ) -> pd.DataFrame:
        if matched_bets.fully_matched_bets.empty:
            I("No fully matched bets to process.")
            return matched_bets.partially_matched_bets

        not_previously_matched = pd.merge(
            matched_bets.fully_matched_bets,
            betting_data.fully_matched_bets,
            on=["race_id", "horse_id", "selection_type", "market_type"],
            how="left",
        )
        not_previously_matched = not_previously_matched[
            not_previously_matched["horse_name_y"].isna()
        ]

        if not not_previously_matched.empty:
            not_previously_matched = not_previously_matched.rename(
                columns={
                    "horse_name_x": "horse_name",
                    "race_time_x": "race_time",
                    "average_price_matched_x": "average_price_matched",
                    "size_matched_x": "size_matched",
                }
            )

            (
                self.s3_client.store_data(
                    pd.concat(
                        [
                            betting_data.fully_matched_bets,
                            not_previously_matched[
                                [
                                    "race_id",
                                    "horse_id",
                                    "horse_name",
                                    "race_time",
                                    "selection_type",
                                    "market_type",
                                    "average_price_matched",
                                    "size_matched",
                                ]
                            ],
                        ]
                    )
                    .drop_duplicates(
                        subset=[
                            "race_time",
                            "race_id",
                            "horse_id",
                            "horse_name",
                            "selection_type",
                            "market_type",
                        ]
                    )
                    .astype(
                        {
                            "race_id": "int64",
                            "horse_id": "int64",
                            "horse_name": "object",
                            "selection_type": "object",
                            "market_type": "object",
                            "average_price_matched": "float64",
                            "size_matched": "float64",
                        }
                    ),
                    f"{self.folder}/fully_matched_bets.parquet",
                ),
            )
        return matched_bets.partially_matched_bets

    def _handle_invalid_bets(
        self,
        validated_data: ValidBets,
        betting_data: RawBettingData,
        cash_out_data: pd.DataFrame,
    ) -> pd.DataFrame:
        invalidated_bets = pd.concat(
            [betting_data.invalidated_bets, validated_data.invalidated_bets]
        ).drop_duplicates(subset=["market_id", "selection_id"])

        invalidated_bets = pd.merge(
            invalidated_bets[
                [
                    "race_id",
                    "horse_id",
                    "horse_name",
                    "selection_type",
                    "market_type",
                    "market_id",
                    "selection_id",
                    "requested_odds",
                    "race_time",
                    "invalidated_reason",
                    "time_invalidated",
                ]
            ],
            cash_out_data[
                [
                    "market_id",
                    "selection_id",
                    "selection_type",
                    "average_price_matched",
                    "size_matched",
                ]
            ],
            on=["market_id", "selection_id", "selection_type"],
            how="left",
        )
        validated_bets = betting_data.selections_data[
            ~betting_data.selections_data["market_id"].isin(
                list(invalidated_bets["market_id"].unique())
            )
        ]
        if not invalidated_bets.empty:
            self.s3_client.store_data(
                invalidated_bets,
                f"{self.folder}/invalidated_bets.parquet",
            )
        if validated_bets.empty:
            self.s3_client.store_data(
                pd.DataFrame(
                    {
                        "race_id": [],
                        "race_time": [],
                        "race_date": [],
                        "horse_id": [],
                        "horse_name": [],
                        "selection_type": [],
                        "market_type": [],
                        "market_id": [],
                        "selection_id": [],
                        "requested_odds": [],
                        "valid": [],
                        "invalidated_reason": [],
                        "invalidated_at": [],
                    }
                ),
                f"{self.folder}/selections_data.parquet",
            )
        else:
            self.s3_client.store_data(
                validated_bets,
                f"{self.folder}/selections_data.parquet",
            )

        return validated_data.valid_bets

    def _split_valid_bets(
        self, data: pd.DataFrame, now_timestamp: pd.Timestamp
    ) -> ValidBets:
        conditions = [
            (data["eight_to_seven_runners"] == True) & (data["market_type"] == "PLACE"),
            (data["short_price_removed_runners"] == True),
        ]

        data = data.assign(
            valid_bet=np.select(
                conditions,
                [False, False],
                default=True,
            ),
            invalidated_reason=np.select(
                conditions,
                ["Invalid 8 to 7 Place", "Invalid Short Price Removed"],
                default="Valid Bet",
            ),
            time_invalidated=np.select(
                conditions,
                [now_timestamp] * 2,
                default=pd.NaT,
            ),
        )
        invalidated_data = data[data["valid_bet"] == False]
        return ValidBets(
            invalidated_bets=invalidated_data,
            valid_bets=data[
                ~data["market_id"].isin(invalidated_data["market_id"].unique())
            ],
        )

    def _store_current_orders(self):
        stored_current_orders, current_orders = ptr(
            lambda: self.s3_client.fetch_data(
                f"{self.folder}/current_orders.parquet",
            ),
            lambda: self.betfair_client.get_current_orders(),
        )
        updated_current_orders = combine_dataframes(
            stored_current_orders, current_orders
        ).drop_duplicates(subset=["bet_id"])

        if updated_current_orders.empty:
            I("No current orders to store.")
            return

        self.s3_client.store_data(
            updated_current_orders,
            f"{self.folder}/current_orders.parquet",
        )
