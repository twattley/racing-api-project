import sys
from datetime import datetime
from pathlib import Path
from time import sleep

import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    is_network_available,
    handle_network_outage,
    is_network_error,
)
from api_helpers.helpers.processing_utils import pt
from api_helpers.helpers.time_utils import get_uk_time_now

from .prices_service import PricesService


def get_sleep_interval(first_race_time: pd.Timestamp) -> int:
    current_time = pd.Timestamp(get_uk_time_now())
    hours_to_first_race = int((first_race_time - current_time).total_seconds() / 3600)
    if hours_to_first_race > 2:
        I("Sleeping for 1 mins")
        return 120
    if hours_to_first_race > 1:
        I("Sleeping for 60 seconds")
        return 60
    I("Sleeping for 5 seconds")
    return 10


def update_betfair_prices(
    new_data: pd.DataFrame,
    existing_data: pd.DataFrame,
    postgres_client: PostgresClient,
    prices_service: PricesService,
):
    processed_data = prices_service.process_new_market_data(new_data)
    updated_data = prices_service.update_price_data(existing_data, processed_data)

    pt(
        lambda: postgres_client.store_data(
            data=processed_data,
            table="combined_price_data",
            schema="live_betting",
        ),
        lambda: postgres_client.store_latest_data(
            data=updated_data,
            table="updated_price_data",
            schema="live_betting",
            unique_columns=[
                "market_id_win",
                "market_id_place",
                "todays_betfair_selection_id",
            ],
        ),
    )


def run_prices_update_loop():
    betfair_client = get_betfair_client()
    postgres_client = get_postgres_client()
    prices_service = PricesService()
    today_date_str = datetime.now().strftime("%Y_%m_%d")
    _, max_race_time = betfair_client.get_min_and_max_race_times()
    backoff_counter = 0

    while True:
        # Check network connectivity at the start of each loop
        if not is_network_available():
            I(
                "Network connectivity issue detected at start of loop. Waiting for recovery..."
            )
            if not handle_network_outage(max_wait_time=300, check_interval=30):
                E("Network connectivity could not be restored. Exiting.")
                betfair_client.logout()
                sys.exit()
            # Reset backoff counter after network recovery
            backoff_counter = 0

        try:
            new_data = betfair_client.create_market_data()

            existing_data = postgres_client.fetch_data(
                "SELECT * FROM live_betting.combined_price_data WHERE race_date = CURRENT_DATE",
            )
            sleep_interval = get_sleep_interval(new_data["race_time"].min())
            update_betfair_prices(
                new_data,
                existing_data,
                postgres_client,
                prices_service,
            )
            sleep(sleep_interval)
            backoff_counter = 0  # Reset backoff counter on success

        except Exception as e:
            # Check if this is a network-related error
            if is_network_error(e):
                W(f"Network error detected: {str(e)}")

                # Verify if network is actually down
                if not is_network_available():
                    I("Network outage confirmed. Waiting for recovery...")
                    if handle_network_outage(max_wait_time=300, check_interval=30):
                        I("Network recovered. Continuing operations.")
                        # Don't increment backoff counter for network issues
                        continue
                    else:
                        E("Network could not be restored. Exiting.")
                        betfair_client.logout()
                        sys.exit()
                else:
                    I(
                        "Network appears available. This may be a service-specific issue."
                    )
                    # Treat as regular error and apply backoff
                    W(f"Service error occurred: {str(e)}")
                    backoff_counter += 1
            else:
                # Non-network error - apply regular backoff
                W(f"Application error occurred: {str(e)}")
                backoff_counter += 1

            # Apply exponential backoff for non-network errors
            sleep_time = min((backoff_counter**2) * 10, 300)  # Cap at 5 minutes
            I(
                f"Sleeping for {sleep_time} seconds due to error (attempt {backoff_counter})"
            )
            sleep(sleep_time)

            if backoff_counter > 10:
                betfair_client.logout()
                E(f"Backoff counter exceeded 10. Exiting with error: {str(e)}")
                sys.exit()

        # Exit if max race time is reached
        if get_uk_time_now() > max_race_time:
            W("Max race time reached. Exiting.")
            betfair_client.logout()
            sys.exit()


if __name__ == "__main__":
    run_prices_update_loop()
