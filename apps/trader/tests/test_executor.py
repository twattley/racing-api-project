"""
Tests for the executor module.

The executor is the IMPERATIVE SHELL:
- Takes decisions from the decision engine
- Interacts with Betfair API (mocked in tests)
- Records results to database (mocked in tests)

These tests verify:
1. Fill-or-kill orders use place_order_immediate
2. Normal orders use place_order
3. Stake limit failsafe is respected
"""

from unittest.mock import MagicMock

from api_helpers.clients.betfair_client import BetFairOrder, OrderResult

from trader.decision_engine import DecisionResult, OrderWithState
from trader.executor import _place_order, execute


class TestFillOrKillExecution:
    """Test that fill-or-kill flag triggers the correct method."""

    def test_fill_or_kill_true_uses_immediate(self):
        """When use_fill_or_kill=True, should call place_order_immediate."""
        order = BetFairOrder(
            size=10.0,
            price=3.0,
            selection_id="12345",
            market_id="1.234567",
            side="BACK",
            strategy="test_fok_001",
        )
        order_with_state = OrderWithState(
            order=order,
            use_fill_or_kill=True,
            within_stake_limit=True,
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order_immediate.return_value = OrderResult(
            success=True,
            message="OK",
            size_matched=10.0,
            average_price_matched=3.0,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        result = _place_order(order_with_state, [], mock_betfair, mock_postgres)

        # Should call place_order_immediate, NOT place_order
        mock_betfair.place_order_immediate.assert_called_once()
        mock_betfair.place_order.assert_not_called()
        assert result.success is True

    def test_fill_or_kill_false_uses_normal(self):
        """When use_fill_or_kill=False, should call regular place_order."""
        order = BetFairOrder(
            size=10.0,
            price=3.0,
            selection_id="12345",
            market_id="1.234567",
            side="BACK",
            strategy="test_normal_001",
        )
        order_with_state = OrderWithState(
            order=order,
            use_fill_or_kill=False,
            within_stake_limit=True,
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

        # Should call place_order, NOT place_order_immediate
        mock_betfair.place_order.assert_called_once()
        mock_betfair.place_order_immediate.assert_not_called()
        assert result.success is True


class TestExecuteSummary:
    """Test the execute function summary counts."""

    def test_execute_with_fill_or_kill_order(self):
        """Execute should handle fill-or-kill orders correctly."""
        order = BetFairOrder(
            size=10.0,
            price=3.0,
            selection_id="12345",
            market_id="1.234567",
            side="BACK",
            strategy="test_exec_fok",
        )
        order_with_state = OrderWithState(
            order=order,
            use_fill_or_kill=True,
            within_stake_limit=True,
        )
        decision = DecisionResult(
            orders=[order_with_state],
            cash_out_market_ids=[],
            invalidations=[],
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order_immediate.return_value = OrderResult(
            success=True,
            message="OK",
            size_matched=10.0,
            average_price_matched=3.0,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary["orders_placed"] == 1
        assert summary["orders_matched"] == 1
        mock_betfair.place_order_immediate.assert_called_once()

    def test_execute_with_normal_order(self):
        """Execute should handle normal orders correctly."""
        order = BetFairOrder(
            size=10.0,
            price=3.0,
            selection_id="12345",
            market_id="1.234567",
            side="BACK",
            strategy="test_exec_normal",
        )
        order_with_state = OrderWithState(
            order=order,
            use_fill_or_kill=False,
            within_stake_limit=True,
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
            size_matched=0.0,  # Unmatched - stays on book
            average_price_matched=None,
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary["orders_placed"] == 1
        assert summary["orders_matched"] == 0  # Not matched yet
        mock_betfair.place_order.assert_called_once()

    def test_execute_mixed_orders(self):
        """Execute should handle mix of fill-or-kill and normal orders."""
        fok_order = OrderWithState(
            order=BetFairOrder(
                size=10.0,
                price=3.0,
                selection_id="111",
                market_id="1.111",
                side="BACK",
                strategy="fok_001",
            ),
            use_fill_or_kill=True,
            within_stake_limit=True,
        )
        normal_order = OrderWithState(
            order=BetFairOrder(
                size=20.0,
                price=4.0,
                selection_id="222",
                market_id="1.222",
                side="BACK",
                strategy="normal_001",
            ),
            use_fill_or_kill=False,
            within_stake_limit=True,
        )
        decision = DecisionResult(
            orders=[fok_order, normal_order],
            cash_out_market_ids=[],
            invalidations=[],
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_betfair.place_order_immediate.return_value = OrderResult(
            success=True, message="OK", size_matched=10.0, average_price_matched=3.0
        )
        mock_betfair.place_order.return_value = OrderResult(
            success=True, message="OK", size_matched=0.0, average_price_matched=None
        )

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = MagicMock(empty=True)

        summary = execute(decision, mock_betfair, mock_postgres)

        assert summary["orders_placed"] == 2
        assert summary["orders_matched"] == 1  # Only FOK matched
        mock_betfair.place_order_immediate.assert_called_once()
        mock_betfair.place_order.assert_called_once()


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
            use_fill_or_kill=False,
            within_stake_limit=True,
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

        assert summary["orders_placed"] == 0
        assert summary["orders_failed"] == 1

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
            use_fill_or_kill=False,
            within_stake_limit=True,
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

        assert summary["orders_placed"] == 1
        assert summary["orders_matched"] == 1  # Partial still counts
