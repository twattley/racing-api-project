import sys
from datetime import datetime
from pathlib import Path
from time import sleep

import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.file_utils import create_todays_log_file
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.processing_utils import pt
from api_helpers.helpers.time_utils import get_uk_time_now

from .prices_service import PricesService

LOG_DIR_PATH = Path(__file__).parent.resolve() / "logs"


def get_sleep_interval(first_race_time: pd.Timestamp) -> int:
    current_time = pd.Timestamp.now(tz="Europe/London")
    hours_to_first_race = int((first_race_time - current_time).total_seconds() / 3600)
    if hours_to_first_race > 2:
        I("Sleeping for 1 mins")
        return 60
    if hours_to_first_race > 1:
        I("Sleeping for 20 seconds")
        return 20
    I("Sleeping for 5 seconds")
    return 5


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

    create_todays_log_file(LOG_DIR_PATH)

    while True:
        try:
            with open(LOG_DIR_PATH / f"execution_{today_date_str}.log", "w") as f:
                f.truncate(0)
            new_data = betfair_client.create_market_data()

            existing_data = postgres_client.fetch_data(
                "SELECT * FROM live_betting.combined_price_data",
            )
            sleep_interval = get_sleep_interval(new_data["race_time"].min())
            update_betfair_prices(
                new_data,
                existing_data,
                postgres_client,
                prices_service,
            )
            sleep(sleep_interval)
            backoff_counter = 0
        except Exception as e:
            W(f"Error occurred: {str(e)}")
            backoff_counter += 1
            sleep((backoff_counter**2) * 10)
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
