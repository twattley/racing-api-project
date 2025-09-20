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

MARKET_FILTER = betfairlightweight.filters.market_filter(
    event_type_ids=["7"],
    market_countries=["GB"],
    market_type_codes=["WIN", "PLACE"],
    market_start_time={
        "from": ((datetime.now()) - timedelta(hours=1)).strftime("%Y-%m-%dT%TZ"),
        "to": (datetime.now())
        .replace(hour=23, minute=59, second=0, microsecond=0)
        .strftime("%Y-%m-%dT%TZ"),
    },
)


MARKET_PROJECTION = [
    "COMPETITION",
    "EVENT",
    "EVENT_TYPE",
    "MARKET_START_TIME",
    "MARKET_DESCRIPTION",
    "RUNNER_DESCRIPTION",
    "RUNNER_METADATA",
]

PRICE_PROJECTION = betfairlightweight.filters.price_projection(
    price_data=betfairlightweight.filters.price_data(ex_all_offers=True)
)


@dataclass(frozen=True)
class BetFairCancelOrders:
    market_ids: list[str]


@dataclass(frozen=True)
class BetFairOrder:
    size: float
    price: float
    selection_id: str
    market_id: str
    side: Literal["BACK", "LAY"]
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
    def _create_bet_orders(data: pd.DataFrame) -> BetFairOrder:
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
    def _handle_back_and_lay_matched_bets(data: pd.DataFrame) -> BetFairOrder:
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
    def _handle_single_matched_back_bets(data: pd.DataFrame) -> BetFairOrder:
        return (
            data.pipe(BetFairCashOut._create_average_lay_odds)
            .pipe(BetFairCashOut._create_cash_out_odds)
            .pipe(BetFairCashOut._alternate_bet_side)
            .pipe(BetFairCashOut._get_cash_out_stake)
            .pipe(BetFairCashOut._get_cash_out_odds)
            .pipe(BetFairCashOut._create_bet_orders)
        )

    @staticmethod
    def _handle_single_matched_lay_bets(data: pd.DataFrame) -> BetFairOrder:
        return (
            data.pipe(BetFairCashOut._create_average_back_odds)
            .pipe(BetFairCashOut._create_cash_out_odds)
            .pipe(BetFairCashOut._alternate_bet_side)
            .pipe(BetFairCashOut._get_cash_out_stake)
            .pipe(BetFairCashOut._get_cash_out_odds)
            .pipe(BetFairCashOut._create_bet_orders)
        )


class BetFairClient:
    """
    Betfair client
    """

    def __init__(
        self, credentials: BetfairCredentials, betfair_cash_out: BetFairCashOut
    ):
        self.credentials = credentials
        self.betfair_cash_out = betfair_cash_out
        self.trading_client: betfairlightweight.APIClient | None = None

    def login(self):
        if self.trading_client is None or self.trading_client.session_expired:
            I("Logging into Betfair...")
            self.trading_client = betfairlightweight.APIClient(
                username=self.credentials.username,
                password=self.credentials.password,
                app_key=self.credentials.app_key,
                certs=self.credentials.certs_path,
            )
            self.trading_client.login(session=requests)
            I("Logged into Betfair!")

    def check_session(self):
        if self.trading_client is None or self.trading_client.session_expired:
            I("Betfair session expired")
            self.login()

    def logout(self):
        if self.trading_client is not None:
            self.trading_client.logout()
            I("Logged out of Betfair")

    def create_market_data(self) -> pd.DataFrame:
        self.check_session()
        markets, runners = self._create_markets_and_runners()
        return self._process_combined_market_data(markets, runners)

    def _get_single_race_markets(self, market_ids: list[str]):
        self.check_session()
        markets = self.trading_client.betting.list_market_catalogue(
            filter=betfairlightweight.filters.market_filter(
                market_ids=market_ids,
            ),
            market_projection=MARKET_PROJECTION,
            max_results=1000,
        )

        D(f"Found {len(markets)} markets")
        runners = {
            runner.selection_id: runner.runner_name
            for market in markets
            for runner in market.runners
        }

        return markets, runners

    def create_single_market_data(self, market_ids: list[str]) -> pd.DataFrame:
        self.check_session()
        markets, runners = self._get_single_race_markets(market_ids)
        data = self._process_combined_market_data(markets, runners)
        return data.rename(
            columns={
                "horse_win": "horse_name",
                "todays_betfair_selection_id": "selection_id",
                "last_traded_price_win": "betfair_win_sp",
                "last_traded_price_place": "betfair_place_sp",
            }
        )

    def create_merged_single_market_data(self, market_ids: list[str]) -> pd.DataFrame:
        self.check_session()
        markets, runners = self._get_single_race_markets(market_ids)
        data = self._process_combined_market_data(markets, runners)
        data = data.rename(
            columns={
                "horse_win": "horse_name",
                "last_traded_price_win": "betfair_win_sp",
                "last_traded_price_place": "betfair_place_sp",
            }
        )
        return pd.merge(
            data[data["market"] == "WIN"],
            data[data["market"] == "PLACE"],
            on=["race_time", "course", "todays_betfair_selection_id"],
            suffixes=("_win", "_place"),
        ).rename(
            columns={
                "horse_win": "horse_name",
                "todays_betfair_selection_id": "horse_id",
                "last_traded_price_win": "betfair_win_sp",
                "last_traded_price_place": "betfair_place_sp",
            }
        )

    def create_market_order_data(self, market_ids: list[str]) -> pd.DataFrame:
        self.check_session()
        markets, runners = self._get_single_race_markets(market_ids)
        data = self._process_combined_market_data(markets, runners)
        data = data.rename(
            columns={
                "todays_betfair_selection_id": "selection_id",
                "market": "market_type",
                "status": "runner_status",
            }
        )
        return data[data["runner_status"] == "ACTIVE"]

    def _create_markets_and_runners(self):
        self.check_session()
        markets = self.trading_client.betting.list_market_catalogue(
            filter=MARKET_FILTER,
            market_projection=MARKET_PROJECTION,
            max_results=1000,
        )
        I(f"Found {len(markets)} markets")
        runners = {
            runner.selection_id: runner.runner_name
            for market in markets
            for runner in market.runners
        }

        return markets, runners

    def get_min_and_max_race_times(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        self.check_session()
        markets, _ = self._create_markets_and_runners()
        start_times = [market.market_start_time for market in markets]
        if not start_times:
            raise ValueError("No markets found")
        return make_uk_time_aware(min(start_times)), make_uk_time_aware(
            max(start_times)
        )

    def _process_combined_market_data(self, markets, runners) -> pd.DataFrame:
        self.check_session()
        combined_data = []

        for market in markets:
            uk_now = get_uk_time_now()
            if make_uk_time_aware(market.market_start_time) <= uk_now:
                I(f"Skipping market {market.market_id} already started")
                continue

            market_book = self.trading_client.betting.list_market_book(
                market_ids=[market.market_id],
                price_projection=PRICE_PROJECTION,
            )
            market_type = market.description.market_type

            for book in market_book:
                for runner in book.runners:
                    runner_data = {
                        "race_time": make_uk_time_aware(market.market_start_time),
                        "market": market_type,
                        "race": market.market_name,
                        "course": market.event.venue,
                        "horse": runners[runner.selection_id],
                        "status": runner.status,
                        "market_id": market.market_id,
                        "todays_betfair_selection_id": runner.selection_id,
                        "last_traded_price": runner.last_price_traded,
                        "total_matched": runner.total_matched,
                    }

                    if runner.status == "ACTIVE":
                        for i, price in enumerate(runner.ex.available_to_back[:5]):
                            runner_data[f"back_price_{i + 1}"] = price.price
                            runner_data[f"back_price_{i + 1}_depth"] = int(
                                round(price.size, 0)
                            )

                        for i, price in enumerate(runner.ex.available_to_lay[:5]):
                            runner_data[f"lay_price_{i + 1}"] = price.price
                            runner_data[f"lay_price_{i + 1}_depth"] = int(
                                round(price.size, 0)
                            )

                    combined_data.append(runner_data)

        data = pd.DataFrame(combined_data)

        data["total_matched_event"] = (
            data.groupby("market_id")["total_matched"]
            .transform("sum")
            .round(0)
            .astype(int)
        )

        data["percent_back_win_chance"] = 100 / data["back_price_1"]
        data["percent_lay_win_chance"] = 100 / data["lay_price_1"]

        data["percent_back_win_book"] = (
            data.groupby("market_id")["percent_back_win_chance"]
            .transform("sum")
            .round(0)
            .astype(int)
        )
        data["percent_lay_win_book"] = (
            data.groupby("market_id")["percent_lay_win_chance"]
            .transform("sum")
            .round(0)
            .astype(int)
        )
        data["market_width"] = (
            data["percent_back_win_book"] - data["percent_lay_win_book"]
        )

        return data[
            [
                "race_time",
                "market",
                "race",
                "course",
                "horse",
                "status",
                "market_id",
                "todays_betfair_selection_id",
                "last_traded_price",
                "total_matched",
                "back_price_1",
                "back_price_1_depth",
                "back_price_2",
                "back_price_2_depth",
                "back_price_3",
                "back_price_3_depth",
                "back_price_4",
                "back_price_4_depth",
                "back_price_5",
                "back_price_5_depth",
                "lay_price_1",
                "lay_price_1_depth",
                "lay_price_2",
                "lay_price_2_depth",
                "lay_price_3",
                "lay_price_3_depth",
                "lay_price_4",
                "lay_price_4_depth",
                "lay_price_5",
                "lay_price_5_depth",
                "total_matched_event",
                "percent_back_win_book",
                "percent_lay_win_book",
                "market_width",
            ]
        ]

    def place_order(
        self,
        betfair_order: BetFairOrder,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> OrderResult:
        """
        Place a betfair order with retry logic for network failures.

        Args:
            betfair_order: The order to place
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)

        Returns:
            OrderResult: Contains success status, message, response data, bet_id, and matching info
        """

        for attempt in range(max_retries + 1):
            try:
                self.check_session()
                D(
                    f"Placing order (attempt {attempt + 1}/{max_retries + 1}) - {betfair_order}"
                )

                response = self.trading_client.betting.place_orders(
                    market_id=betfair_order.market_id,
                    customer_strategy_ref="trader",
                    instructions=[
                        {
                            "orderType": "LIMIT",
                            "selectionId": betfair_order.selection_id,
                            "side": betfair_order.side,
                            "limitOrder": {
                                "price": betfair_order.price,
                                "persistenceType": "LAPSE",
                                "size": betfair_order.size,
                            },
                        }
                    ],
                )

                response_dict = (
                    response.__dict__
                    if hasattr(response, "__dict__")
                    else str(response)
                )

                size_matched = response_dict["_data"]["instructionReports"][0][
                    "sizeMatched"
                ]
                average_price_matched = response_dict["_data"]["instructionReports"][0][
                    "averagePriceMatched"
                ]

                return OrderResult(
                    success=True,
                    message="Order placed successfully",
                    size_matched=size_matched,
                    average_price_matched=average_price_matched,
                )

            except (
                ConnectionError,
                TimeoutError,
                requests.exceptions.RequestException,
            ) as network_error:
                I(f"Network error on attempt {attempt + 1}: {network_error}")
                if attempt < max_retries:
                    I(f"Retrying in {retry_delay} seconds...")
                    sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                    continue
                else:
                    return OrderResult(
                        success=False,
                        message=f"Failed after {max_retries + 1} attempts due to network error: {network_error}",
                    )

            except Exception as e:
                error_msg = f"Unexpected error placing order: {e}"
                I(error_msg)
                return OrderResult(success=False, message=error_msg)

        # This should never be reached, but just in case
        return OrderResult(
            success=False, message="Order placement failed for unknown reason"
        )

    def place_orders(self, betfair_orders: list[BetFairOrder]) -> list[OrderResult]:
        self.check_session()
        orders = []
        for order in betfair_orders:
            result = self.place_order(order)
            orders.append(result)
        return orders

    def cancel_orders(self, betfair_cancel_orders: BetFairCancelOrders):
        self.check_session()
        for id in betfair_cancel_orders.market_ids:
            I(f"Cancelling orders for market {id}")
            try:
                self.trading_client.betting.cancel_orders(market_id=id)
            except Exception as e:
                I(f"Error cancelling orders for market {id}: {e}")

    def cancel_all_orders(self):
        self.check_session()
        self.trading_client.betting.cancel_orders()

    def get_current_orders(self, market_ids: list[str] = None):
        self.check_session()
        current_orders = pd.DataFrame(
            self.trading_client.betting.list_current_orders().__dict__["_data"][
                "currentOrders"
            ]
        )
        current_order_columns = [
            "bet_id",
            "market_id",
            "selection_id",
            "selection_type",
            "execution_status",
            "placed_date",
            "matched_date",
            "average_price_matched",
            "customer_strategy_ref",
            "size_matched",
            "size_remaining",
            "size_lapsed",
            "size_cancelled",
            "size_voided",
            "price_size",
        ]
        if current_orders.empty:
            return pd.DataFrame(columns=current_order_columns)
        else:
            if "customerStrategyRef" not in current_orders.columns:
                current_orders["customerStrategyRef"] = "UI"
            if market_ids:
                current_orders = current_orders[
                    current_orders["marketId"].isin(market_ids)
                ]
            return (
                current_orders.rename(
                    columns={
                        "betId": "bet_id",
                        "marketId": "market_id",
                        "selectionId": "selection_id",
                        "side": "selection_type",
                        "status": "execution_status",
                        "placedDate": "placed_date",
                        "matchedDate": "matched_date",
                        "averagePriceMatched": "average_price_matched",
                        "customerStrategyRef": "customer_strategy_ref",
                        "sizeMatched": "size_matched",
                        "sizeRemaining": "size_remaining",
                        "sizeLapsed": "size_lapsed",
                        "sizeCancelled": "size_cancelled",
                        "sizeVoided": "size_voided",
                        "priceSize": "price_size",
                    }
                )
                .filter(items=current_order_columns)
                .assign(
                    customer_strategy_ref=lambda x: x["customer_strategy_ref"].fillna(
                        "UI"
                    )
                )
            ).pipe(
                BetFairClient.expand_price_size,
            )

    def get_current_orders_with_market_data(self):
        current_orders = self.get_current_orders()
        market_data = self.create_market_order_data(
            list(current_orders["market_id"].unique())
        )
        return pd.merge(
            current_orders, market_data, on=["market_id", "selection_id"], how="left"
        )

    def get_matched_orders(self, market_ids: list[str] = None):
        self.cancel_orders(BetFairCancelOrders(market_ids=market_ids))
        current_orders = self.get_current_orders(market_ids)
        assert_current_orders = current_orders[
            current_orders["execution_status"] == "EXECUTION_COMPLETE"
        ]

        if len(assert_current_orders) != len(current_orders):
            raise ValueError("Some orders have not been cleared")

        grouping_cols = ["market_id", "selection_id", "selection_type"]

        current_orders = current_orders.assign(
            sum_matched=lambda x: x["average_price_matched"] * x["size_matched"],
            horse_sum_matched=lambda x: x.groupby(grouping_cols)[
                "sum_matched"
            ].transform("sum"),
            horse_staked_matched=lambda x: x.groupby(grouping_cols)[
                "size_matched"
            ].transform("sum"),
            average_horse_odds_matched=lambda x: x["horse_sum_matched"]
            / x["horse_staked_matched"],
        )
        current_orders = current_orders.assign(
            average_horse_odds_matched=current_orders[
                "average_horse_odds_matched"
            ].round(2),
        )
        current_orders = (
            current_orders.drop(
                columns=[
                    "average_price_matched",
                    "size_matched",
                    "sum_matched",
                ]
            )
            .rename(
                columns={
                    "horse_staked_matched": "size_matched",
                    "average_horse_odds_matched": "average_price_matched",
                }
            )
            .filter(
                items=[
                    "market_id",
                    "selection_id",
                    "selection_type",
                    "average_price_matched",
                    "size_matched",
                    "customer_strategy_ref",
                ]
            )
        )
        return current_orders.drop_duplicates(subset=grouping_cols)

    def _process_cleared_orders(self, cleared_orders):
        if not cleared_orders.orders:
            I("No cleared orders found")
            return pd.DataFrame()

        # Convert to DataFrame
        orders_data = []
        for order in cleared_orders.orders:
            orders_data.append(
                {
                    "bet_count": getattr(order, "bet_count", None),
                    "bet_id": getattr(order, "bet_id", None),
                    "bet_outcome": getattr(order, "bet_outcome", None),
                    "customer_order_ref": getattr(order, "customer_order_ref", None),
                    "customer_strategy_ref": getattr(
                        order, "customer_strategy_ref", None
                    ),
                    "event_id": getattr(order, "event_id", None),
                    "event_type_id": getattr(order, "event_type_id", None),
                    "handicap": getattr(order, "handicap", None),
                    "last_matched_date": getattr(order, "last_matched_date", None),
                    "market_id": getattr(order, "market_id", None),
                    "order_type": getattr(order, "order_type", None),
                    "persistence_type": getattr(order, "persistence_type", None),
                    "placed_date": getattr(order, "placed_date", None),
                    "price_matched": getattr(order, "price_matched", None),
                    "price_reduced": getattr(order, "price_reduced", None),
                    "price_requested": getattr(order, "price_requested", None),
                    "profit": getattr(order, "profit", None),
                    "commission": getattr(order, "commission", None),
                    "selection_id": getattr(order, "selection_id", None),
                    "settled_date": getattr(order, "settled_date", None),
                    "side": getattr(order, "side", None),
                    "size_settled": getattr(order, "size_settled", None),
                    "size_cancelled": getattr(order, "size_cancelled", None),
                    "item_description": getattr(order, "item_description", None),
                }
            )

        return pd.DataFrame(orders_data)

    def get_past_orders_by_date_range(
        self, from_date: str, to_date: str
    ) -> pd.DataFrame:
        self.check_session()
        cleared_orders = self.trading_client.betting.list_cleared_orders(
            settled_date_range={"from": from_date, "to": to_date},
        )
        return self._process_cleared_orders(cleared_orders)

    def get_past_orders_by_market_id(
        self, market_ids: list[str] = None
    ) -> pd.DataFrame:
        self.check_session()
        cleared_orders = self.trading_client.betting.list_cleared_orders(
            market_ids=market_ids,
        )
        return self._process_cleared_orders(cleared_orders)

    @staticmethod
    def _get_market_ids_for_remaining_cash_out_bets(data: pd.DataFrame) -> list[str]:
        back_subset = data[data["selection_type"] == "BACK"]
        lay_subset = data[data["selection_type"] == "LAY"]

        backs = pd.merge(
            back_subset,
            lay_subset,
            on=[
                "market_id",
                "selection_id",
            ],
            how="left",
            suffixes=["_back", "_lay"],
        )

        lays = pd.merge(
            lay_subset,
            back_subset,
            on=[
                "market_id",
                "selection_id",
            ],
            how="left",
            suffixes=["_back", "_lay"],
        )

        data = pd.concat([backs, lays]).drop_duplicates(
            subset=["market_id", "selection_id"]
        )
        data["back_cashout"] = abs(
            data["size_matched_lay"]
            - (
                (data["average_price_matched_back"] * data["size_matched_back"])
                / data["average_price_matched_lay"]
            )
        ).round(2)
        data["lay_cashout"] = abs(
            data["size_matched_back"]
            - (
                (data["average_price_matched_lay"] * data["size_matched_lay"])
                / data["average_price_matched_back"]
            ).round(2)
        )
        return list(
            data[
                ~(
                    (data["lay_cashout"].round(2) == data["back_cashout"].round(2))
                    & (data["lay_cashout"] < 1)
                    & (data["back_cashout"] < 1)
                )
            ]["market_id"].unique()
        )

    def fetch_cash_out_data(self, market_ids: list[str]) -> pd.DataFrame:
        matched_orders = self.get_matched_orders(market_ids)
        market_ids = BetFairClient._get_market_ids_for_remaining_cash_out_bets(
            matched_orders
        )
        if not market_ids:
            return pd.DataFrame()
        current_market_data = self.create_single_market_data(market_ids)
        data = pd.merge(
            matched_orders,
            current_market_data,
            on=["market_id", "selection_id"],
            how="left",
        )
        data = data[data["race_time"] > pd.Timestamp("now", tz="Europe/London")]
        return data[
            [
                "market_id",
                "selection_id",
                "selection_type",
                "average_price_matched",
                "size_matched",
                "market",
                "status",
                "back_price_1",
                "back_price_1_depth",
                "back_price_2",
                "back_price_2_depth",
                "lay_price_1",
                "lay_price_1_depth",
                "lay_price_2",
                "lay_price_2_depth",
            ]
        ]

    def cash_out_bets(self, market_ids: list[str]):
        cashed_out = False
        while not cashed_out:
            cash_out_data = self.fetch_cash_out_data(market_ids)
            if cash_out_data.empty:
                cashed_out = True
            else:
                cash_out_orders = self.betfair_cash_out.cash_out(cash_out_data)
                self.place_orders(cash_out_orders)
                sleep(10)

        return self.get_matched_orders(market_ids)

    def cash_out_bets_for_selection(
        self, market_ids: list[str], selection_ids: list[str]
    ):
        """
        Cash out bets for specific selection IDs within the given markets.

        Args:
            market_ids: List of market IDs to cash out bets from
            selection_ids: List of selection IDs to specifically cash out

        Returns:
            DataFrame of matched orders for the specified selections

        Raises:
            ValueError: If selection_ids is empty or contains invalid values
        """
        if not selection_ids:
            raise ValueError("selection_ids cannot be empty")

        # Convert selection_ids to strings to match data format
        selection_ids_str = [str(sid) for sid in selection_ids]

        I(
            f"Cashing out bets for selections {selection_ids_str} in markets {market_ids}"
        )

        cashed_out = False
        while not cashed_out:
            # Fetch all cash out data for the markets
            cash_out_data = self.fetch_cash_out_data(market_ids)

            if cash_out_data.empty:
                cashed_out = True
                I("No cash out data found")
            else:
                # Filter data to only include the specified selection IDs
                filtered_cash_out_data = cash_out_data[
                    cash_out_data["selection_id"].astype(str).isin(selection_ids_str)
                ]

                if filtered_cash_out_data.empty:
                    cashed_out = True
                    I(f"No bets found for selection IDs {selection_ids_str}")
                else:
                    I(
                        f"Found {len(filtered_cash_out_data)} bets to cash out for selections {selection_ids_str}"
                    )
                    cash_out_orders = self.betfair_cash_out.cash_out(
                        filtered_cash_out_data
                    )

                    if cash_out_orders:
                        I(f"Placing {len(cash_out_orders)} cash out orders")
                        self.place_orders(cash_out_orders)
                        sleep(10)
                    else:
                        cashed_out = True
                        I("No cash out orders generated")

        # Return matched orders filtered by the specified selections
        all_matched_orders = self.get_matched_orders(market_ids)
        if all_matched_orders.empty:
            return all_matched_orders

        return all_matched_orders[
            all_matched_orders["selection_id"].astype(str).isin(selection_ids_str)
        ]

    @staticmethod
    def expand_price_size(data: pd.DataFrame) -> pd.DataFrame:
        price_size_col = "price_size"

        return data.assign(
            price=lambda x: x[price_size_col].apply(lambda x: x["price"]),
            size=lambda x: x[price_size_col].apply(lambda x: x["size"]),
        ).drop(columns=[price_size_col])

    def get_balance(self):
        self.check_session()
        return self.trading_client.account.get_account_funds(
            wallet="UK", lightweight=True
        )["availableToBetBalance"]

    def get_files(self, params: BetfairHistoricalDataParams) -> list[str]:
        self.check_session()
        I(
            f"Fetching historical market data"
            f"From: {params.from_day}-{params.from_month}-{params.from_year}"
            f"To: {params.to_day}-{params.to_month}-{params.to_year}"
        )
        I(params)
        return self.trading_client.historic.get_file_list(
            "Horse Racing",
            "Basic Plan",
            from_day=params.from_day,
            from_month=params.from_month,
            from_year=params.from_year,
            to_day=params.to_day,
            to_month=params.to_month,
            to_year=params.to_year,
            market_types_collection=params.market_types_collection,
            countries_collection=params.countries_collection,
            file_type_collection=params.file_type_collection,
        )

    def fetch_historical_data(
        self,
        file: str,
    ) -> str:
        self.check_session()
        return self.trading_client.historic.download_file(file)

    def _get_order_details(self, bet_id: str) -> dict | None:
        """
        Get order details by bet ID to check matched amounts.

        Args:
            bet_id: The bet ID to look up

        Returns:
            dict with order details or None if not found
        """
        try:
            current_orders = self.trading_client.betting.list_current_orders()

            for order in current_orders.current_orders:
                if order.bet_id == bet_id:
                    return {
                        "matched_size": getattr(order, "size_matched", 0.0),
                        "matched_odds": getattr(order, "average_price_matched", 0.0),
                        "unmatched_size": getattr(order, "size_remaining", 0.0),
                        "status": getattr(order, "status", "UNKNOWN"),
                    }
            return None
        except Exception as e:
            I(f"Error fetching order details for bet {bet_id}: {e}")
            return None
