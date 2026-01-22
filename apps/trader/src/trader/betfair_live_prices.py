import hashlib
from datetime import datetime

import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.time_utils import convert_col_utc_to_uk


def update_betfair_prices(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
):
    new_data = betfair_client.create_market_data()
    new_data = new_data.assign(
        created_at=datetime.now().replace(microsecond=0, second=0),
        race_date=new_data["race_time"].dt.date,
    )
    win_and_place = pd.merge(
        new_data[new_data["market"] == "WIN"],
        new_data[new_data["market"] == "PLACE"],
        on=[
            "race_time",
            "course",
            "todays_betfair_selection_id",
            "race_date",
        ],
        suffixes=("_win", "_place"),
    )

    win_and_place = win_and_place.rename(
        columns={
            "horse_win": "horse_name",
            "last_traded_price_win": "betfair_win_sp",
            "last_traded_price_place": "betfair_place_sp",
            "status_win": "status",
            "created_at_win": "created_at",
        }
    )
    win_and_place["race_time_string"] = win_and_place["race_time"].dt.strftime(
        "%Y%m%d%H%M"
    )
    # Build a per-row key and hash it; avoid calling .encode on a Series
    key_series = (
        win_and_place["race_time_string"].astype(str).fillna("")
        + win_and_place["course"].astype(str).fillna("")
        + win_and_place["horse_name"].astype(str).fillna("")
        + win_and_place["todays_betfair_selection_id"].astype(str).fillna("")
    )
    win_and_place["unique_id"] = key_series.map(
        lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
    )
    win_and_place = win_and_place.sort_values(by="race_time", ascending=True)

    # Count active runners per market
    active_counts = (
        win_and_place[win_and_place["status"] == "ACTIVE"]
        .groupby("market_id_win")
        .size()
    )
    data = win_and_place.assign(
        current_runner_count=win_and_place["market_id_win"]
        .map(active_counts)
        .fillna(0)
        .astype(int)
    )

    data = data.pipe(convert_col_utc_to_uk, col_name="race_time")

    new_processed_data = data.rename(
        columns={
            "todays_betfair_selection_id": "selection_id",
        }
    ).filter(
        items=[
            "race_time",
            "horse_name",
            "race_date",
            "course",
            "status",
            "market_id_win",
            "selection_id",
            "betfair_win_sp",
            "betfair_place_sp",
            "back_price_1_win",
            "back_price_1_depth_win",
            "back_price_2_win",
            "back_price_2_depth_win",
            "lay_price_1_win",
            "lay_price_1_depth_win",
            "lay_price_2_win",
            "lay_price_2_depth_win",
            "market_place",
            "market_id_place",
            "back_price_1_place",
            "back_price_1_depth_place",
            "back_price_2_place",
            "back_price_2_depth_place",
            "lay_price_1_place",
            "lay_price_1_depth_place",
            "lay_price_2_place",
            "lay_price_2_depth_place",
            "created_at",
            "unique_id",
            "current_runner_count",
        ]
    )

    postgres_client.store_data(
        new_processed_data,
        table="betfair_prices",
        schema="live_betting",
    )
