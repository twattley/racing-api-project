from trader.models import SelectionState
import sys
from time import sleep
import pandas as pd
from api_helpers.clients import get_betfair_client, get_local_postgres_client
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.network_utils import (
    handle_network_outage,
    is_network_available,
    is_network_error,
)
from api_helpers.helpers.time_utils import get_uk_time_now

from .decision_engine import decide, DecisionResult
from .executor import execute, fetch_selection_state
from .price_data import fetch_prices
from .reconciliation import reconcile
from .trading_logger import (
    log_cycle_start,
    log_selection_state_summary,
    log_decision_summary,
    log_execution_summary,
)
from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.clients.postgres_client import PostgresClient

POLL_INTERVAL_SECONDS = 10


# =============================================================================
# PRICE SERVICE - Independent concern, updates database with live prices
# =============================================================================


def update_prices(betfair_client, postgres_client) -> None:
    """
    Fetch and store live prices from Betfair.

    This is independent of the trading loop - it just keeps the
    betfair_prices table up to date. The trader reads prices via
    the v_selection_state view.
    """
    fetch_prices(
        betfair_client=betfair_client,
        postgres_client=postgres_client,
    )


# =============================================================================
# TRADING LOOP - Reconcile → Decide → Execute
# =============================================================================


def run_trading_cycle(
    betfair_client: BetFairClient, postgres_client: PostgresClient, cycle_num: int
) -> dict:
    """
    Run one cycle of the trading loop.

    Returns:
        Summary dict of actions taken, or empty dict if nothing to do.
    """
    log_cycle_start(cycle_num)

    # 1. Reconcile: Sync Betfair order state to our bet_log
    reconcile(betfair_client, postgres_client)

    # 2. Fetch: Get current selection state (includes prices via view)
    selections: list[SelectionState] = fetch_selection_state(postgres_client)

    if not selections:
        return {}

    # Log detailed selection state
    log_selection_state_summary(selections)

    # 3. Get current orders (needed for early bird duplicate detection)
    current_orders: list[CurrentOrder] = betfair_client.get_current_orders()

    # 4. Decide: Pure function - what orders to place?
    decision: DecisionResult = decide(selections, current_orders)

    # Log decisions
    log_decision_summary(
        decision.orders,
        decision.cash_out_market_ids,
        decision.invalidations,
        decision.cancel_orders,
    )

    # 5. Execute: Side effects - place orders, cash out, record invalidations
    if (
        decision.orders
        or decision.cash_out_market_ids
        or decision.invalidations
        or decision.cancel_orders
    ):
        summary = execute(decision, betfair_client, postgres_client)
        log_execution_summary(summary)
        return summary

    I("No actions required this cycle")
    return {}


# =============================================================================
# NETWORK HANDLING
# =============================================================================


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


# =============================================================================
# MAIN
# =============================================================================


if __name__ == "__main__":
    betfair_client: BetFairClient = get_betfair_client()
    postgres_client: PostgresClient = get_local_postgres_client()

    min_race_time, max_race_time = betfair_client.get_min_and_max_race_times()

    cycle_num = 0

    while True:
        cycle_num += 1

        # Pre-flight: Check network connectivity
        if not is_network_available():
            I("Network connectivity issue detected. Waiting for recovery...")
            if not handle_network_outage(max_wait_time=300, check_interval=30):
                E("Network connectivity could not be restored. Exiting.")
                sys.exit()

        try:
            now_timestamp = get_uk_time_now()

            # --- Price Service ---
            update_prices(betfair_client, postgres_client)

            # --- Trading Loop ---
            run_trading_cycle(betfair_client, postgres_client, cycle_num)

            # --- Exit Condition ---
            if now_timestamp > max_race_time:
                W("Max race time reached. Exiting.")
                sys.exit()

            sleep(POLL_INTERVAL_SECONDS)

        except Exception as e:
            if is_network_error(e):
                if not handle_network_issue(e):
                    sys.exit()
            else:
                W(f"Application error occurred: {str(e)}")
                sleep(30)
