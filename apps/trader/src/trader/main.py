import sys
from pathlib import Path
from time import sleep

import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.helpers.file_utils import S3FilePaths
from api_helpers.helpers.logging_config import I, W
from api_helpers.helpers.time_utils import get_uk_time_now

from .fetch_requests import fetch_betting_data
from .market_trader import MarketTrader
from .prepare_requests import prepare_request_data

STAKE_SIZE = 5.0


def set_sleep_interval(
    requests_data: pd.DataFrame,
    min_race_time: pd.Timestamp,
    now_timestamp: pd.Timestamp,
) -> int:
    nearest_race_minutes = requests_data["minutes_to_race"].min()
    time_until_min_race_time = min_race_time - now_timestamp

    if nearest_race_minutes < 10:
        sleep_time = 10
    elif time_until_min_race_time < pd.Timedelta(
        minutes=30
    ):  # Check this if the first is false
        sleep_time = 20
    elif time_until_min_race_time < pd.Timedelta(
        hours=1
    ):  # Check this if the first two are false
        sleep_time = 60
    else:  # Only if all preceding are false
        sleep_time = 120

    return sleep_time


if __name__ == "__main__":
    betfair_client = get_betfair_client()
    postgres_client = get_postgres_client()

    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )
    min_race_time, max_race_time = betfair_client.get_min_and_max_race_times()

    while True:
        now_timestamp = get_uk_time_now()
        betting_data = fetch_betting_data(postgres_client, betfair_client)

        if not betting_data:
            I("No betting data found. Waiting for 60 seconds before retrying.")
            sleep(60)
            continue

        requests_data = prepare_request_data(betting_data)

        trader.trade_markets(
            stake_size=STAKE_SIZE,
            now_timestamp=now_timestamp,
            requests_data=requests_data,
        )
        # Exit if max race time is reached
        if now_timestamp > max_race_time:
            W("Max race time reached. Exiting.")
            sys.exit()

        sleep_time = set_sleep_interval(requests_data, min_race_time, now_timestamp)

        I(f"Sleeping for {sleep_time} seconds")
        sleep(sleep_time)
