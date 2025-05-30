from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.s3_client import S3Client
from api_helpers.helpers.file_utils import S3FilePaths
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr

paths = S3FilePaths()


@dataclass
class BettingData:
    selections: pd.DataFrame
    market_state: pd.DataFrame


@dataclass
class MarketData:
    betfair_market: pd.DataFrame
    current_orders: pd.DataFrame


@dataclass
class RawBettingData:
    betting_data: BettingData
    market_data: MarketData


def fetch_betting_data(
    s3_client: S3Client, betfair_client: BetFairClient
) -> RawBettingData | None:
    market_state_data, selections_data = ptr(
        lambda: s3_client.fetch_data(paths.market_state),
        lambda: s3_client.fetch_data(paths.selections),
    )
    if selections_data.empty:
        I("No selections data found")
        return None

    I(f"Fetching betting data from {paths.selections} and {paths.market_state}")
    I(f"Found {len(selections_data)} selections")
    future_market_data = market_state_data[
        market_state_data["race_time"] > datetime.now()
    ].copy()
    market_ids = list(
        set(future_market_data["market_id_win"].unique())
        | set(future_market_data["market_id_place"].unique())
    )
    betfair_market_data, current_orders = ptr(
        lambda: betfair_client.create_merged_single_market_data(market_ids),
        lambda: betfair_client.get_matched_orders(market_ids),
    )
    I(f"Found {len(betfair_market_data)} betfair market data")
    I(f"Found {len(current_orders)} current orders")

    # TODO - this id feels like a bit of a hack, but it works for now
    betfair_market_data.rename(columns={"horse_id": "selection_id"}, inplace=True)

    return RawBettingData(
        betting_data=BettingData(
            selections=selections_data,
            market_state=market_state_data,
        ),
        market_data=MarketData(
            betfair_market=betfair_market_data,
            current_orders=current_orders,
        ),
    )
