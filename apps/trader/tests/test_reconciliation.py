"""
Tests for the reconciliation module.

Reconciliation ensures our database (bet_log) reflects the true state
of orders on Betfair. This is critical for:
1. Accurate tracking of what's been matched
2. Preventing duplicate entries
3. Calculating remaining stake correctly

These tests verify the reconciliation logic works correctly with
different order states and edge cases.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from trader.reconciliation import (
    ReconciliationResult,
    calculate_liability,
    filter_completed_orders,
    has_matched_amount,
    is_bet_in_log,
    is_order_complete,
    is_trader_order,
    process_completed_order,
    reconcile,
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
    )


def make_executable_order(
    bet_id: str = "BET-001",
    unique_id: str = "unique-123",
    size_matched: float = 0.0,
    **kwargs,
) -> MockCurrentOrder:
    """Create an executable (pending) order for testing."""
    order = make_completed_order(
        bet_id=bet_id,
        unique_id=unique_id,
        size_matched=size_matched,
        **kwargs,
    )
    order.execution_status = "EXECUTABLE"
    return order


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


class TestHasMatchedAmount:
    """Test matched amount detection."""

    def test_order_with_matched_returns_true(self):
        order = make_completed_order(size_matched=10.0)
        assert has_matched_amount(order) is True

    def test_order_with_zero_matched_returns_false(self):
        order = make_completed_order(size_matched=0.0)
        assert has_matched_amount(order) is False

    def test_order_with_none_matched_returns_false(self):
        order = make_completed_order()
        order.size_matched = None
        assert has_matched_amount(order) is False


class TestFilterCompletedOrders:
    """Test the combined filter logic."""

    def test_filters_to_completed_trader_orders_with_matches(self):
        orders = [
            make_completed_order(bet_id="1", unique_id="sel-1", size_matched=10.0),
            make_executable_order(bet_id="2", unique_id="sel-2"),  # Not complete
            make_ui_order(bet_id="3"),  # UI order
            make_completed_order(
                bet_id="4", unique_id="sel-3", size_matched=0.0
            ),  # No match
            make_completed_order(bet_id="5", unique_id="sel-4", size_matched=5.0),
        ]

        filtered = filter_completed_orders(orders)

        assert len(filtered) == 2
        assert filtered[0].bet_id == "1"
        assert filtered[1].bet_id == "5"

    def test_empty_list_returns_empty(self):
        assert filter_completed_orders([]) == []

    def test_no_matching_orders_returns_empty(self):
        orders = [
            make_executable_order(),
            make_ui_order(),
        ]
        assert filter_completed_orders(orders) == []


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


# ============================================================================
# DATABASE OPERATION TESTS (with mocks)
# ============================================================================


class TestIsBetInLog:
    """Test duplicate detection in bet_log."""

    def test_returns_true_when_bet_exists(self):
        mock_client = MagicMock()
        mock_client.fetch_data.return_value = pd.DataFrame([{"exists": 1}])

        result = is_bet_in_log(
            mock_client,
            "unique-123",
            datetime(2026, 1, 22, 12, 0, 0),
        )

        assert result is True

    def test_returns_false_when_bet_not_exists(self):
        mock_client = MagicMock()
        mock_client.fetch_data.return_value = pd.DataFrame()

        result = is_bet_in_log(
            mock_client,
            "unique-123",
            datetime(2026, 1, 22, 12, 0, 0),
        )

        assert result is False

    def test_returns_true_on_error_conservative(self):
        """On error, assume exists to prevent duplicates."""
        mock_client = MagicMock()
        mock_client.fetch_data.side_effect = Exception("DB Error")

        result = is_bet_in_log(
            mock_client,
            "unique-123",
            datetime(2026, 1, 22, 12, 0, 0),
        )

        assert result is True


class TestProcessCompletedOrder:
    """Test individual order processing."""

    def test_skips_if_already_in_log(self):
        mock_client = MagicMock()
        # Simulate bet already exists
        mock_client.fetch_data.return_value = pd.DataFrame([{"exists": 1}])

        order = make_completed_order(unique_id="sel-123")
        result = process_completed_order(order, mock_client)

        assert result is False
        # store_data should NOT be called
        mock_client.store_data.assert_not_called()

    def test_stores_if_not_in_log(self):
        mock_client = MagicMock()
        # First call (is_bet_in_log) returns empty, second (get_selection_type) returns type
        mock_client.fetch_data.side_effect = [
            pd.DataFrame(),  # Not in log
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),  # Selection type
        ]

        order = make_completed_order(
            unique_id="sel-123",
            market_id="1.234",
            selection_id=999,
            side="BACK",
            size_matched=10.0,
            average_price_matched=3.5,
        )
        result = process_completed_order(order, mock_client)

        assert result is True
        mock_client.store_data.assert_called_once()

        # Verify the data stored
        call_args = mock_client.store_data.call_args
        stored_df = call_args.kwargs["data"]
        assert stored_df.iloc[0]["selection_unique_id"] == "sel-123"
        assert stored_df.iloc[0]["matched_size"] == 10.0
        assert stored_df.iloc[0]["matched_price"] == 3.5


# ============================================================================
# RECONCILIATION RESULT TESTS
# ============================================================================


class TestReconciliationResult:
    """Test the result dataclass."""

    def test_to_dict(self):
        result = ReconciliationResult(
            completed_moved_to_log=3,
            duplicates_skipped=1,
            errors=0,
        )
        d = result.to_dict()

        assert d["completed_moved_to_log"] == 3
        assert d["duplicates_skipped"] == 1
        assert d["errors"] == 0

    def test_has_changes_true_when_moved(self):
        result = ReconciliationResult(completed_moved_to_log=1)
        assert result.has_changes() is True

    def test_has_changes_false_when_nothing_moved(self):
        result = ReconciliationResult(duplicates_skipped=5)
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

        assert result.completed_moved_to_log == 0
        assert result.duplicates_skipped == 0
        assert result.errors == 0

    def test_processes_completed_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        # All orders are new (not in log)
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),  # is_bet_in_log for sel-1
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),  # get_selection_type
            pd.DataFrame(),  # is_bet_in_log for sel-2
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),  # get_selection_type
        ]

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_moved_to_log == 2
        assert mock_postgres.store_data.call_count == 2

    def test_skips_duplicates(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
        ]

        mock_postgres = MagicMock()
        # Order already in log
        mock_postgres.fetch_data.return_value = pd.DataFrame([{"exists": 1}])

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_moved_to_log == 0
        assert result.duplicates_skipped == 1
        mock_postgres.store_data.assert_not_called()

    def test_handles_betfair_api_error(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.side_effect = Exception("API Error")
        mock_postgres = MagicMock()

        result = reconcile(mock_betfair, mock_postgres)

        assert result.errors == 1
        assert result.completed_moved_to_log == 0

    def test_handles_individual_order_error_in_processing(self):
        """When an unexpected error occurs processing an order, count as error."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        # We need to make process_completed_order raise an exception
        # This happens when fetch_data returns something that causes pd.to_datetime to fail
        # But is_bet_in_log handles its own exceptions, so we need a different approach
        # Let's make the first order have an invalid placed_date that causes pd.to_datetime to fail
        order1 = make_completed_order(bet_id="1", unique_id="sel-1")
        order1.placed_date = "INVALID_DATE"  # This will cause pd.to_datetime to fail

        mock_betfair.get_current_orders.return_value = [
            order1,
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),  # is_bet_in_log for sel-2
            pd.DataFrame(
                [{"selection_type": "BACK_WIN"}]
            ),  # get_selection_type for sel-2
        ]

        result = reconcile(mock_betfair, mock_postgres)

        # First order errored (invalid date), second succeeded
        assert result.errors == 1
        assert result.completed_moved_to_log == 1

    def test_store_failure_counts_as_skip(self):
        """When store_completed_bet fails, it returns False -> counted as skip."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),  # is_bet_in_log
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),
        ]
        mock_postgres.store_data.side_effect = Exception("Store Error")

        result = reconcile(mock_betfair, mock_postgres)

        # Store failure is caught by store_completed_bet and returns False
        # This is treated as a skip (bet not stored but not an error at reconcile level)
        assert result.duplicates_skipped == 1
        assert result.completed_moved_to_log == 0

    def test_db_error_in_is_bet_in_log_counts_as_skip(self):
        """When is_bet_in_log errors, it conservatively returns True (skip)."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_completed_order(bet_id="1", unique_id="sel-1"),
        ]

        mock_postgres = MagicMock()
        # is_bet_in_log raises error -> returns True -> skipped
        mock_postgres.fetch_data.side_effect = Exception("DB Error")

        result = reconcile(mock_betfair, mock_postgres)

        # Treated as duplicate (conservative behavior)
        assert result.duplicates_skipped == 1
        assert result.errors == 0

    def test_ignores_executable_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_executable_order(bet_id="1", unique_id="sel-1"),  # Should be ignored
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),  # is_bet_in_log
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),
        ]

        result = reconcile(mock_betfair, mock_postgres)

        # Only the completed order should be processed
        assert result.completed_moved_to_log == 1
        assert mock_postgres.store_data.call_count == 1

    def test_ignores_ui_orders(self):
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            make_ui_order(bet_id="1"),  # Should be ignored
            make_completed_order(bet_id="2", unique_id="sel-2"),
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),
        ]

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_moved_to_log == 1


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
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),
        ]

        result = reconcile(mock_betfair, mock_postgres)

        assert result.completed_moved_to_log == 1

    def test_handles_lay_bet_liability_calculation(self):
        """LAY bets should have correct liability stored."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),  # is_bet_in_log
            pd.DataFrame([{"selection_type": "LAY_WIN"}]),
        ]

        order = make_completed_order(
            side="LAY",
            size_matched=10.0,
            average_price_matched=4.0,
        )
        process_completed_order(order, mock_postgres)

        # Verify liability = 10 * (4.0 - 1) = 30
        call_args = mock_postgres.store_data.call_args
        stored_df = call_args.kwargs["data"]
        assert stored_df.iloc[0]["matched_liability"] == 30.0

    def test_handles_missing_matched_date(self):
        """Orders without matched_date should use placed_date."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),
            pd.DataFrame([{"selection_type": "BACK_WIN"}]),
        ]

        order = make_completed_order()
        order.matched_date = None

        process_completed_order(order, mock_postgres)

        call_args = mock_postgres.store_data.call_args
        stored_df = call_args.kwargs["data"]
        # matched_at should fall back to placed_at
        assert stored_df.iloc[0]["matched_at"] is not None

    def test_handles_missing_selection_type(self):
        """If selection not found, should use side as fallback."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.side_effect = [
            pd.DataFrame(),  # is_bet_in_log
            pd.DataFrame(),  # get_selection_type - not found
        ]

        order = make_completed_order(side="BACK")
        process_completed_order(order, mock_postgres)

        call_args = mock_postgres.store_data.call_args
        stored_df = call_args.kwargs["data"]
        assert stored_df.iloc[0]["selection_type"] == "BACK"
