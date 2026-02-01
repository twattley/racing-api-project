"""
Tests for order_cleanup module.

Tests the garbage collection process that cancels stale orders
based on time to race and order age.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from trader.order_cleanup import (
    ORDER_STALE_MINUTES,
    RACE_IMMINENT_MINUTES,
    _cancel_order,
    _get_base_unique_id,
    _get_race_times,
    _is_order_stale,
    _is_trader_order,
    run,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def make_mock_order(
    bet_id: str = "123456789",
    market_id: str = "1.234567890",
    customer_strategy_ref: str = "abcdefghijk",
    execution_status: str = "EXECUTABLE",
    placed_date: datetime = None,
    size: float = 10.0,
    price: float = 3.0,
    side: str = "BACK",
    size_matched: float = 0.0,
    size_remaining: float = 10.0,
) -> MagicMock:
    """Create a mock CurrentOrder object."""
    order = MagicMock()
    order.bet_id = bet_id
    order.market_id = market_id
    order.customer_strategy_ref = customer_strategy_ref
    order.execution_status = execution_status
    order.placed_date = placed_date or datetime.now(ZoneInfo("UTC"))
    order.size = size
    order.price = price
    order.side = side
    order.size_matched = size_matched
    order.size_remaining = size_remaining
    return order


# ============================================================================
# _is_trader_order TESTS
# ============================================================================


class TestIsTraderOrder:
    """Test identification of trader vs UI orders."""

    def test_trader_order_with_valid_ref(self):
        """11-char hash is a trader order."""
        order = make_mock_order(customer_strategy_ref="abcdefghijk")
        assert _is_trader_order(order) is True

    def test_trader_order_with_longer_ref(self):
        """Longer ref (e.g. with retry suffix) is still a trader order."""
        order = make_mock_order(customer_strategy_ref="abcdefghijk_r1")
        assert _is_trader_order(order) is True

    def test_ui_order_returns_false(self):
        """UI_ prefixed orders are not trader orders."""
        order = make_mock_order(customer_strategy_ref="UI_manual_bet")
        assert _is_trader_order(order) is False

    def test_none_ref_returns_false(self):
        """No strategy ref means not a trader order."""
        order = make_mock_order(customer_strategy_ref=None)
        assert _is_trader_order(order) is False

    def test_empty_ref_returns_false(self):
        """Empty strategy ref means not a trader order."""
        order = make_mock_order(customer_strategy_ref="")
        assert _is_trader_order(order) is False

    def test_short_ref_returns_false(self):
        """Very short refs are not trader orders."""
        order = make_mock_order(customer_strategy_ref="abc")
        assert _is_trader_order(order) is False

    def test_exactly_11_chars(self):
        """Exactly 11 chars is valid."""
        order = make_mock_order(customer_strategy_ref="12345678901")
        assert _is_trader_order(order) is True


# ============================================================================
# _get_base_unique_id TESTS
# ============================================================================


class TestGetBaseUniqueId:
    """Test extraction of base unique_id from strategy ref."""

    def test_extracts_first_11_chars(self):
        """Returns first 11 characters."""
        assert _get_base_unique_id("abcdefghijk_r1") == "abcdefghijk"

    def test_exactly_11_chars(self):
        """Works with exactly 11 chars."""
        assert _get_base_unique_id("abcdefghijk") == "abcdefghijk"

    def test_none_returns_none(self):
        """None input returns None."""
        assert _get_base_unique_id(None) is None

    def test_empty_string(self):
        """Empty string returns None (falsy check)."""
        assert _get_base_unique_id("") is None

    def test_short_string(self):
        """Short string returns itself (slicing doesn't error)."""
        assert _get_base_unique_id("abc") == "abc"


# ============================================================================
# _is_order_stale TESTS
# ============================================================================


class TestIsOrderStale:
    """Test order staleness detection based on age."""

    def test_fresh_order_is_not_stale(self):
        """Order placed 1 minute ago is not stale."""
        now = datetime.now(ZoneInfo("UTC"))
        order = make_mock_order(placed_date=now - timedelta(minutes=1))

        assert _is_order_stale(order, now) is False

    def test_old_order_is_stale(self):
        """Order placed beyond ORDER_STALE_MINUTES is stale."""
        now = datetime.now(ZoneInfo("UTC"))
        order = make_mock_order(
            placed_date=now - timedelta(minutes=ORDER_STALE_MINUTES + 1)
        )

        assert _is_order_stale(order, now) is True

    def test_exactly_at_threshold_is_not_stale(self):
        """Order at exactly ORDER_STALE_MINUTES is not stale (must exceed)."""
        now = datetime.now(ZoneInfo("UTC"))
        order = make_mock_order(
            placed_date=now - timedelta(minutes=ORDER_STALE_MINUTES)
        )

        assert _is_order_stale(order, now) is False

    def test_just_over_threshold_is_stale(self):
        """Order just over threshold is stale."""
        now = datetime.now(ZoneInfo("UTC"))
        order = make_mock_order(
            placed_date=now - timedelta(minutes=ORDER_STALE_MINUTES + 0.1)
        )

        assert _is_order_stale(order, now) is True

    def test_none_placed_date_is_not_stale(self):
        """Order with no placed_date is not considered stale."""
        now = datetime.now(ZoneInfo("UTC"))
        order = make_mock_order(placed_date=None)

        assert _is_order_stale(order, now) is False

    def test_naive_datetime_converted(self):
        """Naive datetime placed_date is handled correctly."""
        now = datetime.now(ZoneInfo("UTC"))
        # Naive datetime (no tzinfo)
        naive_placed = datetime.now() - timedelta(minutes=ORDER_STALE_MINUTES + 1)
        order = make_mock_order(placed_date=naive_placed)

        assert _is_order_stale(order, now) is True

    def test_very_old_order(self):
        """Very old order (hours) is definitely stale."""
        now = datetime.now(ZoneInfo("UTC"))
        order = make_mock_order(placed_date=now - timedelta(hours=2))

        assert _is_order_stale(order, now) is True


# ============================================================================
# _get_race_times TESTS
# ============================================================================


class TestGetRaceTimes:
    """Test fetching race times from database."""

    def test_returns_dict_of_race_times(self):
        """Returns mapping of unique_id to race_time."""
        mock_postgres = MagicMock()
        race_time_1 = datetime.now() + timedelta(hours=1)
        race_time_2 = datetime.now() + timedelta(hours=2)

        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {
                "unique_id": ["sel_001", "sel_002"],
                "race_time": [race_time_1, race_time_2],
            }
        )

        result = _get_race_times(mock_postgres)

        assert result == {"sel_001": race_time_1, "sel_002": race_time_2}

    def test_returns_empty_dict_when_no_data(self):
        """Returns empty dict when no selections found."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame()

        result = _get_race_times(mock_postgres)

        assert result == {}

    def test_calls_correct_query(self):
        """Fetches today's selections."""
        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame()

        _get_race_times(mock_postgres)

        # Verify query fetches current date selections
        call_args = mock_postgres.fetch_data.call_args[0][0]
        assert "race_date = CURRENT_DATE" in call_args
        assert "live_betting.selections" in call_args


# ============================================================================
# _cancel_order TESTS
# ============================================================================


class TestCancelOrder:
    """Test order cancellation."""

    def test_successful_cancellation(self):
        """Returns True on successful cancel."""
        mock_betfair = MagicMock()
        order = make_mock_order(bet_id="123", market_id="1.234")

        result = _cancel_order(mock_betfair, order)

        assert result is True
        mock_betfair.trading_client.betting.cancel_orders.assert_called_once_with(
            market_id="1.234",
            instructions=[{"betId": "123"}],
        )

    def test_failed_cancellation_returns_false(self):
        """Returns False when cancel fails."""
        mock_betfair = MagicMock()
        mock_betfair.trading_client.betting.cancel_orders.side_effect = Exception(
            "API error"
        )
        order = make_mock_order()

        result = _cancel_order(mock_betfair, order)

        assert result is False

    def test_logs_failure(self):
        """Logs the failure reason."""
        mock_betfair = MagicMock()
        mock_betfair.trading_client.betting.cancel_orders.side_effect = Exception(
            "Rate limit exceeded"
        )
        order = make_mock_order(bet_id="999")

        with patch("trader.order_cleanup.I") as mock_log:
            _cancel_order(mock_betfair, order)
            mock_log.assert_called()
            assert "999" in str(mock_log.call_args)


# ============================================================================
# run() INTEGRATION TESTS
# ============================================================================


class TestRunNoOrders:
    """Test run() when there are no orders."""

    def test_returns_empty_summary_when_no_orders(self):
        """No orders means nothing to cancel."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_postgres = MagicMock()

        result = run(mock_betfair, mock_postgres)

        assert result == {"cancelled_stale": 0, "cancelled_imminent": 0}

    def test_does_not_query_database_when_no_orders(self):
        """Don't hit DB if no orders to process."""
        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = []
        mock_postgres = MagicMock()

        run(mock_betfair, mock_postgres)

        mock_postgres.fetch_data.assert_not_called()


class TestRunImminentRaceCancellation:
    """Test cancellation of orders when race is imminent."""

    def test_cancels_order_when_race_imminent(self):
        """Orders are cancelled when race is < RACE_IMMINENT_MINUTES away."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)  # Race in 2 minutes

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=1),  # Fresh order
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 1
        assert result["cancelled_stale"] == 0
        mock_betfair.trading_client.betting.cancel_orders.assert_called_once()

    def test_does_not_cancel_when_race_far_away(self):
        """Fresh orders are not cancelled when race is far away."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=60)  # Race in 1 hour

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=1),  # Fresh order
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 0
        assert result["cancelled_stale"] == 0
        mock_betfair.trading_client.betting.cancel_orders.assert_not_called()


class TestRunStaleCancellation:
    """Test cancellation of stale orders."""

    def test_cancels_stale_order_when_race_far(self):
        """Stale orders are cancelled even when race is far away."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=60)  # Race far away

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=ORDER_STALE_MINUTES + 1),  # Stale
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_stale"] == 1
        assert result["cancelled_imminent"] == 0

    def test_does_not_cancel_fresh_order(self):
        """Fresh orders are not cancelled when race is far away."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=60)  # Race far away

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=1),  # Fresh
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_stale"] == 0
        assert result["cancelled_imminent"] == 0


class TestRunFiltering:
    """Test filtering of orders (non-executable, UI orders, etc.)."""

    def test_skips_non_executable_orders(self):
        """Only EXECUTABLE orders are considered for cancellation."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)  # Race imminent

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            execution_status="EXECUTION_COMPLETE",  # Not executable
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 0
        mock_betfair.trading_client.betting.cancel_orders.assert_not_called()

    def test_skips_ui_orders(self):
        """UI orders are not cancelled by cleanup."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)  # Race imminent

        order = make_mock_order(
            customer_strategy_ref="UI_manual_bet",  # UI order
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 0
        mock_betfair.trading_client.betting.cancel_orders.assert_not_called()

    def test_skips_orders_without_strategy_ref(self):
        """Orders without strategy ref are skipped."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)  # Race imminent

        order = make_mock_order(customer_strategy_ref=None)

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 0

    def test_skips_orders_without_race_time(self):
        """Orders for unknown selections are skipped."""
        now = datetime.now(ZoneInfo("UTC"))

        order = make_mock_order(customer_strategy_ref="unknownuniq")

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["differentid"], "race_time": [now + timedelta(hours=1)]}
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 0
        assert result["cancelled_stale"] == 0


class TestRunMultipleOrders:
    """Test handling of multiple orders."""

    def test_processes_multiple_orders(self):
        """Multiple orders are each evaluated independently."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time_imminent = now + timedelta(minutes=2)
        race_time_far = now + timedelta(minutes=60)

        order_imminent = make_mock_order(
            bet_id="111",
            customer_strategy_ref="imminentsel",
            placed_date=now - timedelta(minutes=1),
        )
        order_stale = make_mock_order(
            bet_id="222",
            customer_strategy_ref="staleselect",
            placed_date=now - timedelta(minutes=ORDER_STALE_MINUTES + 1),
        )
        order_fresh = make_mock_order(
            bet_id="333",
            customer_strategy_ref="freshselect",
            placed_date=now - timedelta(minutes=1),
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [
            order_imminent,
            order_stale,
            order_fresh,
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {
                "unique_id": ["imminentsel", "staleselect", "freshselect"],
                "race_time": [race_time_imminent, race_time_far, race_time_far],
            }
        )

        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 1
        assert result["cancelled_stale"] == 1
        # Should have called cancel twice (imminent + stale)
        assert mock_betfair.trading_client.betting.cancel_orders.call_count == 2

    def test_imminent_takes_priority_over_stale(self):
        """Order is counted as imminent, not stale, when both apply."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)  # Imminent

        # Order is both stale AND race is imminent
        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=ORDER_STALE_MINUTES + 1),  # Stale
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        # Should be counted as imminent (checked first)
        assert result["cancelled_imminent"] == 1
        assert result["cancelled_stale"] == 0


class TestRunEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_cancel_failure_gracefully(self):
        """Failed cancellation doesn't stop processing other orders."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)  # Imminent

        order1 = make_mock_order(
            bet_id="111",
            customer_strategy_ref="selection01",
        )
        order2 = make_mock_order(
            bet_id="222",
            customer_strategy_ref="selection02",
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order1, order2]
        # First cancel fails, second succeeds
        mock_betfair.trading_client.betting.cancel_orders.side_effect = [
            Exception("API error"),
            None,
        ]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {
                "unique_id": ["selection01", "selection02"],
                "race_time": [race_time, race_time],
            }
        )

        result = run(mock_betfair, mock_postgres)

        # Only second cancellation succeeded
        assert result["cancelled_imminent"] == 1

    def test_handles_naive_race_time(self):
        """Naive datetime race_time is converted to UTC."""
        now = datetime.now(ZoneInfo("UTC"))
        # Naive datetime (no timezone)
        race_time_naive = datetime.now() + timedelta(minutes=2)

        order = make_mock_order(customer_strategy_ref="abcdefghijk")

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time_naive]}
        )

        # Should not raise an error
        result = run(mock_betfair, mock_postgres)

        assert result["cancelled_imminent"] == 1

    def test_boundary_just_over_imminent_threshold(self):
        """Test behavior just over the RACE_IMMINENT_MINUTES boundary."""
        now = datetime.now(ZoneInfo("UTC"))
        # Just over threshold - should NOT be cancelled as imminent
        race_time = now + timedelta(minutes=RACE_IMMINENT_MINUTES + 0.5)

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=1),
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        # Just over threshold - should NOT be cancelled as imminent
        assert result["cancelled_imminent"] == 0

    def test_race_in_past_is_imminent(self):
        """Race already started should definitely cancel orders."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now - timedelta(minutes=5)  # Race was 5 mins ago

        order = make_mock_order(customer_strategy_ref="abcdefghijk")

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        result = run(mock_betfair, mock_postgres)

        # Negative minutes_to_race is definitely < RACE_IMMINENT_MINUTES
        assert result["cancelled_imminent"] == 1


class TestRunLogging:
    """Test logging behavior."""

    def test_logs_summary_when_orders_cancelled(self):
        """Summary is logged when there are cancellations."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=2)

        order = make_mock_order(customer_strategy_ref="abcdefghijk")

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        with patch("trader.order_cleanup.I") as mock_info:
            run(mock_betfair, mock_postgres)
            # Should log the cancellation and the summary
            assert mock_info.call_count >= 2

    def test_no_summary_log_when_nothing_cancelled(self):
        """No summary logged when no cancellations."""
        now = datetime.now(ZoneInfo("UTC"))
        race_time = now + timedelta(minutes=60)

        order = make_mock_order(
            customer_strategy_ref="abcdefghijk",
            placed_date=now - timedelta(minutes=1),
        )

        mock_betfair = MagicMock()
        mock_betfair.get_current_orders.return_value = [order]

        mock_postgres = MagicMock()
        mock_postgres.fetch_data.return_value = pd.DataFrame(
            {"unique_id": ["abcdefghijk"], "race_time": [race_time]}
        )

        with patch("trader.order_cleanup.I") as mock_info:
            run(mock_betfair, mock_postgres)
            # Should not log summary
            for call in mock_info.call_args_list:
                assert "Order cleanup:" not in str(call)


# ============================================================================
# CONSTANTS TESTS
# ============================================================================


class TestConstants:
    """Test that constants are set correctly."""

    def test_order_stale_minutes(self):
        """ORDER_STALE_MINUTES should be 5."""
        assert ORDER_STALE_MINUTES == 5

    def test_race_imminent_minutes(self):
        """RACE_IMMINENT_MINUTES should be 5."""
        assert RACE_IMMINENT_MINUTES == 5
