import os
import time

from dotenv import load_dotenv

load_dotenv(
    dotenv_path="/Users/tomwattley/App/racing-api-project/racing-api-project/libraries/api-helpers/src/api_helpers/.env"
)

from api_helpers.clients import get_local_postgres_client, get_remote_postgres_client

if __name__ == "__main__":
    local_pg_client = get_local_postgres_client()
    remote_pg_client = get_remote_postgres_client()

    interval_seconds = int(os.getenv("LIVE_PRICES_SYNC_INTERVAL", "10"))
    error_sleep_seconds = int(os.getenv("LIVE_PRICES_ERROR_SLEEP", "10"))
    print(
        f"Starting live prices sync loop (interval: {interval_seconds}s)...", flush=True
    )

    try:
        while True:
            # Fetch
            try:
                data = remote_pg_client.fetch_data(
                    """
                        SELECT 
                            todays_betfair_selection_id as selection_id,
                            betfair_win_sp,
                            betfair_place_sp,
                            status,
                            created_at
                        FROM live_betting.updated_price_data
                        WHERE race_time::date = current_date
                          AND race_time > current_timestamp
                    """
                )
            except Exception as e:
                print(f"Fetch error: {e}", flush=True)
                time.sleep(error_sleep_seconds)
                continue

            # Optional: skip if no rows
            try:
                if data is None or (hasattr(data, "empty") and data.empty):
                    print("No data returned; skipping store.", flush=True)
                else:
                    local_pg_client.store_latest_data(
                        data=data,
                        schema="live_betting",
                        table="updated_price_data",
                        unique_columns=["selection_id"],
                        created_at=True,
                    )
                    print(
                        f"Synced live prices at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                        flush=True,
                    )
            except Exception as e:
                print(f"Store error: {e}", flush=True)

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("Interrupted. Exiting live prices sync loop.", flush=True)
