import os
import sys
from datetime import datetime
from time import sleep

import pandas as pd
from api_helpers.clients.betfair_client import (
    BetFairClient,
    BetfairCredentials,
    BetFairCashOut,
)
from api_helpers.clients.s3_client import S3Client, S3Connection
from api_helpers.helpers.logging_config import I, W, E
from api_helpers.helpers.processing_utils import pt
from api_helpers.helpers.time_utils import get_uk_time_now

from src.config import config
from src.prices_service import PricesService


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
    price_data: pd.DataFrame,
    previous_price_data: pd.DataFrame,
    s3_storage_client: S3Client,
    prices_service: PricesService,
    file_path: str,
):
    keep_count = 3
    combined_data = prices_service.combine_new_market_data(
        price_data, previous_price_data
    )
    updated_data = prices_service.update_price_data(combined_data)
    updated_data = updated_data.assign(created_at=datetime.now())

    pt(
        lambda: s3_storage_client.store_with_timestamp(
            data=combined_data,
            base_path=file_path,
            file_prefix="combined_price_data",
            file_name="combined_price_data",
            keep_count=keep_count,
        ),
        lambda: s3_storage_client.store_with_timestamp(
            data=updated_data,
            base_path=file_path,
            file_prefix="updated_price_data",
            file_name="updated_price_data",
            keep_count=keep_count,
        ),
    )


def run_prices_update_loop():
    betfair_client = BetFairClient(
        BetfairCredentials(
            username=config.bf_username,
            password=config.bf_password,
            app_key=config.bf_app_key,
            certs_path=config.bf_certs_path,
        ),
        BetFairCashOut(),
    )
    s3_storage_client = S3Client(
        S3Connection(
            access_key_id=config.s3_access_key,
            secret_access_key=config.s3_secret_access_key,
            region_name=config.s3_region_name,
            endpoint_url=config.s3_endpoint_url,
            bucket_name=config.s3_bucket_name,
        )
    )
    prices_service = PricesService()
    today_date_str = datetime.now().strftime("%Y_%m_%d")
    s3_file_path = f"today/{today_date_str}/price_data"
    _, max_race_time = betfair_client.get_min_and_max_race_times()
    backoff_counter = 0

    log_file_folder = f"/{config.log_file_dir}/{today_date_str}"

    if not os.path.exists(log_file_folder):
        os.makedirs(log_file_folder)

    log_file_path = f"/{log_file_folder}/execution.log"

    while True:
        try:
            with open(log_file_path, "w") as f:
                f.truncate(0)

            I(
                f"Getting price data, current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} and max race time: {max_race_time}"
            )
            price_data = betfair_client.create_market_data()
            if max_race_time is None:
                max_race_time = price_data["race_time"].max()
                I(f"Setting max race time to {max_race_time}")
            previous_price_data = s3_storage_client.fetch_data(
                s3_storage_client.get_latest_timestamped_file(
                    base_path=s3_file_path,
                    file_prefix="combined_price_data",
                    file_name="combined_price_data",
                )
            )
            sleep_interval = get_sleep_interval(price_data["race_time"].min())
            update_betfair_prices(
                price_data,
                previous_price_data,
                s3_storage_client,
                prices_service,
                s3_file_path,
            )
            sleep(sleep_interval)
            backoff_counter = 0
        except Exception as e:
            W(f"Error occurred: {str(e)}")
            backoff_counter += 1
            sleep((backoff_counter**2) * 10)
            if backoff_counter > 10:
                E(f"Backoff counter exceeded 10. Exiting with error: {str(e)}")
                sys.exit()

        # Exit if max race time is reached
        if get_uk_time_now() > max_race_time:
            W("Max race time reached. Exiting.")
            betfair_client.logout()
            sys.exit()


if __name__ == "__main__":
    run_prices_update_loop()
