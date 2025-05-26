from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.s3_client import S3Client
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr
from api_helpers.helpers.time_utils import get_uk_time_now
from api_helpers.helpers.file_utils import S3FilePaths

paths = S3FilePaths()


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

    fully_matched_bets = s3_client.fetch_data(paths.fully_matched_bets)

    invalidated_bets, cashed_out_bets = ptr(
        lambda: s3_client.fetch_data(paths.invalidated_bets),
        lambda: s3_client.fetch_data(paths.cashed_out_bets),
    )
    selections_data, market_state_data = ptr(
        lambda: s3_client.fetch_data(paths.selections),
        lambda: s3_client.fetch_data(paths.market_state),
    )
    if selections_data.empty:
        I("No selections data found")
        return None

    # selections_data = selections_data[selections_data["race_time"] > datetime.now()]

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

    I(f"Fetching betting data from {paths.selections} and {paths.market_state}")
    I(f"Found {len(selections_data)} selections")

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
