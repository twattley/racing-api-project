from datetime import datetime

import numpy as np
import pandas as pd
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.time_utils import convert_col_utc_to_uk

from .fetch_requests import RawBettingData

FINAL_COLS = [
    "unique_id",
    "race_id",
    "race_date",
    "horse_id",
    "horse_name",
    "selection_type",
    "market_type",
    "market_id",
    "selection_id",
    "requested_odds",
    "race_time",
    "minutes_to_race",
    "back_price_1",
    "back_price_1_depth",
    "back_price_2",
    "back_price_2_depth",
    "lay_price_1",
    "lay_price_1_depth",
    "lay_price_2",
    "lay_price_2_depth",
    "eight_to_seven_runners",
    "short_price_removed_runners",
    "average_price_matched_selections",
    "size_matched_selections",
    "customer_strategy_ref_selections",
    "average_price_matched_betfair",
    "size_matched_betfair",
    "customer_strategy_ref_betfair",
    "valid",
    "invalidated_at",
    "invalidated_reason",
    "fully_matched",
    "cashed_out",
    "processed_at",
    "price_change",
]


def calculate_eight_to_seven_runners(data: pd.DataFrame) -> pd.DataFrame:
    data = data.assign(
        active_runner_ind=lambda x: np.where(x["status_win"] == "ACTIVE", 1, 0),
        number_of_active_runners=lambda x: x.groupby("race_id")[
            "active_runner_ind"
        ].transform("sum"),
        eight_to_seven_runners=lambda x: np.where(
            (x["number_of_active_runners"] <= 7) & (x["number_of_runners"] >= 8),
            True,
            False,
        ),
    )
    return data.drop(columns=["active_runner_ind", "number_of_active_runners"])


def calculate_short_price_removed_runners(data: pd.DataFrame) -> pd.DataFrame:
    data = data.assign(
        short_price_removed_ind=lambda x: np.where(
            (x["back_price_win"] < 12) & (x["status_win"] == "REMOVED"), 1, 0
        ),
        short_price_removed_runners_count=lambda x: x.groupby("race_id")[
            "short_price_removed_ind"
        ].transform("sum"),
        short_price_removed_runners=lambda x: np.where(
            x["short_price_removed_runners_count"] > 0, True, False
        ),
    )
    return data.drop(
        columns=["short_price_removed_ind", "short_price_removed_runners_count"]
    )


def calculate_conditions_for_invalidating_orders(data: pd.DataFrame) -> pd.DataFrame:
    return data.pipe(calculate_eight_to_seven_runners).pipe(
        calculate_short_price_removed_runners
    )


def prepare_request_data(data: RawBettingData) -> pd.DataFrame:
    now_timestamp = datetime.now()

    betfair_market_with_prices = pd.merge(
        data.market_data.betfair_market,
        data.market_data.price_updates,
        on=["market_id_win", "market_id_place", "selection_id"],
        how="left",
    )
    betfair_market_state = (
        pd.merge(
            data.betting_data.market_state,
            betfair_market_with_prices,
            on=["market_id_win", "market_id_place", "selection_id"],
            how="left",
        )
        .drop(columns=["race_time_x"])
        .rename(columns={"race_time_y": "race_time"})
        .filter(
            items=[
                "horse_name",
                "selection_id",
                "market_id_win",
                "market_id_place",
                "back_price_win",
                "lay_price_win",
                "back_price_place",
                "lay_price_place",
                "race_id",
                "race_date",
                "number_of_runners",
                "race_time",
                "market_win",
                "status_win",
                "betfair_win_sp",
                "total_matched_win",
                "back_price_1_win",
                "back_price_1_depth_win",
                "back_price_2_win",
                "back_price_2_depth_win",
                "lay_price_1_win",
                "lay_price_1_depth_win",
                "lay_price_2_win",
                "lay_price_2_depth_win",
                "market_place",
                "status_place",
                "betfair_place_sp",
                "back_price_1_place",
                "back_price_1_depth_place",
                "back_price_2_place",
                "back_price_2_depth_place",
                "lay_price_1_place",
                "lay_price_1_depth_place",
                "lay_price_2_place",
                "lay_price_2_depth_place",
                "price_change",
            ]
        )
    )
    betfair_market_state = betfair_market_state.pipe(
        calculate_conditions_for_invalidating_orders
    ).pipe(
        convert_col_utc_to_uk,
        "race_time",
    )
    I("Structuring request data")
    win_betfair_data = betfair_market_state[
        [
            "status_win",
            "market_id_win",
            "selection_id",
            "betfair_win_sp",
            "back_price_1_win",
            "back_price_1_depth_win",
            "back_price_2_win",
            "back_price_2_depth_win",
            "lay_price_1_win",
            "lay_price_1_depth_win",
            "lay_price_2_win",
            "lay_price_2_depth_win",
            "eight_to_seven_runners",
            "short_price_removed_runners",
            "price_change",
        ]
    ].rename(
        columns={
            "market_id_win": "market_id",
            "status_win": "status",
            "betfair_win_sp": "last_traded_price",
            "back_price_1_win": "back_price_1",
            "back_price_1_depth_win": "back_price_1_depth",
            "back_price_2_win": "back_price_2",
            "back_price_2_depth_win": "back_price_2_depth",
            "lay_price_1_win": "lay_price_1",
            "lay_price_1_depth_win": "lay_price_1_depth",
            "lay_price_2_win": "lay_price_2",
            "lay_price_2_depth_win": "lay_price_2_depth",
        }
    )
    place_betfair_data = betfair_market_state[
        [
            "status_place",
            "market_id_place",
            "selection_id",
            "betfair_place_sp",
            "back_price_1_place",
            "back_price_1_depth_place",
            "back_price_2_place",
            "back_price_2_depth_place",
            "lay_price_1_place",
            "lay_price_1_depth_place",
            "lay_price_2_place",
            "lay_price_2_depth_place",
            "eight_to_seven_runners",
            "short_price_removed_runners",
            "price_change",
        ]
    ].rename(
        columns={
            "market_id_place": "market_id",
            "status_place": "status",
            "betfair_place_sp": "last_traded_price",
            "back_price_1_place": "back_price_1",
            "back_price_1_depth_place": "back_price_1_depth",
            "back_price_2_place": "back_price_2",
            "back_price_2_depth_place": "back_price_2_depth",
            "lay_price_1_place": "lay_price_1",
            "lay_price_1_depth_place": "lay_price_1_depth",
            "lay_price_2_place": "lay_price_2",
            "lay_price_2_depth_place": "lay_price_2_depth",
        }
    )

    win_selections_data = data.betting_data.selections[
        (data.betting_data.selections["market_type"] == "WIN")
        & (data.betting_data.selections["valid"] == True)
    ][
        [
            "unique_id",
            "race_id",
            "race_date",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "market_id",
            "selection_id",
            "requested_odds",
            "race_time",
            "average_price_matched",
            "size_matched",
            "customer_strategy_ref",
            "valid",
            "invalidated_at",
            "invalidated_reason",
            "fully_matched",
            "cashed_out",
            "processed_at",
        ]
    ]

    place_selections_data = data.betting_data.selections[
        (data.betting_data.selections["market_type"] == "PLACE")
        & (data.betting_data.selections["valid"] == True)
    ][
        [
            "unique_id",
            "race_id",
            "race_date",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "market_id",
            "selection_id",
            "requested_odds",
            "race_time",
            "average_price_matched",
            "size_matched",
            "customer_strategy_ref",
            "valid",
            "invalidated_at",
            "invalidated_reason",
            "fully_matched",
            "cashed_out",
            "processed_at",
        ]
    ]
    win_selections_data = pd.merge(
        win_selections_data,
        win_betfair_data,
        on=["market_id", "selection_id"],
        how="left",
    )
    place_selections_data = pd.merge(
        place_selections_data,
        place_betfair_data,
        on=["market_id", "selection_id"],
        how="left",
    )

    selections_data = pd.concat([win_selections_data, place_selections_data]).pipe(
        convert_col_utc_to_uk, "race_time"
    )

    current_orders = data.market_data.current_orders[
        [
            "market_id",
            "selection_id",
            "selection_type",
            "average_price_matched",
            "size_matched",
            "customer_strategy_ref",
        ]
    ]

    request_data = (
        pd.merge(
            selections_data,
            current_orders,
            on=["market_id", "selection_id"],
            how="left",
            suffixes=("_selections", "_betfair"),
        )
        .rename(
            columns={
                "selection_type_selections": "selection_type",
            }
        )
        .drop(columns=["selection_type_betfair"])
    )
    request_data = request_data.assign(
        size_matched_betfair=lambda x: pd.to_numeric(
            x["size_matched_betfair"], errors="coerce"
        ).fillna(0),
        hours_to_race=lambda x: (
            (x["race_time"] - now_timestamp).dt.total_seconds() / 3600
        )
        .round(0)
        .astype(int),
        minutes_to_race=lambda x: (
            (x["race_time"] - now_timestamp).dt.total_seconds() / 60
        )
        .round(0)
        .astype(int),
        seconds_to_race=lambda x: ((x["race_time"] - now_timestamp).dt.total_seconds())
        .round(0)
        .astype(int),
    )

    return request_data[FINAL_COLS].copy()
