import numpy as np
import pandas as pd
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.time_utils import get_uk_time_now
from src.fetch_requests import RawBettingData


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
    now_timestamp = get_uk_time_now()
    betfair_market_state = (
        pd.merge(
            data.market_state_data,
            data.betfair_market_data,
            on=["market_id_win", "market_id_place", "selection_id"],
            how="left",
        )
        .drop(columns=["race_time_x", "horse_name_x"])
        .rename(columns={"race_time_y": "race_time", "horse_name_y": "horse_name"})
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
            ]
        )
    )
    betfair_market_state = betfair_market_state.pipe(
        calculate_conditions_for_invalidating_orders
    )
    I("Structuring request data")
    win_betfair_data = betfair_market_state[
        [
            "race_time",
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
            "race_time",
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

    win_selections_data = data.selections_data[
        (data.selections_data["market_type"] == "WIN")
        & (data.selections_data["valid"] == True)
    ][
        [
            "id",
            "race_id",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "market_id",
            "selection_id",
            "in_dutch",
            "bet_group_id",
            "requested_odds",
        ]
    ]

    place_selections_data = data.selections_data[
        (data.selections_data["market_type"] == "PLACE")
        & (data.selections_data["valid"] == True)
    ][
        [
            "id",
            "race_id",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "market_id",
            "selection_id",
            "in_dutch",
            "bet_group_id",
            "requested_odds",
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

    selections_data = pd.concat([win_selections_data, place_selections_data])
    current_orders = data.current_orders[
        [
            "market_id",
            "selection_id",
            "selection_type",
            "average_price_matched",
            "size_matched",
        ]
    ]

    request_data = pd.merge(
        selections_data,
        current_orders,
        on=["market_id", "selection_id", "selection_type"],
        how="left",
    ).assign(
        size_matched=lambda x: pd.to_numeric(x["size_matched"], errors="coerce").fillna(
            0
        ),
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

    return request_data[
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
            "average_price_matched",
            "size_matched",
        ]
    ]
