"""
Reconciliation - Sync Betfair state to database.

This module is responsible for ensuring our database reflects
the true state of orders on Betfair. Betfair is the source of truth.

Simplified approach:
1. Cancel ALL executable orders (they've had their chance to match)
2. Fetch all orders (now all EXECUTION_COMPLETE)
3. Aggregate orders by selection (customer_strategy_ref)
4. Upsert aggregated totals to bet_log

No pending_orders table needed - we always cancel unmatched portions
and work with what matched.
"""

from collections import defaultdict
from dataclasses import dataclass

from api_helpers.clients.betfair_client import BetFairClient, CurrentOrder
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import D, E, I, W


@dataclass
class AggregatedOrder:
    """Aggregated order data for a single selection (may come from multiple Betfair orders)."""

    unique_id: str
    market_id: str
    selection_id: int
    side: str
    total_matched: float
    total_requested: float
    weighted_avg_price: float
    size_cancelled: float
    bet_ids: list[str]  # All bet IDs for this selection
    latest_placed_at: str | None
    latest_matched_at: str | None


@dataclass
class ReconciliationResult:
    """Result of a reconciliation run."""

    orders_cancelled: int = 0
    selections_upserted: int = 0
    errors: int = 0
    current_orders: list[CurrentOrder] | None = None  # Orders after reconciliation

    def to_dict(self) -> dict:
        return {
            "orders_cancelled": self.orders_cancelled,
            "selections_upserted": self.selections_upserted,
            "errors": self.errors,
        }

    def has_activity(self) -> bool:
        """Return True if any activity occurred."""
        return self.orders_cancelled > 0 or self.selections_upserted > 0


# ============================================================================
# MAIN RECONCILIATION FUNCTION
# ============================================================================


def reconcile(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
    customer_refs: list[str],
) -> ReconciliationResult:
    """
    Reconcile Betfair orders with our database.

    Simplified process:
    1. Get all current orders from Betfair
    2. Cancel any EXECUTABLE orders (unmatched portions)
    3. Re-fetch orders (now all EXECUTION_COMPLETE)
    4. Aggregate by selection and upsert totals to bet_log

    Args:
        betfair_client: Betfair API client
        postgres_client: Database client
        customer_refs: List of customer strategy refs to filter by

    Returns:
        ReconciliationResult with counts of actions taken
    """
    result = ReconciliationResult()

    try:
        # Step 1: Get current orders
        current_orders: list[CurrentOrder] = betfair_client.get_current_orders(
            customer_strategy_refs=customer_refs
        )

        if not current_orders:
            return result

        # Step 2: Cancel any EXECUTABLE orders
        executable_orders: list[CurrentOrder] = [
            o
            for o in current_orders
            if o.execution_status == "EXECUTABLE" and is_trader_order(order=o)
        ]

        if executable_orders:
            # Get unique market IDs to cancel
            market_ids: list[str] = list(set(o.market_id for o in executable_orders))
            betfair_client.check_session()
            for market_id in market_ids:
                try:
                    betfair_client.trading_client.betting.cancel_orders(  # type: ignore
                        market_id=market_id
                    )
                    I(f"Cancelled unmatched orders in market {market_id}")
                except Exception as e:
                    W(f"Failed to cancel orders in market {market_id}: {e}")
            result.orders_cancelled = len(executable_orders)

        # Step 3: Re-fetch orders (now should all be EXECUTION_COMPLETE)
        current_orders: list[CurrentOrder] = betfair_client.get_current_orders(
            customer_strategy_refs=customer_refs
        )
        result.current_orders = current_orders

        if not current_orders:
            return result

        # Filter to completed trader orders only
        completed_orders: list[CurrentOrder] = [
            o
            for o in current_orders
            if o.execution_status == "EXECUTION_COMPLETE" and is_trader_order(o)
        ]

        if not completed_orders:
            return result

        # Step 4: Aggregate by selection
        aggregated: dict[str, AggregatedOrder] = _aggregate_orders_by_selection(
            completed_orders
        )

        # Step 5: Upsert aggregated totals to bet_log
        for unique_id, agg_order in aggregated.items():
            try:
                if upsert_aggregated_order(agg_order, postgres_client):
                    result.selections_upserted += 1
            except Exception as e:
                E(f"Error upserting aggregated order for {unique_id}: {e}")
                result.errors += 1

        if result.has_activity() or result.errors > 0:
            I(f"Reconciliation: {result.to_dict()}")

        return result

    except Exception as e:
        E(f"Error during reconciliation: {e}")
        result.errors += 1
        return result


# ============================================================================
# ORDER AGGREGATION
# ============================================================================


def _aggregate_orders_by_selection(
    orders: list[CurrentOrder],
) -> dict[str, AggregatedOrder]:
    """
    Aggregate multiple orders into one record per selection.

    Multiple Betfair orders can exist for the same selection (customer_strategy_ref).
    We need to sum matched amounts and calculate weighted average price.

    Args:
        orders: List of completed orders from Betfair

    Returns:
        Dict mapping unique_id to AggregatedOrder
    """
    # Group orders by customer_strategy_ref (our unique_id)
    grouped: dict[str, list[CurrentOrder]] = defaultdict(list)
    for order in orders:
        if order.customer_strategy_ref:
            grouped[order.customer_strategy_ref].append(order)

    aggregated: dict[str, AggregatedOrder] = {}

    for unique_id, order_group in grouped.items():
        total_matched = sum(o.size_matched for o in order_group)
        total_requested = sum(o.size for o in order_group)
        total_cancelled = sum(o.size_cancelled for o in order_group)

        # Calculate weighted average price
        if total_matched > 0:
            weighted_sum = sum(
                o.size_matched * o.average_price_matched for o in order_group
            )
            weighted_avg_price = weighted_sum / total_matched
        else:
            weighted_avg_price = 0.0

        # Use the first order for common fields
        first_order: CurrentOrder = order_group[0]

        # Find latest dates
        placed_dates = [o.placed_date for o in order_group if o.placed_date]
        matched_dates = [o.matched_date for o in order_group if o.matched_date]

        aggregated[unique_id] = AggregatedOrder(
            unique_id=unique_id,
            market_id=first_order.market_id,
            selection_id=first_order.selection_id,
            side=first_order.side,
            total_matched=total_matched,
            total_requested=total_requested,
            weighted_avg_price=round(weighted_avg_price, 2),
            size_cancelled=total_cancelled,
            bet_ids=[o.bet_id for o in order_group],
            latest_placed_at=max(placed_dates) if placed_dates else None,
            latest_matched_at=max(matched_dates) if matched_dates else None,
        )

        D(
            f"[{unique_id}] Aggregated {len(order_group)} orders: "
            f"matched={total_matched:.2f} @ {weighted_avg_price:.2f}"
        )

    return aggregated


# ============================================================================
# ORDER FILTERING
# ============================================================================


def is_trader_order(order: CurrentOrder) -> bool:
    """Check if order was placed by our trader (not manual UI)."""
    return (
        order.customer_strategy_ref is not None and order.customer_strategy_ref != "UI"
    )


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================


def upsert_aggregated_order(
    agg_order: AggregatedOrder,
    postgres_client: PostgresClient,
) -> bool:
    """
    Upsert aggregated order totals to bet_log.

    Uses ON CONFLICT DO UPDATE on selection_unique_id.
    One row per selection in bet_log, with summed totals.

    Args:
        agg_order: Aggregated order data
        postgres_client: Database client

    Returns:
        True if upserted successfully, False otherwise
    """
    unique_id = agg_order.unique_id
    selection_type = get_selection_type(postgres_client, unique_id, agg_order.side)
    matched_liability = calculate_liability(
        agg_order.side, agg_order.total_matched, agg_order.weighted_avg_price
    )

    # Store all bet IDs as comma-separated string
    bet_ids_str = ",".join(agg_order.bet_ids)

    query = """
        INSERT INTO live_betting.bet_log (
            selection_unique_id, bet_id, market_id, selection_id, side,
            selection_type, requested_price, requested_size,
            matched_size, matched_price, size_remaining, size_lapsed, size_cancelled,
            matched_liability, betfair_status, status, placed_at, matched_at
        ) VALUES (
            :unique_id, :bet_id, :market_id, :selection_id, :side,
            :selection_type, :matched_price, :requested_size,
            :matched_size, :matched_price, 0, 0, :size_cancelled,
            :matched_liability, 'EXECUTION_COMPLETE', 'MATCHED', :placed_at, :matched_at
        )
        ON CONFLICT (selection_unique_id) DO UPDATE SET
            bet_id = EXCLUDED.bet_id,
            matched_size = EXCLUDED.matched_size,
            matched_price = EXCLUDED.matched_price,
            requested_size = EXCLUDED.requested_size,
            size_remaining = 0,
            size_cancelled = EXCLUDED.size_cancelled,
            matched_liability = EXCLUDED.matched_liability,
            betfair_status = 'EXECUTION_COMPLETE',
            status = 'MATCHED',
            matched_at = EXCLUDED.matched_at
    """

    try:
        postgres_client.execute_query(
            query,
            {
                "unique_id": unique_id,
                "bet_id": bet_ids_str,
                "market_id": agg_order.market_id,
                "selection_id": agg_order.selection_id,
                "side": agg_order.side,
                "selection_type": selection_type,
                "requested_size": agg_order.total_requested,
                "matched_size": agg_order.total_matched,
                "matched_price": agg_order.weighted_avg_price,
                "size_cancelled": agg_order.size_cancelled,
                "matched_liability": matched_liability,
                "placed_at": agg_order.latest_placed_at,
                "matched_at": agg_order.latest_matched_at or agg_order.latest_placed_at,
            },
        )
        return True
    except Exception as e:
        E(f"[{unique_id}] Failed to upsert to bet_log: {e}")
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
