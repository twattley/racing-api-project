# filepath: /Users/tomwattley/App/racing-api-project/racing-api-project/apps/trader/src/trader/market_trader.py
from dataclasses import dataclass

import numpy as np
import pandas as pd
from api_helpers.clients import BetFairClient, S3Client
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.helpers.file_utils import S3FilePaths
from api_helpers.helpers.logging_config import I, W

SELECTION_COLS = [
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


@dataclass
class TradeRequest:
    valid_bets: bool
    info: str
    selections_data: pd.DataFrame | None = None
    orders: list[BetFairOrder] | None = None
    cash_out_market_ids: list[str] | None = None


class MarketTrader:
    def __init__(self, s3_client: S3Client, betfair_client: BetFairClient):
        self.s3_client = s3_client
        self.betfair_client = betfair_client
        self.paths = S3FilePaths()

    def trade_markets(
        self,
        stake_size: int,
        now_timestamp: pd.Timestamp,
        requests_data: pd.DataFrame,
    ) -> None:
        trades: TradeRequest = self._calculate_trade_positions(
            stake_size=stake_size,
            requests_data=requests_data,
            now_timestamp=now_timestamp,
        )

        if trades.cash_out_market_ids:
            self.betfair_client.cash_out_bets(trades.cash_out_market_ids)

        if trades.orders:
            for order in trades.orders:
                result: OrderResult = self.betfair_client.place_order(order)
                if result.success:
                    I(f"Order placed successfully: {order}")
                else:
                    W(f"Failed to place order: {order}, Error: {result.message}")

        if trades.selections_data is not None:
            self.s3_client.store_data(
                trades.selections_data[SELECTION_COLS], self.paths.selections
            )

    def _calculate_trade_positions(
        self,
        stake_size: int,
        requests_data: pd.DataFrame,
        now_timestamp: pd.Timestamp,
    ) -> TradeRequest:
        upcoming_bets = self._check_bets_in_next_hour(requests_data)
        if upcoming_bets.empty:
            tr = TradeRequest(
                valid_bets=False,
                info="No bets in the next hour",
            )
            I(tr.info)
            return tr

        requests_data = (
            requests_data.pipe(self._mark_invalid_bets, now_timestamp)
            .pipe(self._mark_fully_matched_bets, stake_size, now_timestamp)
            .pipe(self._set_new_size_and_price, stake_size)
            .pipe(self._check_odds_available)
        )

        orders, cash_out_market_ids = self._create_bet_data(requests_data)
        selections_data = self._update_selections_data(requests_data)
        return TradeRequest(
            valid_bets=True,
            info="Bets requested!",
            selections_data=selections_data,
            orders=orders,
            cash_out_market_ids=cash_out_market_ids,
        )

    def _check_bets_in_next_hour(self, data: pd.DataFrame) -> pd.DataFrame:
        return data[(data["minutes_to_race"].between(0, 60))]

    def _update_selections_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            average_price_matched=data["average_price_matched_selections"]
            .fillna(data["average_price_matched_betfair"])
            .round(2),
            size_matched=data["size_matched_betfair"].round(2),
            customer_strategy_ref=data["customer_strategy_ref_selections"]
            .fillna(data["customer_strategy_ref_betfair"])
            .round(2),
        )
        return data.filter(items=SELECTION_COLS)

    def _mark_invalid_bets(
        self, data: pd.DataFrame, now_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        conditions = [
            (data["eight_to_seven_runners"] == True) & (data["market_type"] == "PLACE"),
            (data["short_price_removed_runners"] == True),
            (data["minutes_to_race"] < 1),
        ]

        return data.assign(
            valid=np.select(
                conditions,
                [False, False, False],
                default=data["valid"],
            ),
            invalidated_reason=np.select(
                conditions,
                ["Invalid 8 to 7 Place", "Invalid Short Price Removed", "Race Started"],
                default=data["invalidated_reason"],
            ),
            invalidated_at=np.select(
                conditions,
                [now_timestamp] * 3,
                default=data["invalidated_at"],
            ),
            processed_at=now_timestamp,
            cash_out=np.select(
                conditions,
                [True, True, False],
                default=False,
            ),
        )

    def _extract_invalidated_fully_matched_bets(
        self, data: pd.DataFrame, market_ids: list[str]
    ) -> pd.DataFrame:
        return data[(data["market_id"].isin(market_ids))]

    def _get_invalidated_fully_matched_bets_market_ids(
        self, data: pd.DataFrame
    ) -> list[str]:
        return (
            data[(data["valid"] == False) & (data["fully_matched"] == True)][
                "market_id"
            ]
            .unique()
            .tolist()
        )

    def _mark_fully_matched_bets(
        self, data: pd.DataFrame, stake_size: float, now_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        data = data.assign(
            staked_minus_target=np.select(
                [
                    (data["selection_type"] == "BACK"),
                    (data["selection_type"] == "LAY"),
                ],
                [
                    (stake_size - data["size_matched_betfair"]),
                    (
                        (stake_size * 1.5)
                        - (
                            data["size_matched_betfair"]
                            * (data["average_price_matched_betfair"] - 1)
                        )
                    ),
                ],
                default=0,
            )
        )
        data = data.assign(
            fully_matched=np.where(
                data["fully_matched"] == True,  # If already True, keep it True
                True,
                np.where(
                    data["staked_minus_target"] > 1, False, True
                ),  # Otherwise, calculate normally
            ),
            processed_at=now_timestamp,
        )

        return data

    def _set_new_size_and_price(
        self, data: pd.DataFrame, stake_size: float
    ) -> pd.DataFrame:
        conditions = [
            (data["selection_type"] == "BACK") & (data["size_matched_betfair"] > 0),
            (data["selection_type"] == "LAY") & (data["size_matched_betfair"] > 0),
            (data["selection_type"] == "BACK") & (data["size_matched_betfair"] == 0),
            (data["selection_type"] == "LAY") & (data["size_matched_betfair"] == 0),
        ]

        data = data.assign(
            remaining_size=np.select(
                conditions,
                [
                    stake_size - data["size_matched_betfair"],
                    (
                        (stake_size * 1.5)
                        - (data["average_price_matched_betfair"] - 1)
                        * data["size_matched_betfair"]
                    )
                    / (data["lay_price_1"] - 1),
                    stake_size,
                    (stake_size * 1.5) / (data["lay_price_1"] - 1),
                ],
            ),
            amended_average_price=np.select(
                conditions,
                [
                    (
                        (
                            (
                                data["average_price_matched_betfair"]
                                * data["size_matched_betfair"]
                            )
                            + (
                                data["back_price_1"]
                                * (stake_size - data["size_matched_betfair"])
                            )
                        )
                        / stake_size
                    ),
                    (
                        (stake_size * 1.5)
                        / (
                            (
                                (
                                    (stake_size * 1.5)
                                    - (data["average_price_matched_betfair"] - 1)
                                    * data["size_matched_betfair"]
                                )
                                / (data["lay_price_1"] - 1)
                            )
                            + data["size_matched_betfair"]
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

        print(data[["remaining_size", "amended_average_price"]].head())

        return data

    def _check_odds_available(self, data: pd.DataFrame) -> pd.DataFrame:
        return data.assign(
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

    def _create_bet_data(
        self, data: pd.DataFrame
    ) -> tuple[list[BetFairOrder], list[str]]:
        cash_out_market_ids = (
            data[data["cash_out"] == True]["market_id"].unique().tolist()
        )
        fully_matched_cash_out_market_ids = (
            data[(data["valid"] == False) & (data["fully_matched"] == True)][
                "market_id"
            ]
            .unique()
            .tolist()
        )

        bets = data[
            (data["valid"] == True)
            & (data["available_odds"] == True)
            & (data["cash_out"] == False)
            & (data["remaining_size"] > 1)
            & (data["fully_matched"] == False)
        ]

        orders = []

        for i in bets.itertuples():
            if i.selection_type == "BACK":
                order = BetFairOrder(
                    size=i.remaining_size,
                    price=i.back_price_1,
                    market_id=i.market_id,
                    selection_id=i.selection_id,
                    side=i.selection_type,
                    strategy="mvp",
                )
                orders.append(order)
            elif i.selection_type == "LAY":
                order = BetFairOrder(
                    size=i.remaining_size,
                    price=i.lay_price_1,
                    market_id=i.market_id,
                    selection_id=i.selection_id,
                    side=i.selection_type,
                    strategy="mvp",
                )
                orders.append(order)
            else:
                raise ValueError(f"Invalid selection type: {i.selection_type}")

        return orders, list(
            set(cash_out_market_ids + fully_matched_cash_out_market_ids)
        )
