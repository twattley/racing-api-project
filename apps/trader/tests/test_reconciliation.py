"""
Tests for the reconciliation module.

Reconciliation ensures our database reflects the true state
of orders on Betfair using an upsert pattern:
- bet_log: one row per selection (completed orders)
- pending_orders: one row per selection (executable orders)

These tests verify the reconciliation logic works correctly with
different order states and edge cases.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pandas as pd

from trader.reconciliation import (
    ReconciliationResult,
    calculate_liability,
    get_matched_total_from_log,
    get_selection_type,
    is_order_complete,
    is_trader_order,
    reconcile,
    remove_pending_order,
    upsert_completed_order,
    upsert_pending_order,
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
        size=size_matched,
        size_remaining=0.0,
        size_lapsed=0.0,
        size_cancelled=0.0,
    )


def make_executable_order(
    bet_id: str = "BET-001",
    unique_id: str = "unique-123",
    size_matched: float = 0.0,
    size_remaining: float = 10.0,
    **kwargs,
) -> MockCurrentOrder:
    """Create an executable (pending) order for testing."""
    now = datetime.now(ZoneInfo("UTC"))
    return MockCurrentOrder(
        bet_id=bet_id,
        market_id=kwargs.get("market_id", "1.234567890"),
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


class TestIsOrderComplete:
    """Test order completion detection."""

    def test_complete_order_returns_true(self):
        order = make_completed_order()
        assert is_order_complete(order) is True

    def test_executable_order_returns_false(self):
        order = make_executable_order()
        assert is_order_complete(order) is False


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
# UPSERT TESTS
# ============================================================================


class TestUpsertCompletedOrder:
    """Test upserting completed orders to bet_log."""

    def test_upserts_completed_order(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        order = make_completed_order(
            unique_id="sel-123",
            side="BACK",
            size_matched=10.0,
            average_price_matched=3.5,
        )

        result = upsert_completed_order(order, mock_postgres)

        assert result is True
        mock_postgres.execute_query.assert_called_once()
        # Check query contains upsert pattern
        call_args = mock_postgres.execute_query.call_args
        assert "ON CONFLICT" in call_args[0][0]
        assert "DO UPDATE" in call_args[0][0]

    def test_returns_false_on_error(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        mock_postgres.execute_query.side_effect = Exception("DB Error")

        order = make_completed_order(unique_id="sel-123")
        result = upsert_completed_order(order, mock_postgres)

        assert result is False


class TestUpsertPendingOrder:
    """Test upserting executable orders to pending_orders."""

    def test_upserts_pending_order(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        order = make_executable_order(
            unique_id="sel-123",
            size_remaining=10.0,
        )

        result = upsert_pending_order(order, mock_postgres)

        assert result is True
        mock_postgres.execute_query.assert_called_once()
        call_args = mock_postgres.execute_query.call_args
        assert "ON CONFLICT" in call_args[0][0]
        assert "pending_orders" in call_args[0][0]

    def test_returns_false_on_error(self):
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        mock_postgres.execute_query.side_effect = Exception("DB Error")

        order = make_executable_order(unique_id="sel-123")
        result = upsert_pending_order(order, mock_postgres)

        assert result is False


class TestRemovePendingOrder:
    """Test removing pending orders when completed."""

    def test_removes_pending_order(self):
        mock_postgres = MagicMock()
        mock_postgres.execute_query.return_value = 1  # 1 row deleted

        result = remove_pending_order("sel-123", mock_postgres)

        assert result is True
        call_args = mock_postgres.execute_query.call_args
        assert "DELETE FROM" in call_args[0][0]

    def test_returns_false_when_no_row_deleted(self):
        mock_postgres = MagicMock()
        mock_postgres.execute_query.return_value = 0  # No rows deleted

        result = remove_pending_order("sel-123", mock_postgres)

        assert result is False

    def test_returns_false_on_error(self):
        mock_postgres = MagicMock()
        mock_postgres.execute_query.side_effect = Exception("DB Error")

        result = remove_pending_order("sel-123", mock_postgres)

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
            completed_upserted=3,
            pending_upserted=2,
            pending_cleaned=1,
            errors=0,
        )
        d = result.to_dict()

        assert d["completed_upserted"] == 3
        assert d["pending_upserted"] == 2
        assert d["pending_cleaned"] == 1
        assert d["errors"] == 0

    def test_has_changes_true_when_completed_upserted(self):
        result = ReconciliationResult(completed_upserted=1)
        assert result.has_changes() is True

    def test_has_changes_true_when_pending_upserted(self):
        result = ReconciliationResult(pending_upserted=1)
        assert result.has_changes() is True

    def test_has_changes_true_when_pending_cleaned(self):
        result = ReconciliationResult(pending_cleaned=1)
        assert result.has_changes() is True

    def test_has_changes_false_when_nothing_changed(self):
        result = ReconciliationResult(errors=5)
        assert result.has_changes() is False


# ============================================================================
# FULL RECONCILIATION TESTS
# ============================================================================


class TestReconcile:
    """Test the main reconcile function."""

    def test_returns_empty_result_when_no_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_postgres = MagicMock()

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_upserted == 0
        assert result.pending_upserted == 0
        assert result.pending_cleaned == 0
        assert result.errors == 0

    def test_processes_completed_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        mock_postgres.execute_query.return_value = 1  # 1 row affected

        result = reconcile(mock_betfair, mock_postgres)

        # 2 completed orders upserted, 2 pending cleanups attempted
        assert result.completed_upserted == 2
        assert result.pending_cleaned == 2

    def test_processes_executable_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_executable_order(bet_id="1", unique_id="sel-1"),
            make_executable_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        result = reconcile(mock_betfair, mock_postgres)

        assert result.pending_upserted == 2
        assert result.completed_upserted == 0

    def test_handles_mixed_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
            make_executable_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        mock_postgres.execute_query.return_value = 1

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_upserted == 1
        assert result.pending_upserted == 1
        assert result.pending_cleaned == 1

    def test_handles_betfair_api_error(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.side_effect = Exception("API Error")
        mock_postgres = MagicMock()

        result = reconcile(mock_betfair, mock_postgres)

        assert result.errors == 1
        assert result.completed_upserted == 0

    def test_handles_individual_order_error(self):
        """When an upsert fails, the order is not counted but doesn't block others."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        # First upsert fails (exception caught inside upsert_completed_order),
        # cleanup returns 0, second upsert succeeds, cleanup succeeds
        mock_postgres.execute_query.side_effect = [
            Exception("DB Error"),  # First upsert fails (returns False)
            0,  # First cleanup finds nothing
            None,  # Second upsert succeeds
            1,  # Second cleanup succeeds
        ]

        result = reconcile(mock_betfair, mock_postgres)

        # First order failed silently, second succeeded
        assert result.completed_upserted == 1
        assert result.pending_cleaned == 1
        # No errors counted because upsert catches its own exceptions
        assert result.errors == 0

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
        mock_postgres.execute_query.return_value = 1

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_upserted == 1

    def test_ignores_orders_without_strategy_ref(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_no_ref_order(bet_id="1"),  # Should be ignored
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )
        mock_postgres.execute_query.return_value = 1

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_upserted == 1


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
        mock_postgres.execute_query.return_value = 1

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_upserted == 1

    def test_lay_bet_liability_calculation_in_upsert(self):
        """LAY bets should have correct liability calculated."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "LAY"}]
        )

        order = make_completed_order(
            side="LAY",
            size_matched=10.0,
            average_price_matched=4.0,
        )
        upsert_completed_order(order, mock_postgres)

        # Verify liability = 10 * (4.0 - 1) = 30
        call_args = mock_postgres.execute_query.call_args
        params = call_args[0][1]
        assert params["matched_liability"] == 30.0

    def test_handles_order_with_no_matched_amount(self):
        """Executable orders with no match should still be tracked."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            [{"selection_type": "BACK"}]
        )

        order = make_executable_order(
            size_matched=0.0,
            size_remaining=10.0,
        )
        result = upsert_pending_order(order, mock_postgres)

        assert result is True
        call_args = mock_postgres.execute_query.call_args
        params = call_args[0][1]
        assert params["matched_size"] == 0.0
        assert params["size_remaining"] == 10.0
