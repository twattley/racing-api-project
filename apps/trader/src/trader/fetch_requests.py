from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.s3_client import S3Client
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr
from api_helpers.helpers.time_utils import get_uk_time_now


@dataclass
class RawBettingData:
    selections_data: pd.DataFrame
    fully_matched_bets: pd.DataFrame
    cashed_out_bets: pd.DataFrame
    invalidated_bets: pd.DataFrame
    market_state_data: pd.DataFrame
    betfair_market_data: pd.DataFrame
    current_orders: pd.DataFrame


def fetch_betting_data(
    s3_client: S3Client, betfair_client: BetFairClient
) -> RawBettingData | None:
    now_timestamp = get_uk_time_now()

    folder = f"today/{now_timestamp.strftime('%Y_%m_%d')}/trader_data"

    selections_file_path = f"{folder}/selections.parquet"
    fully_matched_bets_file_path = f"{folder}/fully_matched_bets.parquet"
    cashed_out_bets_file_path = f"{folder}/cashed_out_bets_bets.parquet"
    invalidated_bets_file_path = f"{folder}/invalidated_bets.parquet"
    market_state_file_path = f"{folder}/market_state.parquet"

    fully_matched_bets = s3_client.fetch_data(fully_matched_bets_file_path)

    invalidated_bets, cashed_out_bets = ptr(
        lambda: s3_client.fetch_data(invalidated_bets_file_path),
        lambda: s3_client.fetch_data(cashed_out_bets_file_path),
    )
    selections_data, market_state_data = ptr(
        lambda: s3_client.fetch_data(selections_file_path),
        lambda: s3_client.fetch_data(market_state_file_path),
    )
    if selections_data.empty:
        I("No selections data found")
        return None

    selections_data = selections_data[selections_data["race_time"] > datetime.now()]
    if selections_data.empty:
        I("No selections data found")
        return None

    if fully_matched_bets.empty:
        column_names = [
            "race_time",
            "race_id",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "average_price_matched",
            "size_matched",
        ]
        fully_matched_bets = pd.DataFrame(columns=column_names)

    I(f"Fetching betting data from {selections_file_path} and {market_state_file_path}")
    I(f"Found {len(selections_data)} selections")

    market_state_data = market_state_data[
        market_state_data["race_time"] > datetime.now()
    ]
    if market_state_data.empty:
        I("No market state data found")
        return None

    betfair_market_data, current_orders = ptr(
        lambda: betfair_client.create_merged_single_market_data(
            list(
                set(market_state_data["market_id_win"].unique())
                | set(market_state_data["market_id_place"].unique())
            )
        ),
        lambda: betfair_client.get_matched_orders([]),
    )
    I(f"Found {len(betfair_market_data)} betfair market data")
    I(f"Found {len(current_orders)} current orders")

    # TODO - this id feels like a bit of a hack, but it works for now
    betfair_market_data.rename(columns={"horse_id": "selection_id"}, inplace=True)

    return RawBettingData(
        selections_data=selections_data,
        fully_matched_bets=fully_matched_bets,
        cashed_out_bets=cashed_out_bets,
        invalidated_bets=invalidated_bets,
        market_state_data=market_state_data,
        betfair_market_data=betfair_market_data,
        current_orders=current_orders,
    )
