import sys
from datetime import datetime
from time import sleep
from zoneinfo import ZoneInfo

import pandas as pd
from api_helpers.clients import get_betfair_client, get_cloud_postgres_client
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    handle_network_outage,
    is_network_available,
    is_network_error,
)
from api_helpers.helpers.time_utils import get_uk_time_now
from trader.utils import load_staking_config

from .betfair_live_prices import update_betfair_prices, update_live_betting_data
from .fetch_requests import fetch_betting_data
from .market_trader import MarketTrader
from .prepare_requests import prepare_request_data


def set_sleep_interval(
    now_timestamp: pd.Timestamp,
) -> int:
    earliest_timestamp = datetime.now(ZoneInfo("Europe/London")).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    if now_timestamp < earliest_timestamp:
        return 120  # Sleep for 2 minutes if before 10 AM UK time
    else:
        return 15  # Sleep for 15 seconds if after 10 AM UK time


if __name__ == "__main__":
    betfair_client = get_betfair_client()
    postgres_client = get_cloud_postgres_client()
    staking_config = load_staking_config()

    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
        staking_config=staking_config,
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
            update_betfair_prices(
                betfair_client=betfair_client,
                postgres_client=postgres_client,
            )
            update_live_betting_data(
                betfair_client=betfair_client,
                postgres_client=postgres_client,
            )
            betting_data = fetch_betting_data(postgres_client, betfair_client)

            if not betting_data:
                sleep_time = set_sleep_interval(now_timestamp)
                I(
                    f"No betting data found. Waiting for {sleep_time} seconds before retrying."
                )
                sleep(sleep_time)
                continue

            requests_data = prepare_request_data(betting_data)

            trader.trade_markets(
                now_timestamp=now_timestamp,
                requests_data=requests_data,
            )
            # Exit if max race time is reached
            if now_timestamp > max_race_time:
                W("Max race time reached. Exiting.")
                sys.exit()

            sleep_time = set_sleep_interval(now_timestamp)

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
