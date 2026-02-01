"""
Tests for the reconciliation module.

Reconciliation ensures our database reflects the true state
of orders on Betfair using a simplified approach:
1. Cancel ALL executable orders (they've had their chance to match)
2. Aggregate completed orders by selection (customer_strategy_ref)
3. Upsert aggregated totals to bet_log (one row per selection)

Betfair is the source of truth.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pandas as pd
from trader.reconciliation import (
    AggregatedOrder,
    ReconciliationResult,
    _aggregate_orders_by_selection,
    calculate_liability,
    get_matched_total_from_log,
    get_selection_type,
    is_trader_order,
    reconcile,
    upsert_aggregated_order,
)

# ============================================================================
# FIXTURES - Test data builders
# ============================================================================


@dataclass
class MockCurrentOrder:
    """Mock of CurrentOrder from betfair_client."""

    bet_id: str
    market_id: str
    selection_id: int
    side: str
    execution_status: str
    customer_strategy_ref: Optional[str]
    size_matched: float
    average_price_matched: float
    placed_date: datetime
    matched_date: Optional[datetime] = None
    price: float = 3.0
    size: float = 10.0
    size_remaining: float = 0.0
    size_lapsed: float = 0.0
    size_cancelled: float = 0.0


def make_completed_order(
    bet_id: str = "BET-001",
    market_id: str = "1.234567890",
    selection_id: int = 12345,
    side: str = "BACK",
    unique_id: str = "unique-123",
    size_matched: float = 10.0,
    average_price_matched: float = 3.5,
    size: float = 10.0,
    size_cancelled: float = 0.0,
    placed_date: Optional[datetime] = None,
    matched_date: Optional[datetime] = None,
) -> MockCurrentOrder:
    """Create a completed order for testing."""
    now = datetime.now(ZoneInfo("UTC"))
    return MockCurrentOrder(
        bet_id=bet_id,
        market_id=market_id,
        selection_id=selection_id,
        side=side,
        execution_status="EXECUTION_COMPLETE",
        customer_strategy_ref=unique_id,
        size_matched=size_matched,
        average_price_matched=average_price_matched,
        placed_date=placed_date or now,
        matched_date=matched_date or now,
        price=average_price_matched,
        size=size,
        size_remaining=0.0,
        size_lapsed=0.0,
        size_cancelled=size_cancelled,
    )


def make_executable_order(
    bet_id: str = "BET-001",
    unique_id: str = "unique-123",
    market_id: str = "1.234567890",
    size_matched: float = 0.0,
    size_remaining: float = 10.0,
    **kwargs,
) -> MockCurrentOrder:
    """Create an executable (pending) order for testing."""
    now = datetime.now(ZoneInfo("UTC"))
    return MockCurrentOrder(
        bet_id=bet_id,
        market_id=market_id,
        selection_id=kwargs.get("selection_id", 12345),
        side=kwargs.get("side", "BACK"),
        execution_status="EXECUTABLE",
        customer_strategy_ref=unique_id,
        size_matched=size_matched,
        average_price_matched=kwargs.get("average_price_matched", 0.0),
        placed_date=kwargs.get("placed_date", now),
        matched_date=kwargs.get("matched_date"),
        price=kwargs.get("price", 3.0),
        size=kwargs.get("size", 10.0),
        size_remaining=size_remaining,
        size_lapsed=0.0,
        size_cancelled=0.0,
    )


def make_ui_order(**kwargs) -> MockCurrentOrder:
    """Create an order placed via UI (not trader)."""
    order = make_completed_order(**kwargs)
    order.customer_strategy_ref = "UI"
    return order


def make_no_ref_order(**kwargs) -> MockCurrentOrder:
    """Create an order with no strategy ref."""
    order = make_completed_order(**kwargs)
    order.customer_strategy_ref = None
    return order


# ============================================================================
# FILTER TESTS - Order filtering logic
# ============================================================================


class TestIsTraderOrder:
    """Test trader vs UI order detection."""

    def test_trader_order_returns_true(self):
        order = make_completed_order(unique_id="selection-123")
        assert is_trader_order(order) is True

    def test_ui_order_returns_false(self):
        order = make_ui_order()
        assert is_trader_order(order) is False

    def test_no_ref_order_returns_false(self):
        order = make_no_ref_order()
        assert is_trader_order(order) is False


# ============================================================================
# LIABILITY CALCULATION TESTS
# ============================================================================


class TestCalculateLiability:
    """Test liability calculation for different bet types."""

    def test_back_bet_liability_equals_stake(self):
        assert calculate_liability("BACK", 10.0, 3.5) == 10.0

    def test_lay_bet_liability_calculated(self):
        # Liability = stake * (odds - 1) = 10 * (3.5 - 1) = 25
        assert calculate_liability("LAY", 10.0, 3.5) == 25.0

    def test_lay_bet_at_evens_liability(self):
        # Liability = stake * (2.0 - 1) = 10 * 1 = 10
        assert calculate_liability("LAY", 10.0, 2.0) == 10.0

    def test_lay_bet_with_invalid_price_returns_none(self):
        assert calculate_liability("LAY", 10.0, 1.0) is None
        assert calculate_liability("LAY", 10.0, 0.0) is None

    def test_unknown_side_returns_none(self):
        assert calculate_liability("UNKNOWN", 10.0, 3.5) is None

    def test_zero_matched_returns_none(self):
        assert calculate_liability("BACK", 0.0, 3.5) is None


# ============================================================================
# AGGREGATION TESTS
# ============================================================================


class TestAggregateOrdersBySelection:
    """Test aggregation of multiple orders per selection."""

    def test_single_order_aggregates_correctly(self):
        orders = [
            make_completed_order(
                bet_id="BET-1",
                unique_id="sel-123",
                size_matched=10.0,
                average_price_matched=3.5,
            )
        ]

        result = _aggregate_orders_by_selection(orders)

        assert "sel-123" in result
        agg = result["sel-123"]
        assert agg.total_matched == 10.0
        assert agg.weighted_avg_price == 3.5
        assert agg.bet_ids == ["BET-1"]

    def test_multiple_orders_same_selection_aggregated(self):
        """Two orders for same selection should be summed."""
        orders = [
            make_completed_order(
                bet_id="BET-1",
                unique_id="sel-123",
                size_matched=5.0,
                average_price_matched=3.0,
                size=5.0,
            ),
            make_completed_order(
                bet_id="BET-2",
                unique_id="sel-123",
                size_matched=5.0,
                average_price_matched=4.0,
                size=5.0,
            ),
        ]

        result = _aggregate_orders_by_selection(orders)

        assert "sel-123" in result
        agg = result["sel-123"]
        assert agg.total_matched == 10.0
        assert agg.total_requested == 10.0
        # Weighted avg: (5*3 + 5*4) / 10 = 35/10 = 3.5
        assert agg.weighted_avg_price == 3.5
        assert set(agg.bet_ids) == {"BET-1", "BET-2"}

    def test_different_selections_kept_separate(self):
        """Orders for different selections should not be aggregated."""
        orders = [
            make_completed_order(
                bet_id="BET-1", unique_id="sel-111", size_matched=10.0
            ),
            make_completed_order(
                bet_id="BET-2", unique_id="sel-222", size_matched=20.0
            ),
        ]

        result = _aggregate_orders_by_selection(orders)

        assert len(result) == 2
        assert result["sel-111"].total_matched == 10.0
        assert result["sel-222"].total_matched == 20.0

    def test_zero_matched_orders_included(self):
        """Orders with no match should still be aggregated (for cancelled tracking)."""
        orders = [
            make_completed_order(
                bet_id="BET-1",
                unique_id="sel-123",
                size_matched=0.0,
                average_price_matched=0.0,
                size_cancelled=10.0,
            )
        ]

        result = _aggregate_orders_by_selection(orders)

        assert "sel-123" in result
        agg = result["sel-123"]
        assert agg.total_matched == 0.0
        assert agg.size_cancelled == 10.0

    def test_orders_without_strategy_ref_ignored(self):
        """Orders with no customer_strategy_ref should be skipped."""
        order = make_completed_order(bet_id="BET-1", unique_id="sel-123")
        order.customer_strategy_ref = None

        result = _aggregate_orders_by_selection([order])

        assert len(result) == 0


# ============================================================================
# UPSERT TESTS
# ============================================================================


class TestUpsertAggregatedOrder:
    """Test upserting aggregated orders to bet_log."""

    def test_upserts_aggregated_order(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        agg_order = AggregatedOrder(
            unique_id="sel-123",
            market_id="1.234567890",
            selection_id=12345,
            side="BACK",
            total_matched=10.0,
            total_requested=10.0,
            weighted_avg_price=3.5,
            size_cancelled=0.0,
            bet_ids=["BET-1", "BET-2"],
            latest_placed_at="2026-01-01T12:00:00Z",
            latest_matched_at="2026-01-01T12:00:01Z",
        )

        result = upsert_aggregated_order(agg_order, mock_postgres)

        assert result is True
        mock_postgres.execute_query.assert_called_once()
        call_args = mock_postgres.execute_query.call_args
        assert "ON CONFLICT" in call_args[0][0]
        assert "DO UPDATE" in call_args[0][0]
        # Check bet_ids are comma-joined
        params = call_args[0][1]
        assert params["bet_id"] == "BET-1,BET-2"

    def test_returns_false_on_error(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        mock_postgres.execute_query.side_effect = Exception("DB Error")

        agg_order = AggregatedOrder(
            unique_id="sel-123",
            market_id="1.234567890",
            selection_id=12345,
            side="BACK",
            total_matched=10.0,
            total_requested=10.0,
            weighted_avg_price=3.5,
            size_cancelled=0.0,
            bet_ids=["BET-1"],
            latest_placed_at=None,
            latest_matched_at=None,
        )

        result = upsert_aggregated_order(agg_order, mock_postgres)

        assert result is False


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


class TestGetSelectionType:
    """Test getting selection type from database."""

    def test_returns_selection_type_when_found(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = get_selection_type(mock_postgres, "sel-123", "LAY")

        assert result == "BACK"

    def test_returns_fallback_when_not_found(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame()

        result = get_selection_type(mock_postgres, "sel-123", "LAY")

        assert result == "LAY"

    def test_returns_fallback_on_error(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = Exception("DB Error")

        result = get_selection_type(mock_postgres, "sel-123", "BACK")

        assert result == "BACK"


class TestGetMatchedTotalFromLog:
    """Test getting matched total from bet_log."""

    def test_returns_matched_amount(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame([{"total_matched": 25.0}])

        result = get_matched_total_from_log(mock_postgres, "sel-123")

        assert result == 25.0

    def test_returns_zero_when_not_found(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame()

        result = get_matched_total_from_log(mock_postgres, "sel-123")

        assert result == 0.0

    def test_returns_zero_on_error(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = Exception("DB Error")

        result = get_matched_total_from_log(mock_postgres, "sel-123")

        assert result == 0.0


# ============================================================================
# RECONCILIATION RESULT TESTS
# ============================================================================


class TestReconciliationResult:
    """Test the result dataclass."""

    def test_to_dict(self):
        result = ReconciliationResult(
            orders_cancelled=3,
            selections_upserted=2,
            errors=1,
        )
        d = result.to_dict()

        assert d["orders_cancelled"] == 3
        assert d["selections_upserted"] == 2
        assert d["errors"] == 1

    def test_has_activity_true_when_orders_cancelled(self):
        result = ReconciliationResult(orders_cancelled=1)
        assert result.has_activity() is True

    def test_has_activity_true_when_selections_upserted(self):
        result = ReconciliationResult(selections_upserted=1)
        assert result.has_activity() is True

    def test_has_activity_false_when_nothing_happened(self):
        result = ReconciliationResult()
        assert result.has_activity() is False

    def test_has_activity_false_with_only_errors(self):
        """Errors alone don't count as 'activity'."""
        result = ReconciliationResult(errors=1)
        assert result.has_activity() is False


# ============================================================================
# FULL RECONCILIATION TESTS
# ============================================================================


class TestReconcile:
    """Test the main reconcile function."""

    def test_returns_empty_result_when_no_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_postgres = MagicMock()

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["ref-1"])

        assert result.orders_cancelled == 0
        assert result.selections_upserted == 0
        assert result.errors == 0

    def test_cancels_executable_orders(self):
        """Executable orders should be cancelled."""
        mock_betfair = MagicMock()
        # First call returns executable orders, second call returns completed
        mock_betfair.get_current_orders.side_effect = [
            [make_executable_order(bet_id="1", unique_id="sel-1", market_id="1.111")],
            [make_completed_order(bet_id="1", unique_id="sel-1", size_matched=5.0)],
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["sel-1"])

        assert result.orders_cancelled == 1
        mock_betfair.trading_client.betting.cancel_orders.assert_called_once()

    def test_aggregates_completed_orders(self):
        """Completed orders should be aggregated and upserted."""
        mock_betfair = MagicMock()
        # No executable orders, just completed
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1", size_matched=5.0),
            make_completed_order(bet_id="2", unique_id="sel-1", size_matched=5.0),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["sel-1"])

        # Two orders aggregated into one selection
        assert result.selections_upserted == 1
        mock_postgres.execute_query.assert_called_once()

    def test_returns_current_orders(self):
        """Result should include current_orders for reuse."""
        mock_betfair = MagicMock()
        orders = [make_completed_order(bet_id="1", unique_id="sel-1")]
        mock_betfair.get_current_orders.return_value = orders

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["sel-1"])

        assert result.current_orders == orders

    def test_handles_betfair_api_error(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.side_effect = Exception("API Error")
        mock_postgres = MagicMock()

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["ref-1"])

        assert result.errors == 1
        assert result.selections_upserted == 0

    def test_ignores_ui_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_ui_order(bet_id="1"),  # Should be ignored
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["sel-2"])

        assert result.selections_upserted == 1


# ============================================================================
# EDGE CASES
# ============================================================================


class TestReconciliationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_handles_very_small_matched_amount(self):
        """Amounts like 0.01 should still be processed."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(size_matched=0.01),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = reconcile(mock_betfair, mock_postgres, customer_refs=["unique-123"])

        assert result.selections_upserted == 1

    def test_lay_bet_liability_calculation(self):
        """LAY bets should have correct liability calculated."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "LAY"}]
        )

        agg_order = AggregatedOrder(
            unique_id="sel-123",
            market_id="1.234567890",
            selection_id=12345,
            side="LAY",
            total_matched=10.0,
            total_requested=10.0,
            weighted_avg_price=4.0,
            size_cancelled=0.0,
            bet_ids=["BET-1"],
            latest_placed_at=None,
            latest_matched_at=None,
        )

        upsert_aggregated_order(agg_order, mock_postgres)

        # Verify liability = 10 * (4.0 - 1) = 30
        call_args = mock_postgres.execute_query.call_args
        params = call_args[0][1]
        assert params["matched_liability"] == 30.0

    def test_weighted_average_with_uneven_amounts(self):
        """Test weighted average calculation with different sized orders."""
        orders = [
            make_completed_order(
                bet_id="BET-1",
                unique_id="sel-123",
                size_matched=2.0,  # 20% of total
                average_price_matched=2.0,
                size=2.0,
            ),
            make_completed_order(
                bet_id="BET-2",
                unique_id="sel-123",
                size_matched=8.0,  # 80% of total
                average_price_matched=5.0,
                size=8.0,
            ),
        ]

        result = _aggregate_orders_by_selection(orders)

        agg = result["sel-123"]
        assert agg.total_matched == 10.0
        # Weighted avg: (2*2 + 8*5) / 10 = (4 + 40) / 10 = 4.4
        assert agg.weighted_avg_price == 4.4
