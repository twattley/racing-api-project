"""
Reconciliation - Sync Betfair state to database.

This module is responsible for ensuring our database reflects
the true state of orders on Betfair. Betfair is the source of truth.

Key Responsibilities:
1. Process EXECUTION_COMPLETE orders → upsert to bet_log
2. Process EXECUTABLE orders → upsert to pending_orders
3. Clean up pending_orders for completed orders

Both tables use one row per selection (upsert on selection_unique_id).
This is called at the start of each trading loop BEFORE any new decisions
are made, ensuring we have accurate state before acting.
"""

from dataclasses import dataclass

from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W


@dataclass
class ReconciliationResult:
    """Result of a reconciliation run."""

    completed_upserted: int = 0
    pending_upserted: int = 0
    pending_cleaned: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "completed_upserted": self.completed_upserted,
            "pending_upserted": self.pending_upserted,
            "pending_cleaned": self.pending_cleaned,
            "errors": self.errors,
        }

    def has_changes(self) -> bool:
        """Only consider cleanup/errors as 'changes' worth logging."""
        return self.pending_cleaned > 0 or self.errors > 0


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
    1. Fetch all current orders from Betfair (our trader orders only)
    2. EXECUTION_COMPLETE orders → upsert to bet_log, remove from pending_orders
    3. EXECUTABLE orders → upsert to pending_orders

    Both tables maintain one row per selection_unique_id.

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

        # Filter to our trader orders only (not manual UI bets)
        trader_orders = [o for o in current_orders if is_trader_order(o)]

        for order in trader_orders:
            try:
                if is_order_complete(order):
                    # Completed order → upsert to bet_log
                    if upsert_completed_order(order, postgres_client):
                        result.completed_upserted += 1
                    # Remove from pending_orders if exists
                    if remove_pending_order(
                        order.customer_strategy_ref, postgres_client
                    ):
                        result.pending_cleaned += 1
                else:
                    # Executable order → upsert to pending_orders
                    if upsert_pending_order(order, postgres_client):
                        result.pending_upserted += 1
            except Exception as e:
                E(f"Error processing order {order.bet_id}: {e}")
                result.errors += 1

        # Only log if there are changes, errors, or first time seeing orders
        if result.has_changes() or result.errors > 0:
            I(f"Reconciliation: {result.to_dict()}")

        return result

    except Exception as e:
        E(f"Error during reconciliation: {e}")
        result.errors += 1
        return result


# ============================================================================
# ORDER FILTERING
# ============================================================================


def is_order_complete(order: CurrentOrder) -> bool:
    """Check if order execution is complete."""
    return order.execution_status == "EXECUTION_COMPLETE"


def is_trader_order(order: CurrentOrder) -> bool:
    """Check if order was placed by our trader (not manual UI)."""
    return (
        order.customer_strategy_ref is not None and order.customer_strategy_ref != "UI"
    )


# ============================================================================
# DATABASE OPERATIONS - UPSERTS
# ============================================================================


def upsert_completed_order(
    order: CurrentOrder,
    postgres_client: PostgresClient,
) -> bool:
    """
    Upsert a completed order to bet_log.

    Uses ON CONFLICT DO UPDATE on selection_unique_id.
    One row per selection in bet_log.

    Args:
        order: Completed order from Betfair
        postgres_client: Database client

    Returns:
        True if upserted successfully, False otherwise
    """
    unique_id = order.customer_strategy_ref
    selection_type = get_selection_type(postgres_client, unique_id, order.side)
    matched_liability = calculate_liability(
        order.side, order.size_matched, order.average_price_matched
    )

    query = """
        INSERT INTO live_betting.bet_log (
            selection_unique_id, bet_id, market_id, selection_id, side,
            selection_type, requested_price, requested_size,
            matched_size, matched_price, size_remaining, size_lapsed, size_cancelled,
            matched_liability, betfair_status, status, placed_at, matched_at
        ) VALUES (
            :unique_id, :bet_id, :market_id, :selection_id, :side,
            :selection_type, :requested_price, :requested_size,
            :matched_size, :matched_price, :size_remaining, :size_lapsed, :size_cancelled,
            :matched_liability, :betfair_status, 'MATCHED', :placed_at, :matched_at
        )
        ON CONFLICT (selection_unique_id) DO UPDATE SET
            bet_id = EXCLUDED.bet_id,
            matched_size = EXCLUDED.matched_size,
            matched_price = EXCLUDED.matched_price,
            size_remaining = EXCLUDED.size_remaining,
            size_lapsed = EXCLUDED.size_lapsed,
            size_cancelled = EXCLUDED.size_cancelled,
            matched_liability = EXCLUDED.matched_liability,
            betfair_status = EXCLUDED.betfair_status,
            status = 'MATCHED',
            matched_at = EXCLUDED.matched_at
    """

    try:
        postgres_client.execute_query(
            query,
            {
                "unique_id": unique_id,
                "bet_id": order.bet_id,
                "market_id": order.market_id,
                "selection_id": order.selection_id,
                "side": order.side,
                "selection_type": selection_type,
                "requested_price": order.price,
                "requested_size": order.size,
                "matched_size": order.size_matched,
                "matched_price": order.average_price_matched,
                "size_remaining": order.size_remaining,
                "size_lapsed": order.size_lapsed,
                "size_cancelled": order.size_cancelled,
                "matched_liability": matched_liability,
                "betfair_status": order.execution_status,
                "placed_at": order.placed_date,
                "matched_at": order.matched_date or order.placed_date,
            },
        )
        # Don't log every upsert - logged in reconciliation summary
        return True
    except Exception as e:
        E(f"[{unique_id}] Failed to upsert to bet_log: {e}")
        return False


def upsert_pending_order(
    order: CurrentOrder,
    postgres_client: PostgresClient,
) -> bool:
    """
    Upsert an executable order to pending_orders.

    Uses ON CONFLICT DO UPDATE on selection_unique_id.
    One row per selection in pending_orders.

    Args:
        order: Executable order from Betfair
        postgres_client: Database client

    Returns:
        True if upserted successfully, False otherwise
    """
    unique_id = order.customer_strategy_ref
    selection_type = get_selection_type(postgres_client, unique_id, order.side)
    matched_liability = calculate_liability(
        order.side, order.size_matched or 0, order.average_price_matched or 0
    )

    query = """
        INSERT INTO live_betting.pending_orders (
            selection_unique_id, bet_id, market_id, selection_id, side,
            selection_type, requested_price, requested_size,
            matched_size, matched_price, size_remaining, size_lapsed, size_cancelled,
            matched_liability, betfair_status, status, placed_at, matched_at, updated_at
        ) VALUES (
            :unique_id, :bet_id, :market_id, :selection_id, :side,
            :selection_type, :requested_price, :requested_size,
            :matched_size, :matched_price, :size_remaining, :size_lapsed, :size_cancelled,
            :matched_liability, :betfair_status, 'PENDING', :placed_at, :matched_at, NOW()
        )
        ON CONFLICT (selection_unique_id) DO UPDATE SET
            bet_id = EXCLUDED.bet_id,
            matched_size = EXCLUDED.matched_size,
            matched_price = EXCLUDED.matched_price,
            size_remaining = EXCLUDED.size_remaining,
            size_lapsed = EXCLUDED.size_lapsed,
            size_cancelled = EXCLUDED.size_cancelled,
            matched_liability = EXCLUDED.matched_liability,
            betfair_status = EXCLUDED.betfair_status,
            matched_at = EXCLUDED.matched_at,
            updated_at = NOW()
    """

    try:
        postgres_client.execute_query(
            query,
            {
                "unique_id": unique_id,
                "bet_id": order.bet_id,
                "market_id": order.market_id,
                "selection_id": order.selection_id,
                "side": order.side,
                "selection_type": selection_type,
                "requested_price": order.price,
                "requested_size": order.size,
                "matched_size": order.size_matched or 0,
                "matched_price": order.average_price_matched,
                "size_remaining": order.size_remaining,
                "size_lapsed": order.size_lapsed or 0,
                "size_cancelled": order.size_cancelled or 0,
                "matched_liability": matched_liability,
                "betfair_status": order.execution_status,
                "placed_at": order.placed_date,
                "matched_at": order.matched_date,
            },
        )
        # Don't log every upsert - logged in reconciliation summary
        return True
    except Exception as e:
        E(f"[{unique_id}] Failed to upsert to pending_orders: {e}")
        return False


def remove_pending_order(
    unique_id: str,
    postgres_client: PostgresClient,
) -> bool:
    """
    Remove a pending order when it becomes completed.

    Args:
        unique_id: Selection unique ID
        postgres_client: Database client

    Returns:
        True if a row was deleted, False otherwise
    """
    query = """
        DELETE FROM live_betting.pending_orders
        WHERE selection_unique_id = :unique_id
    """
    try:
        rows = postgres_client.execute_query(query, {"unique_id": unique_id})
        return rows > 0
    except Exception as e:
        W(f"[{unique_id}] Failed to remove from pending_orders: {e}")
        return False


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


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
    if not matched_size:
        return None
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
    With upsert pattern, there's only one row per selection.

    Args:
        postgres_client: Database client
        unique_id: Selection unique ID

    Returns:
        Total matched amount (0.0 if none or error)
    """
    try:
        result = postgres_client.fetch_data(
            f"""
            SELECT COALESCE(matched_size, 0) as total_matched
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
