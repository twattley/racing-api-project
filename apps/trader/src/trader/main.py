import sys
from time import sleep

import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.helpers.file_utils import S3FilePaths
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    handle_network_outage,
    is_network_available,
    is_network_error,
)
from api_helpers.helpers.time_utils import get_uk_time_now

from .fetch_requests import fetch_betting_data
from .market_trader import MarketTrader
from .prepare_requests import prepare_request_data
from api_helpers.config import config


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
        # Check network connectivity at the start of each loop
        if not is_network_available():
            I(
                "Network connectivity issue detected at start of loop. Waiting for recovery..."
            )
            if not handle_network_outage(max_wait_time=300, check_interval=30):
                E("Network connectivity could not be restored. Exiting.")
                sys.exit()

        try:
            now_timestamp = get_uk_time_now()
            betting_data = fetch_betting_data(postgres_client, betfair_client)

            if not betting_data:
                I("No betting data found. Waiting for 60 seconds before retrying.")
                sleep(60)
                continue

            requests_data = prepare_request_data(betting_data)

            trader.trade_markets(
                stake_size=config.stake_size,
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

        except Exception as e:
            # Check if this is a network-related error
            if is_network_error(e):
                W(f"Network error detected: {str(e)}")

                # Verify if network is actually down
                if not is_network_available():
                    I("Network outage confirmed. Waiting for recovery...")
                    if handle_network_outage(max_wait_time=300, check_interval=30):
                        I("Network recovered. Continuing operations.")
                        continue
                    else:
                        E("Network could not be restored. Exiting.")
                        sys.exit()
                else:
                    I(
                        "Network appears available. This may be a service-specific issue."
                    )
                    # Treat as regular error - sleep and continue
                    W(f"Service error occurred: {str(e)}")
                    sleep(60)
            else:
                # Non-network error - log and continue with short sleep
                W(f"Application error occurred: {str(e)}")
                sleep(30)
