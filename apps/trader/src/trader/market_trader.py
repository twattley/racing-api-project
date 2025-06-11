from dataclasses import dataclass

import numpy as np
import pandas as pd
from api_helpers.clients import BetFairClient
from api_helpers.clients import PostgresClient
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.helpers.logging_config import I, W, E, D

import pandas as pd
import re


def print_dataframe_for_testing(df):

    print("pd.DataFrame({")

    for col in df.columns:
        value = df[col].iloc[0]
        if re.match(r"\d{4}-\d{2}-\d{2}", str(value)):
            str_test = (
                "[" + " ".join([f"pd.Timestamp('{x}')," for x in list(df[col])]) + "]"
            )
            print(f"'{col}':{str_test},")
        else:
            print(f"'{col}':{list(df[col])},")
    print("})")


SELECTION_COLS = [
    "unique_id",
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


class MaxStakeSizeExceededError(Exception):
    """Exception raised when the maximum stake size is exceeded."""

    def __init__(self, message="Maximum stake size exceeded."):
        self.message = message
        super().__init__(self.message)


@dataclass
class TradeRequest:
    valid_bets: bool
    info: str
    selections_data: pd.DataFrame | None = None
    orders: list[BetFairOrder] | None = None
    cash_out_market_ids: list[str] | None = None


class MarketTrader:
    def __init__(self, postgres_client: PostgresClient, betfair_client: BetFairClient):
        self.postgres_client = postgres_client
        self.betfair_client = betfair_client

    def trade_markets(
        self,
        stake_size: int,
        now_timestamp: pd.Timestamp,
        requests_data: pd.DataFrame,
    ) -> None:
        I(
            f"Starting trade_markets with stake_size: {stake_size}, timestamp: {now_timestamp}"
        )
        I(f"Input requests_data shape: {requests_data.shape}")

        trades: TradeRequest = self._calculate_trade_positions(
            stake_size=stake_size,
            requests_data=requests_data,
            now_timestamp=now_timestamp,
        )

        if trades.cash_out_market_ids:
            I(
                f"Processing {len(trades.cash_out_market_ids)} cash out market IDs: {trades.cash_out_market_ids}"
            )
            self.betfair_client.cash_out_bets(trades.cash_out_market_ids)
            cash_out_data = (
                trades.selections_data[
                    trades.selections_data["market_id"].isin(trades.cash_out_market_ids)
                ]
                .assign(
                    cash_out_placed=True,
                    cashed_out_invalid=False,
                )
                .filter(
                    items=[
                        "market_id",
                        "selection_id",
                        "cash_out_placed",
                        "cashed_out_invalid",
                    ]
                )
            )
            I(f"Cash out data shape: {cash_out_data.shape}")
            trades.selections_data = (
                pd.merge(
                    trades.selections_data,
                    cash_out_data,
                    how="left",
                    on=["market_id", "selection_id"],
                )
                .assign(
                    cashed_out=lambda x: x["cash_out_placed"].fillna(x["cashed_out"]),
                    valid=lambda x: x["cashed_out_invalid"].fillna(x["valid"]),
                )
                .drop(columns=["cash_out_placed", "cashed_out_invalid"])
            )
            I("Cash out data merged successfully")

        if trades.orders:
            I(f"Processing {len(trades.orders)} orders")
            for i, order in enumerate(trades.orders, 1):
                I(f"Placing order {i}/{len(trades.orders)}: {order}")
                result: OrderResult = self.betfair_client.place_order(order)
                if result.success:
                    I(f"Order {i} placed successfully: {order}")
                else:
                    W(f"Failed to place order {i}: {order}, Error: {result.message}")
        else:
            I("No orders to process")

        if trades.selections_data is not None:
            I(f"Selections data shape: {trades.selections_data[SELECTION_COLS].shape}")
            self.postgres_client.store_latest_data(
                data=trades.selections_data[SELECTION_COLS],
                schema="live_betting",
                table="selections",
                unique_columns=["id", "market_id", "selection_id"],
            )
            I("Selections data stored successfully")

        I("trade_markets completed")

    def _calculate_trade_positions(
        self,
        stake_size: int,
        requests_data: pd.DataFrame,
        now_timestamp: pd.Timestamp,
    ) -> TradeRequest:
        I(f"Calculating trade positions for {len(requests_data)} requests")

        upcoming_bets = self._check_bets_in_next_hour(requests_data)
        if upcoming_bets.empty:
            tr = TradeRequest(
                valid_bets=False,
                info="No bets in the next hour",
            )
            I(tr.info)
            return tr

        I(f"Found {len(upcoming_bets)} bets in the next hour")

        stake_exceeded = self._check_stake_size_exceedeI(requests_data, stake_size)
        if not stake_exceeded.empty:
            E(f"Stake size exceeded for {len(stake_exceeded)} bets")
            raise MaxStakeSizeExceededError(
                f"Maximum stake size of {stake_size} exceeded for the following bets: {stake_exceeded}"
            )

        I("Processing bet validation and calculations")
        requests_data = (
            requests_data.pipe(self._mark_invalid_bets, now_timestamp)
            .pipe(self._mark_fully_matched_bets, stake_size, now_timestamp)
            .pipe(self._set_new_size_and_price, stake_size)
            .pipe(self._check_odds_available)
        )

        orders, cash_out_market_ids = self._create_bet_data(requests_data)
        selections_data = self._update_selections_data(requests_data)

        I(
            f"Trade calculation complete - Orders: {len(orders) if orders else 0}, Cash outs: {len(cash_out_market_ids) if cash_out_market_ids else 0}"
        )

        return TradeRequest(
            valid_bets=True,
            info="Bets requested!",
            selections_data=selections_data,
            orders=orders,
            cash_out_market_ids=cash_out_market_ids,
        )

    def _check_bets_in_next_hour(self, data: pd.DataFrame) -> pd.DataFrame:
        upcoming = data[(data["minutes_to_race"].between(0, 60))]
        I(f"Checking bets in next hour: {len(upcoming)}/{len(data)} qualify")
        return upcoming

    def _check_stake_size_exceedeI(
        self, data: pd.DataFrame, stake_size: int
    ) -> pd.DataFrame:
        I(f"Checking stake size limits against {stake_size}")
        data = data.assign(
            stake_exceeded=np.select(
                [
                    (data["selection_type"] == "BACK"),
                    (data["selection_type"] == "LAY"),
                ],
                [
                    (data["size_matched_betfair"] > stake_size),
                    (data["size_matched_betfair"] > stake_size * 1.5),
                ],
                default=False,
            )
        )

        exceeded = data[data["stake_exceeded"] == True]
        if not exceeded.empty:
            W(f"Found {len(exceeded)} bets exceeding stake limits")
            for _, row in exceeded.iterrows():
                W(
                    f"Stake exceeded - {row['selection_type']}: {row['size_matched_betfair']} > limit"
                )

        return exceeded

    def _update_selections_data(self, data: pd.DataFrame) -> pd.DataFrame:
        I("Updating selections data with final values")
        data = data.assign(
            average_price_matched=data["average_price_matched_selections"]
            .astype(float)
            .fillna(data["average_price_matched_betfair"].astype(float))
            .round(2),
            size_matched=data["size_matched_betfair"].round(2),
            customer_strategy_ref=data["customer_strategy_ref_selections"]
            .fillna(data["customer_strategy_ref_betfair"])
            .round(2),
        )
        result = data.filter(items=SELECTION_COLS)
        I(f"Updated selections data shape: {result.shape}")
        return result

    def _mark_invalid_bets(
        self, data: pd.DataFrame, now_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        I("Marking invalid bets")
        initial_valid_count = (
            data["valid"].sum() if "valid" in data.columns else len(data)
        )

        conditions = [
            (data["eight_to_seven_runners"] == True) & (data["market_type"] == "PLACE"),
            (data["short_price_removed_runners"] == True),
            (data["minutes_to_race"] < 1),
        ]

        condition_names = [
            "Invalid 8 to 7 Place",
            "Invalid Short Price Removed",
            "Race Started",
        ]

        for i, (condition, name) in enumerate(zip(conditions, condition_names)):
            count = condition.sum()
            if count > 0:
                I(f"Found {count} bets to invalidate due to: {name}")

        result = data.assign(
            valid=np.select(
                conditions,
                [False, False, False],
                default=data["valid"],
            ),
            invalidated_reason=np.select(
                conditions,
                condition_names,
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

        final_valid_count = result["valid"].sum()
        invalidated_count = initial_valid_count - final_valid_count
        if invalidated_count > 0:
            I(f"Invalidated {invalidated_count} bets")

        return result

    def _extract_invalidated_fully_matched_bets(
        self, data: pd.DataFrame, market_ids: list[str]
    ) -> pd.DataFrame:
        result = data[(data["market_id"].isin(market_ids))]
        I(
            f"Extracted {len(result)} invalidated fully matched bets from {len(market_ids)} markets"
        )
        return result

    def _get_invalidated_fully_matched_bets_market_ids(
        self, data: pd.DataFrame
    ) -> list[str]:
        market_ids = (
            data[(data["valid"] == False) & (data["fully_matched"] == True)][
                "market_id"
            ]
            .unique()
            .tolist()
        )
        I(f"Found {len(market_ids)} market IDs with invalidated fully matched bets")
        return market_ids

    def _mark_fully_matched_bets(
        self, data: pd.DataFrame, stake_size: float, now_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        I(f"Marking fully matched bets with stake size: {stake_size}")

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
        fully_matched_ids = data[
            (data["fully_matched"] == True) | data["staked_minus_target"] < 1
        ]["id"].unique()
        data = data.assign(
            fully_matched=np.where(
                data["id"].isin(fully_matched_ids),  # If already True, keep it True
                True,
                False,
            ),
            processed_at=now_timestamp,
        )
        return data

    def _set_new_size_and_price(
        self, data: pd.DataFrame, stake_size: float
    ) -> pd.DataFrame:
        I(f"Setting new size and price calculations with stake size: {stake_size}")

        conditions = [
            (data["selection_type"] == "BACK") & (data["size_matched_betfair"] > 0),
            (data["selection_type"] == "LAY") & (data["size_matched_betfair"] > 0),
            (data["selection_type"] == "BACK") & (data["size_matched_betfair"] == 0),
            (data["selection_type"] == "LAY") & (data["size_matched_betfair"] == 0),
        ]

        condition_names = [
            "BACK with existing match",
            "LAY with existing match",
            "BACK new bet",
            "LAY new bet",
        ]

        for condition, name in zip(conditions, condition_names):
            count = condition.sum()
            if count > 0:
                I(f"Processing {count} bets for: {name}")

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

        I(
            f"Remaining size range: {data['remaining_size'].min():.2f} - {data['remaining_size'].max():.2f}"
        )
        I(
            f"Average price range: {data['amended_average_price'].min():.2f} - {data['amended_average_price'].max():.2f}"
        )

        return data

    def _check_odds_available(self, data: pd.DataFrame) -> pd.DataFrame:
        I("Checking odds availability")

        back_condition = (
            (data["selection_type"] == "BACK")
            & (data["amended_average_price"] >= data["requested_odds"])
            & (data["back_price_1_depth"] >= data["remaining_size"])
        )

        lay_condition = (
            (data["selection_type"] == "LAY")
            & (data["amended_average_price"] <= data["requested_odds"])
            & (data["lay_price_1_depth"] >= data["remaining_size"])
        )

        back_available = back_condition.sum()
        lay_available = lay_condition.sum()

        I(f"Odds availability - BACK: {back_available}, LAY: {lay_available}")

        result = data.assign(
            available_odds=np.select(
                [back_condition, lay_condition],
                [True, True],
                default=False,
            )
        )

        total_available = result["available_odds"].sum()
        I(f"Total bets with available odds: {total_available}")

        return result

    def _create_bet_data(
        self, data: pd.DataFrame
    ) -> tuple[list[BetFairOrder], list[str]]:
        I("Creating bet data and orders")

        cash_out_market_ids = (
            data[data["cash_out"] == True]["market_id"].unique().tolist()
        )
        I(f"Cash out market IDs: {len(cash_out_market_ids)}")

        fully_matched_cash_out_market_ids = (
            data[(data["valid"] == False) & (data["fully_matched"] == True)][
                "market_id"
            ]
            .unique()
            .tolist()
        )
        I(
            f"Fully matched cash out market IDs: {len(fully_matched_cash_out_market_ids)}"
        )

        bets = data[
            (data["valid"] == True)
            & (data["available_odds"] == True)
            & (data["cash_out"] == False)
            & (data["remaining_size"] > 1)
            & (data["fully_matched"] == False)
        ]

        I(f"Eligible bets for orders: {len(bets)}")

        orders = []

        bets = bets.assign(
            remaining_size=lambda x: x["remaining_size"].round(2),
        )

        for i in bets.itertuples():
            if i.selection_type == "BACK":
                order = BetFairOrder(
                    size=round(i.remaining_size, 2),
                    price=i.back_price_1,
                    market_id=i.market_id,
                    selection_id=i.selection_id,
                    side=i.selection_type,
                    strategy=i.id,
                )
                orders.append(order)
                I(
                    f"Created BACK order: size={i.remaining_size}, price={i.back_price_1}"
                )
            elif i.selection_type == "LAY":
                order = BetFairOrder(
                    size=round(i.remaining_size, 2),
                    price=i.lay_price_1,
                    market_id=i.market_id,
                    selection_id=i.selection_id,
                    side=i.selection_type,
                    strategy=i.id,
                )
                orders.append(order)
                I(f"Created LAY order: size={i.remaining_size}, price={i.lay_price_1}")
            else:
                E(f"Invalid selection type: {i.selection_type}")
                raise ValueError(f"Invalid selection type: {i.selection_type}")

        combined_cash_out_ids = list(
            set(cash_out_market_ids + fully_matched_cash_out_market_ids)
        )
        I(
            f"Total orders created: {len(orders)}, Total cash out markets: {len(combined_cash_out_ids)}"
        )

        return orders, combined_cash_out_ids
