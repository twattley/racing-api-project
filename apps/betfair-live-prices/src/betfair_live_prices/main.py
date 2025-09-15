import sys
from datetime import datetime
from time import sleep

import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    handle_network_outage,
    is_network_available,
    is_network_error,
)
from api_helpers.helpers.pipeline_status_utils import log_job_run_time
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
    return 5


def update_betfair_prices(
    new_data: pd.DataFrame,
    postgres_client: PostgresClient,
    prices_service: PricesService,
):
    processed_data = prices_service.process_new_market_data(new_data)
    new_processed_data = processed_data.rename(columns={
        "todays_betfair_selection_id": "selection_id",
    }).filter(
        items=[
            "race_time",
            "horse_name",
            "race_date",
            "course",
            "status",
            "market_id_win",
            "selection_id",
            "betfair_win_sp",
            "betfair_place_sp",
            "back_price_1_win",
            "back_price_1_depth_win",
            "back_price_2_win",
            "back_price_2_depth_win",
            "lay_price_1_win",
            "lay_price_1_depth_win",
            "lay_price_2_win",
            "lay_price_2_depth_win",
            "market_place",
            "market_id_place",
            "back_price_1_place",
            "back_price_1_depth_place",
            "back_price_2_place",
            "back_price_2_depth_place",
            "lay_price_1_place",
            "lay_price_1_depth_place",
            "lay_price_2_place",
            "lay_price_2_depth_place",
            "created_at",
            "unique_id",
        ]
    ).to_dict(orient="records")

    postgres_client.execute_query(
            """
                INSERT INTO live_betting.updated_price_data_v2(
                    race_time,
                    horse_name,
                    race_date,
                    course,
                    status,
                    market_id_win,
                    selection_id,
                    betfair_win_sp,
                    betfair_place_sp,
                    back_price_1_win,
                    back_price_1_depth_win,
                    back_price_2_win,
                    back_price_2_depth_win,
                    lay_price_1_win,
                    lay_price_1_depth_win,
                    lay_price_2_win,
                    lay_price_2_depth_win,
                    market_place,
                    market_id_place,
                    back_price_1_place,
                    back_price_1_depth_place,
                    back_price_2_place,
                    back_price_2_depth_place,
                    lay_price_1_place,
                    lay_price_1_depth_place,
                    lay_price_2_place,
                    lay_price_2_depth_place,
                    created_at,
                    unique_id
                        )
                    VALUES (
                        :race_time,
                        :horse_name,
                        :race_date,
                        :course,
                        :status,
                        :market_id_win,
                        :selection_id,
                        :betfair_win_sp,
                        :betfair_place_sp,
                        :back_price_1_win,
                        :back_price_1_depth_win,
                        :back_price_2_win,
                        :back_price_2_depth_win,
                        :lay_price_1_win,
                        :lay_price_1_depth_win,
                        :lay_price_2_win,
                        :lay_price_2_depth_win,
                        :market_place,
                        :market_id_place,
                        :back_price_1_place,
                        :back_price_1_depth_place,
                        :back_price_2_place,
                        :back_price_2_depth_place,
                        :lay_price_1_place,
                        :lay_price_1_depth_place,
                        :lay_price_2_place,
                        :lay_price_2_depth_place,
                        :created_at,
                        :unique_id
                        )
                        ON CONFLICT (unique_id)
                        DO UPDATE SET
                            status = EXCLUDED.status,
                            betfair_win_sp = EXCLUDED.betfair_win_sp,
                            betfair_place_sp = EXCLUDED.betfair_place_sp,
                            back_price_1_win = EXCLUDED.back_price_1_win,
                            back_price_1_depth_win = EXCLUDED.back_price_1_depth_win,
                            back_price_2_win = EXCLUDED.back_price_2_win,
                            back_price_2_depth_win = EXCLUDED.back_price_2_depth_win,
                            lay_price_1_win = EXCLUDED.lay_price_1_win,
                            lay_price_1_depth_win = EXCLUDED.lay_price_1_depth_win,
                            lay_price_2_win = EXCLUDED.lay_price_2_win,
                            lay_price_2_depth_win = EXCLUDED.lay_price_2_depth_win,
                            market_place = EXCLUDED.market_place,
                            market_id_place = EXCLUDED.market_id_place,
                            back_price_1_place = EXCLUDED.back_price_1_place,
                            back_price_1_depth_place = EXCLUDED.back_price_1_depth_place,
                            back_price_2_place = EXCLUDED.back_price_2_place,
                            back_price_2_depth_place = EXCLUDED.back_price_2_depth_place,
                            lay_price_1_place = EXCLUDED.lay_price_1_place,
                            lay_price_1_depth_place = EXCLUDED.lay_price_1_depth_place,
                            lay_price_2_place = EXCLUDED.lay_price_2_place,
                            lay_price_2_depth_place = EXCLUDED.lay_price_2_depth_place,
                            created_at = EXCLUDED.created_at;
                """,
                new_processed_data,
            )

def run_prices_update_loop():
    betfair_client = get_betfair_client()
    postgres_client = get_postgres_client()
    prices_service = PricesService()
    datetime.now().strftime("%Y_%m_%d")
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
            sleep_interval = get_sleep_interval(new_data["race_time"].min())
            update_betfair_prices(
                new_data,
                postgres_client,
                prices_service,
            )
            log_job_run_time("betfair_live_prices")
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
