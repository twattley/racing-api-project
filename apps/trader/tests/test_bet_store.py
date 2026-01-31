"""Tests for bet_store module - order management helpers."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from trader.bet_store import (
    calculate_remaining_stake,
    find_order_for_selection,
    is_order_stale,
    ORDER_TIMEOUT_MINUTES,
)


class TestFindOrderForSelection:
    """Tests for finding orders by selection."""

    def test_finds_matching_order(self):
        order = MagicMock()
        order.customer_strategy_ref = "selection_001"

        result = find_order_for_selection([order], "selection_001")
        assert result == order

    def test_returns_none_when_not_found(self):
        order = MagicMock()
        order.customer_strategy_ref = "selection_001"

        result = find_order_for_selection([order], "selection_999")
        assert result is None

    def test_returns_none_for_empty_list(self):
        result = find_order_for_selection([], "selection_001")
        assert result is None


class TestIsOrderStaleWithTimeout:
    """Tests for is_order_stale with timeout."""

    def test_not_stale_within_timeout(self):
        order = MagicMock()
        order.placed_date = datetime.now(ZoneInfo("UTC")) - timedelta(minutes=2)

        # Only 2 minutes old, timeout is 5 - not stale
        assert is_order_stale(order) is False

    def test_stale_after_timeout(self):
        order = MagicMock()
        order.placed_date = datetime.now(ZoneInfo("UTC")) - timedelta(minutes=10)

        # 10 minutes old, timeout is 5 - stale
        assert is_order_stale(order) is True

    def test_custom_timeout(self):
        order = MagicMock()
        order.placed_date = datetime.now(ZoneInfo("UTC")) - timedelta(minutes=15)

        # 15 minutes old, custom timeout of 20 - not stale
        assert is_order_stale(order, timeout_minutes=20) is False

    def test_no_placed_date_not_stale(self):
        order = MagicMock()
        order.placed_date = None

        assert is_order_stale(order) is False


class TestCalculateRemainingStake:
    """Tests for remaining stake calculation."""

    def test_full_stake_needed_when_nothing_matched(self):
        result = calculate_remaining_stake(
            target_stake=50.0,
            current_order=None,
            matched_in_log=0.0,
        )
        assert result == 50.0

    def test_accounts_for_matched_in_log(self):
        result = calculate_remaining_stake(
            target_stake=50.0,
            current_order=None,
            matched_in_log=20.0,
        )
        assert result == 30.0

    def test_accounts_for_current_order_matched(self):
        order = MagicMock()
        order.size_matched = 15.0
        order.size_remaining = 5.0

        result = calculate_remaining_stake(
            target_stake=50.0,
            current_order=order,
            matched_in_log=10.0,
        )
        # 50 - 10 (log) - 15 (matched) - 5 (remaining) = 20
        assert result == 20.0

    def test_returns_zero_when_fully_staked(self):
        result = calculate_remaining_stake(
            target_stake=50.0,
            current_order=None,
            matched_in_log=50.0,
        )
        assert result == 0.0

    def test_returns_zero_when_over_staked(self):
        result = calculate_remaining_stake(
            target_stake=50.0,
            current_order=None,
            matched_in_log=60.0,
        )
        assert result == 0.0
