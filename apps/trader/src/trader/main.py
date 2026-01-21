import sys
from time import sleep

from api_helpers.clients import get_betfair_client, get_local_postgres_client
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    handle_network_outage,
    is_network_available,
    is_network_error,
)
from api_helpers.helpers.time_utils import get_uk_time_now

from .decision_engine import decide
from .executor import execute, fetch_selection_state, reconcile
from .price_data import fetch_prices

POLL_INTERVAL_SECONDS = 15


if __name__ == "__main__":
    betfair_client = get_betfair_client()
    postgres_client = get_local_postgres_client()

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

            # 0. Reconcile state from Betfair
            # This moves EXECUTION_COMPLETE orders to bet_log
            # (Stale order cancellation is now handled per-selection in _place_order)
            reconcile(betfair_client, postgres_client)

            # 1. Refresh live prices from Betfair
            fetch_prices(
                betfair_client=betfair_client,
                postgres_client=postgres_client,
            )

            # 2. Fetch current state from view (single query)
            selection_state = fetch_selection_state(postgres_client)

            if selection_state.empty:
                I(f"No selections found. Sleeping for {POLL_INTERVAL_SECONDS} seconds.")
                sleep(POLL_INTERVAL_SECONDS)
                continue

            I(f"Checking {len(selection_state)} selections for potential bets")

            # 3. Decide what to do
            decision = decide(selection_state)

            # 4. Execute decisions (side effects)
            if decision.orders or decision.cash_out_market_ids:
                summary = execute(decision, betfair_client, postgres_client)
                I(f"Executed: {summary}")

            # Exit if max race time is reached
            if now_timestamp > max_race_time:
                W("Max race time reached. Exiting.")
                sys.exit()

            I(f"Sleeping for {POLL_INTERVAL_SECONDS} seconds")
            sleep(POLL_INTERVAL_SECONDS)

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
