import sys
from time import sleep

from api_helpers.clients import get_betfair_client, get_local_postgres_client
from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
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
    ExecutionSummary,
    execute,
    fetch_selection_state,
    fetch_todays_unique_ids,
)
from .price_data import fetch_prices
from .reconciliation import ReconciliationResult, reconcile
from .trade_cycle import TradeCycle

POLL_INTERVAL_SECONDS = 5

# Logging options
VERBOSE_LOGGING = False  # Show all selections (not just those with bets)
CLEAR_SCREEN = True  # Clear terminal each cycle for clean view


def run_trading_cycle(
    betfair_client: BetFairClient, postgres_client: PostgresClient, cycle_num: int
) -> TradeCycle:
    """
    Run one cycle of the trading loop.

    Simplified flow:
    1. Reconcile: Cancel any unmatched orders, aggregate matched totals to bet_log
    2. Fetch: Get current selection state (includes prices via view)
    3. Decide: What orders to place?
    4. Execute: Place orders, cash out, record invalidations

    Returns:
        TradeCycle object containing all results.
    """
    cycle = TradeCycle(cycle_num=cycle_num)

    customer_refs: list[str] = fetch_todays_unique_ids(postgres_client)

    # 1. Reconcile: Cancel unmatched orders & sync Betfair state to bet_log
    cycle.reconciliation: ReconciliationResult = reconcile(
        betfair_client, postgres_client, customer_refs
    )

    # 2. Fetch: Get current selection state (includes prices via view)
    cycle.selections: list[SelectionState] = fetch_selection_state(postgres_client)

    if not cycle.selections:
        cycle.log(verbose=VERBOSE_LOGGING)
        return cycle

    # 3. Use current orders from reconcile (avoids extra API call)
    current_orders: list[CurrentOrder] = cycle.reconciliation.current_orders or []

    # 4. Decide: Pure function - what orders to place?
    cycle.decision: DecisionResult = decide(cycle.selections, current_orders)

    # 5. Execute: Side effects - place orders, cash out, record invalidations
    if (
        cycle.decision.orders
        or cycle.decision.cash_out_market_ids
        or cycle.decision.invalidations
    ):
        cycle.execution: ExecutionSummary = execute(
            cycle.decision, betfair_client, postgres_client, customer_refs
        )

    # Log everything in one place
    cycle.log(verbose=VERBOSE_LOGGING, clear_screen=CLEAR_SCREEN)

    return cycle


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
            fetch_prices(
                betfair_client=betfair_client,
                postgres_client=postgres_client,
            )

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
