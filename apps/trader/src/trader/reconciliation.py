"""
Reconciliation - Sync Betfair state to database.

This module is responsible for ensuring our database (bet_log) reflects
the true state of orders on Betfair. Betfair is the source of truth.

Key Responsibilities:
1. Process EXECUTION_COMPLETE orders → move to bet_log
2. Detect and handle stale EXECUTABLE orders
3. Prevent duplicate entries in bet_log

This is called at the start of each trading loop BEFORE any new decisions
are made, ensuring we have accurate state before acting.
"""

from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W


@dataclass
class ReconciliationResult:
    """Result of a reconciliation run."""

    completed_moved_to_log: int = 0
    duplicates_skipped: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "completed_moved_to_log": self.completed_moved_to_log,
            "duplicates_skipped": self.duplicates_skipped,
            "errors": self.errors,
        }

    def has_changes(self) -> bool:
        return self.completed_moved_to_log > 0


# ============================================================================
# MAIN RECONCILIATION FUNCTION
# ============================================================================


def reconcile(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
) -> ReconciliationResult:
    """
    Reconcile Betfair orders with our database.

    Process:
    1. Fetch all current orders from Betfair
    2. Filter to EXECUTION_COMPLETE orders (our orders, not UI)
    3. For each, check if already in bet_log
    4. If not, store in bet_log

    Args:
        betfair_client: Betfair API client
        postgres_client: Database client

    Returns:
        ReconciliationResult with counts of actions taken
    """
    result = ReconciliationResult()

    try:
        current_orders = betfair_client.get_current_orders()

        if not current_orders:
            return result

        # Filter to completed orders from our trader (not manual UI bets)
        completed_orders = filter_completed_orders(current_orders)

        for order in completed_orders:
            try:
                processed = process_completed_order(order, postgres_client)
                if processed:
                    result.completed_moved_to_log += 1
                else:
                    result.duplicates_skipped += 1
            except Exception as e:
                E(f"Error processing order {order.bet_id}: {e}")
                result.errors += 1

        if result.has_changes():
            I(f"Reconciliation: {result.to_dict()}")

        return result

    except Exception as e:
        E(f"Error during reconciliation: {e}")
        result.errors += 1
        return result


# ============================================================================
# ORDER FILTERING
# ============================================================================


def filter_completed_orders(
    current_orders: list[CurrentOrder],
) -> list[CurrentOrder]:
    """
    Filter orders to only those that are:
    - EXECUTION_COMPLETE (fully matched)
    - From our trader (customer_strategy_ref != 'UI')
    - Have matched amount > 0

    Args:
        current_orders: List of orders from Betfair

    Returns:
        Filtered list of completed orders
    """
    return [
        order
        for order in current_orders
        if is_order_complete(order) and is_trader_order(order) and has_matched_amount(order)
    ]


def is_order_complete(order: CurrentOrder) -> bool:
    """Check if order execution is complete."""
    return order.execution_status == "EXECUTION_COMPLETE"


def is_trader_order(order: CurrentOrder) -> bool:
    """Check if order was placed by our trader (not manual UI)."""
    return order.customer_strategy_ref is not None and order.customer_strategy_ref != "UI"


def has_matched_amount(order: CurrentOrder) -> bool:
    """Check if order has any matched amount."""
    return order.size_matched is not None and order.size_matched > 0


# ============================================================================
# ORDER PROCESSING
# ============================================================================


def process_completed_order(
    order: CurrentOrder,
    postgres_client: PostgresClient,
) -> bool:
    """
    Process a single completed order - store in bet_log if not already there.

    Args:
        order: Completed order from Betfair
        postgres_client: Database client

    Returns:
        True if stored, False if skipped (already exists)
    """
    unique_id = order.customer_strategy_ref
    placed_at = pd.to_datetime(order.placed_date)

    # Check if already in bet_log
    if is_bet_in_log(postgres_client, unique_id, placed_at):
        return False

    # Store in bet_log
    return store_completed_bet(
        unique_id=unique_id,
        market_id=order.market_id,
        selection_id=order.selection_id,
        side=order.side,
        matched_size=order.size_matched,
        matched_price=order.average_price_matched,
        placed_at=placed_at,
        matched_at=(
            pd.to_datetime(order.matched_date) if order.matched_date else None
        ),
        postgres_client=postgres_client,
    )


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================


def is_bet_in_log(
    postgres_client: PostgresClient,
    unique_id: str,
    placed_at: datetime,
) -> bool:
    """
    Check if a bet is already recorded in bet_log.

    Uses unique_id + placed_at as the composite key to prevent duplicates.

    Args:
        postgres_client: Database client
        unique_id: Selection unique ID
        placed_at: When the bet was placed

    Returns:
        True if already exists, False otherwise
    """
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT 1 FROM live_betting.bet_log 
            WHERE selection_unique_id = '{unique_id}'
              AND placed_at = '{placed_at}'
            LIMIT 1
            """
        )
        return not result.empty
    except Exception as e:
        W(f"Error checking bet_log for {unique_id}: {e}")
        # Conservative: assume it exists to prevent duplicates
        return True


def store_completed_bet(
    unique_id: str,
    market_id: str,
    selection_id: int,
    side: str,
    matched_size: float,
    matched_price: float,
    placed_at: datetime,
    matched_at: datetime | None,
    postgres_client: PostgresClient,
) -> bool:
    """
    Store a completed bet in bet_log.

    Calculates liability based on side and stores the full record.

    Args:
        unique_id: Selection unique ID (links to selections table)
        market_id: Betfair market ID
        selection_id: Betfair selection ID
        side: 'BACK' or 'LAY'
        matched_size: Amount matched
        matched_price: Average price matched
        placed_at: When bet was placed
        matched_at: When bet was fully matched
        postgres_client: Database client

    Returns:
        True if stored successfully, False otherwise
    """
    # Calculate liability
    matched_liability = calculate_liability(side, matched_size, matched_price)

    # Get selection_type from selections table
    selection_type = get_selection_type(postgres_client, unique_id, side)

    data = pd.DataFrame(
        [
            {
                "selection_unique_id": unique_id,
                "market_id": market_id,
                "selection_id": selection_id,
                "side": side,
                "selection_type": selection_type,
                "matched_price": matched_price,
                "matched_size": matched_size,
                "matched_liability": matched_liability,
                "status": "MATCHED",
                "placed_at": placed_at,
                "matched_at": matched_at or placed_at,
            }
        ]
    )

    try:
        postgres_client.store_data(
            data=data,
            table="bet_log",
            schema="live_betting",
        )
        I(f"[{unique_id}] Stored in bet_log: {matched_size} @ {matched_price}")
        return True
    except Exception as e:
        E(f"[{unique_id}] Failed to store in bet_log: {e}")
        return False


def calculate_liability(
    side: str,
    matched_size: float,
    matched_price: float,
) -> float | None:
    """
    Calculate liability for a bet.

    For BACK bets: liability = stake
    For LAY bets: liability = stake * (odds - 1)

    Args:
        side: 'BACK' or 'LAY'
        matched_size: Amount matched
        matched_price: Price matched at

    Returns:
        Calculated liability or None if cannot be calculated
    """
    if side == "BACK":
        return matched_size
    elif side == "LAY" and matched_price and matched_price > 1:
        return matched_size * (matched_price - 1)
    return None


def get_selection_type(
    postgres_client: PostgresClient,
    unique_id: str,
    fallback: str,
) -> str:
    """
    Get selection_type from selections table.

    Args:
        postgres_client: Database client
        unique_id: Selection unique ID
        fallback: Value to use if not found

    Returns:
        selection_type or fallback value
    """
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT selection_type FROM live_betting.selections 
            WHERE unique_id = '{unique_id}'
            LIMIT 1
            """
        )
        if not result.empty:
            return result.iloc[0]["selection_type"]
    except Exception as e:
        W(f"Error getting selection_type for {unique_id}: {e}")
    return fallback


def get_matched_total_from_log(
    postgres_client: PostgresClient,
    unique_id: str,
) -> float:
    """
    Get total matched amount from bet_log for a selection.

    This is used to calculate remaining stake needed when placing orders.

    Args:
        postgres_client: Database client
        unique_id: Selection unique ID

    Returns:
        Total matched amount (0.0 if none or error)
    """
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT COALESCE(SUM(matched_size), 0) as total_matched
            FROM live_betting.bet_log 
            WHERE selection_unique_id = '{unique_id}'
            """
        )
        if result.empty:
            return 0.0
        return float(result.iloc[0]["total_matched"])
    except Exception as e:
        W(f"Error getting matched from log for {unique_id}: {e}")
        return 0.0
