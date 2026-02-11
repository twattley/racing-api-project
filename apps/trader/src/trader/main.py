"""
Trader main loop.

Flow each cycle:
1. Fetch prices from Betfair
2. Decide: What orders to place?
3. Execute: Place orders, cash out, record invalidations
4. Sleep 5s (let orders match)
5. Reconcile: Cancel unmatched, sync matched to bet_log

Reconciling at end means bet_log is accurate after each cycle,
with only a short stale window during the sleep.
"""

import sys
from time import sleep

from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    handle_network_outage,
    is_network_available,
    is_network_error,
)
from api_helpers.helpers.time_utils import get_uk_time_now
from trader.models import SelectionState

from .decision_engine import DecisionResult, decide
from .executor import (
    execute,
    fetch_selection_state,
    fetch_todays_unique_ids,
)
from .price_data import fetch_prices
from .reconciliation import reconcile

POLL_INTERVAL_SECONDS = 5


def run_trading_cycle(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> None:
    """
    Run one cycle of the trading loop.

    Flow:
    1. Fetch selection state (bet_log is accurate from previous reconcile)
    2. Decide: What orders to place?
    3. Execute: Place orders, cash out, record invalidations
    4. Sleep (let orders match)
    5. Reconcile: Cancel unmatched, sync matched to bet_log
    """
    customer_refs: list[str] = fetch_todays_unique_ids(postgres_client)

    # 1. Fetch: Get current selection state (bet_log accurate from last reconcile)
    selections: list[SelectionState] = fetch_selection_state(postgres_client)

    if not selections:
        return

    # 2. Decide: What orders to place?
    decision: DecisionResult = decide(selections)

    # 3. Execute: Place orders, cash out, record invalidations
    if decision.orders or decision.cash_out_market_ids or decision.invalidations:
        execute(decision, betfair_client, postgres_client, customer_refs)

    # 4. Sleep: Give orders time to match
    sleep(POLL_INTERVAL_SECONDS)

    # 5. Reconcile: Cancel unmatched, sync matched to bet_log
    reconcile(betfair_client, postgres_client, customer_refs)


def handle_network_issue(error: Exception) -> bool:
    """
    Handle a potential network error.

    Returns:
        True if we should continue the loop, False if we should exit.
    """
    W(f"Network error detected: {str(error)}")

    if not is_network_available():
        I("Network outage confirmed. Waiting for recovery...")
        if handle_network_outage(max_wait_time=300, check_interval=30):
            I("Network recovered. Continuing operations.")
            return True
        else:
            E("Network could not be restored. Exiting.")
            return False
    else:
        I("Network appears available. This may be a service-specific issue.")
        W(f"Service error occurred: {str(error)}")
        sleep(60)
        return True


if __name__ == "__main__":
    betfair_client: BetFairClient = get_betfair_client()
    postgres_client: PostgresClient = get_postgres_client()

    min_race_time, max_race_time = betfair_client.get_min_and_max_race_times()

    while True:
        # Pre-flight: Check network connectivity
        if not is_network_available():
            I("Network connectivity issue detected. Waiting for recovery...")
            if not handle_network_outage(max_wait_time=300, check_interval=30):
                E("Network connectivity could not be restored. Exiting.")
                sys.exit()

        try:
            now_timestamp = get_uk_time_now()

            # --- Price Service ---
            fetch_prices(
                betfair_client=betfair_client,
                postgres_client=postgres_client,
            )

            # --- Trading Loop ---
            run_trading_cycle(betfair_client, postgres_client)

            # --- Exit Condition ---
            if now_timestamp > max_race_time:
                W("Max race time reached. Exiting.")
                sys.exit()

        except Exception as e:
            if is_network_error(e):
                if not handle_network_issue(e):
                    sys.exit()
            else:
                W(f"Application error occurred: {str(e)}")
                sleep(30)
