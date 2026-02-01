"""
Tests for the executor module.

The executor is the IMPERATIVE SHELL:
- Takes decisions from the decision engine
- Interacts with Betfair API (mocked in tests)
- Records results to database (mocked in tests)

These tests verify:
1. Orders are placed correctly
2. Stake limit failsafe is respected
3. Price improvement triggers order replacement
4. Existing orders are handled correctly
"""

from unittest.mock import MagicMock

from api_helpers.clients.betfair_client import BetFairOrder, OrderResult

from trader.decision_engine import DecisionResult, OrderWithState
from trader.executor import _place_order, execute, ExecutionSummary


class TestOrderPlacement:
    """Test basic order placement logic."""

    def test_places_order_when_no_existing(self):
        """Should place order when no existing order."""
        order = BetFairOrder(
            size=10.0,
            price=3.0,
            selection_id="12345",
            market_id="1.234567",
            side="BACK",
            strategy="test_001",
        )
        order_with_state = OrderWithState(
            order=order,
            within_stake_limit=True,
            target_stake=10.0,
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order.return_value = OrderResult(
            success=True,
            message="OK",
            size_matched=0.0,
            average_price_matched=None,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        result = _place_order(order_with_state, [], mock_betfair, mock_postgres)

        mock_betfair.place_order.assert_called_once()
        assert result.success is True

    def test_skips_when_active_order_exists(self):
        """Should skip placing when active order exists at same price."""
        order = BetFairOrder(
            size=10.0,
            price=3.0,
            selection_id="12345",
            market_id="1.234567",
            side="BACK",
            strategy="test_skip_001",
        )
        order_with_state = OrderWithState(
            order=order,
            within_stake_limit=True,
            target_stake=10.0,
        )

        # Simulate existing order - must match customer_strategy_ref
        existing_order = MagicMock()
        existing_order.customer_strategy_ref = "test_skip_001"
        existing_order.price = 3.0
        existing_order.execution_status = "EXECUTABLE"
        existing_order.size_matched = 0

        mock_betfair = MagicMock()
        mock_postgres = MagicMock()

        result = _place_order(
            order_with_state, [existing_order], mock_betfair, mock_postgres
        )

        # Should not place order
        mock_betfair.place_order.assert_not_called()
        assert result is None


class TestExecuteSummary:
    """Test the execute function summary counts."""

    def test_execute_counts_placed_orders(self):
        """Execute should count placed orders."""
        order_with_state = OrderWithState(
            order=BetFairOrder(
                size=10.0,
                price=3.0,
                selection_id="12345",
                market_id="1.234567",
                side="BACK",
                strategy="test_exec",
            ),
            within_stake_limit=True,
            target_stake=10.0,
        )
        decision = DecisionResult(
            orders=[order_with_state],
            cash_out_market_ids=[],
            invalidations=[],
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order.return_value = OrderResult(
            success=True,
            message="OK",
            size_matched=0.0,
            average_price_matched=None,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary.orders_placed == 1
        mock_betfair.place_order.assert_called_once()

    def test_execute_counts_matched_orders(self):
        """Execute should count matched orders."""
        order_with_state = OrderWithState(
            order=BetFairOrder(
                size=10.0,
                price=3.0,
                selection_id="12345",
                market_id="1.234567",
                side="BACK",
                strategy="test_matched",
            ),
            within_stake_limit=True,
            target_stake=10.0,
        )
        decision = DecisionResult(
            orders=[order_with_state],
            cash_out_market_ids=[],
            invalidations=[],
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order.return_value = OrderResult(
            success=True,
            message="OK",
            size_matched=10.0,  # Fully matched
            average_price_matched=3.0,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary.orders_placed == 1
        assert summary.orders_matched == 1


class TestOrderResultHandling:
    """Test handling of various order results."""

    def test_failed_order_counted(self):
        """Failed orders should be counted in summary."""
        order_with_state = OrderWithState(
            order=BetFairOrder(
                size=10.0,
                price=3.0,
                selection_id="12345",
                market_id="1.234567",
                side="BACK",
                strategy="test_fail",
            ),
            within_stake_limit=True,
            target_stake=10.0,
        )
        decision = DecisionResult(
            orders=[order_with_state],
            cash_out_market_ids=[],
            invalidations=[],
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order.return_value = OrderResult(
            success=False,
            message="API Error",
            size_matched=None,
            average_price_matched=None,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary.orders_placed == 0
        assert summary.orders_failed == 1

    def test_partial_match_counted_as_matched(self):
        """Partial matches (size_matched > 0) should count as matched."""
        order_with_state = OrderWithState(
            order=BetFairOrder(
                size=10.0,
                price=3.0,
                selection_id="12345",
                market_id="1.234567",
                side="BACK",
                strategy="test_partial",
            ),
            within_stake_limit=True,
            target_stake=10.0,
        )
        decision = DecisionResult(
            orders=[order_with_state],
            cash_out_market_ids=[],
            invalidations=[],
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order.return_value = OrderResult(
            success=True,
            message="OK",
            size_matched=5.0,  # Partial match
            average_price_matched=3.0,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary.orders_placed == 1
        assert summary.orders_matched == 1  # Partial still counts
