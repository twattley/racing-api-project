import hashlib
from datetime import datetime, timedelta

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.time_utils import convert_col_utc_to_uk, get_uk_time_now
from api_helpers.helpers.simulation import simulate_place_counts


def _calculate_num_places(n_runners: int) -> int:
    """Determine number of places based on runner count (default rules)."""
    if n_runners < 8:
        return 2
    if n_runners < 16:
        return 3
    return 4


def _simulate_race_place_prices(race_df: pd.DataFrame) -> pd.DataFrame:
    """Run place simulation for a single race and return with sim columns."""
    n_runners = len(race_df)
    n_places = _calculate_num_places(n_runners)

    sim_results = simulate_place_counts(
        race_df,
        price_col="betfair_win_sp",
        horse_col="horse_name",
        n_places=n_places,
        n_sims=10000,
        seed=7,
    )

    # Merge simulation results back
    return race_df.merge(
        sim_results[["horse", "sim_place_prob", "sim_place_price"]],
        left_on="horse_name",
        right_on="horse",
        how="left",
    ).drop(columns=["horse"])

def fetch_prices(
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

    # Simulate place prices for races starting in the next 10 minutes
    now = pd.Timestamp(get_uk_time_now()).tz_localize(None)
    cutoff = now + pd.Timedelta(minutes=10)

    imminent_mask = (new_processed_data["race_time"] > now) & (
        new_processed_data["race_time"] <= cutoff
    )
    imminent_races = new_processed_data[imminent_mask]

    # Initialize sim columns as null
    new_processed_data["sim_place_prob"] = None
    new_processed_data["sim_place_price"] = None

    if not imminent_races.empty:
        # Process each imminent race
        simulated_parts = []
        for race_time in imminent_races["race_time"].unique():
            race_df = imminent_races[imminent_races["race_time"] == race_time].copy()
            # Only simulate if we have valid win prices
            if race_df["betfair_win_sp"].notna().all() and (race_df["betfair_win_sp"] > 0).all():
                sim_df = _simulate_race_place_prices(race_df)
                simulated_parts.append(sim_df)

        if simulated_parts:
            simulated = pd.concat(simulated_parts, ignore_index=True)
            # Update the main dataframe with simulation results
            sim_lookup = simulated.set_index("unique_id")[["sim_place_prob", "sim_place_price"]]
            new_processed_data.loc[imminent_mask, "sim_place_prob"] = (
                new_processed_data.loc[imminent_mask, "unique_id"].map(sim_lookup["sim_place_prob"])
            )
            new_processed_data.loc[imminent_mask, "sim_place_price"] = (
                new_processed_data.loc[imminent_mask, "unique_id"].map(sim_lookup["sim_place_price"])
            )

    postgres_client.store_data(
        new_processed_data,
        table="betfair_prices",
        schema="live_betting",
    )
