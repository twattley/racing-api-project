import sys
from time import sleep

import pandas as pd
from api_helpers.helpers.logging_config import I, W
from api_helpers.helpers.time_utils import get_uk_time_now
from src.fetch_requests import fetch_betting_data
from src.market_trader import MarketTrader
from src.prepare_requests import prepare_request_data
from src.storage.clients import get_betfair_client, get_s3_client

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
    s3_client = get_s3_client()
    betfair_client = get_betfair_client()

    trader = MarketTrader(
        s3_client=s3_client,
        betfair_client=betfair_client,
        stake_size=STAKE_SIZE,
    )
    price_data = betfair_client.create_market_data()
    min_race_time = price_data["race_time"].min()
    max_race_time = price_data["race_time"].max()

    while True:
        now_timestamp = get_uk_time_now()
        betting_data = fetch_betting_data(s3_client, betfair_client)

        if not betting_data:
            sleep(60)
            continue

        requests_data = prepare_request_data(betting_data)

        trader.trade_markets(
            requests_data=requests_data,
            betting_data=betting_data,
            now_timestamp=now_timestamp,
        )
        # Exit if max race time is reached
        if now_timestamp > max_race_time:
            W("Max race time reached. Exiting.")
            sys.exit()

        sleep_time = set_sleep_interval(requests_data, min_race_time, now_timestamp)

        I(f"Sleeping for {sleep_time} seconds")
        sleep(sleep_time)
