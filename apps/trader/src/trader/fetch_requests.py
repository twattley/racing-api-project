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
    print("---------------------check-------------------------------")
    print(f"market_state_data: {market_state_data}")
    print("---------------------check-------------------------------")
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
    if not market_ids:
        current_orders = pd.DataFrame(
            columns=[
                "market_id",
                "selection_id",
                "selection_type",
                "average_price_matched",
                "size_matched",
                "customer_strategy_ref",
            ]
        )
        betfair_market_data = pd.DataFrame(
            columns=[
                "race_time",
                "market_win",
                "race_win",
                "course",
                "horse_name",
                "status_win",
                "market_id_win",
                "horse_id",
                "betfair_win_sp",
                "total_matched_win",
                "back_price_1_win",
                "back_price_1_depth_win",
                "back_price_2_win",
                "back_price_2_depth_win",
                "back_price_3_win",
                "back_price_3_depth_win",
                "back_price_4_win",
                "back_price_4_depth_win",
                "back_price_5_win",
                "back_price_5_depth_win",
                "lay_price_1_win",
                "lay_price_1_depth_win",
                "lay_price_2_win",
                "lay_price_2_depth_win",
                "lay_price_3_win",
                "lay_price_3_depth_win",
                "lay_price_4_win",
                "lay_price_4_depth_win",
                "lay_price_5_win",
                "lay_price_5_depth_win",
                "total_matched_event_win",
                "percent_back_win_book_win",
                "percent_lay_win_book_win",
                "market_width_win",
                "market_place",
                "race_place",
                "horse_place",
                "status_place",
                "market_id_place",
                "betfair_place_sp",
                "total_matched_place",
                "back_price_1_place",
                "back_price_1_depth_place",
                "back_price_2_place",
                "back_price_2_depth_place",
                "back_price_3_place",
                "back_price_3_depth_place",
                "back_price_4_place",
                "back_price_4_depth_place",
                "back_price_5_place",
                "back_price_5_depth_place",
                "lay_price_1_place",
                "lay_price_1_depth_place",
                "lay_price_2_place",
                "lay_price_2_depth_place",
                "lay_price_3_place",
                "lay_price_3_depth_place",
                "lay_price_4_place",
                "lay_price_4_depth_place",
                "lay_price_5_place",
                "lay_price_5_depth_place",
                "total_matched_event_place",
                "percent_back_win_book_place",
                "percent_lay_win_book_place",
                "market_width_place",
            ]
        )
        I("No future markets found, returning empty dataframes")
    else:
        I(f"Found {len(market_ids)} future markets")
        I(f"Fetching betfair market data for {len(market_ids)} markets")
        # Fetch betfair market data and current orders
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
