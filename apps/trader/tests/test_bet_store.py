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


class TestIsOrderStaleEarlyBirdMode:
    """Tests for is_order_stale with early bird expiry (max logic)."""

    def test_early_order_persists_until_cutoff(self):
        """Order at 10am, race 8pm - should hang until 6pm cutoff."""
        order = MagicMock()
        # Order placed at 10am
        order.placed_date = datetime(2026, 1, 26, 10, 0, 0, tzinfo=ZoneInfo("UTC"))

        # Race at 8pm, early bird cutoff at 6pm
        early_bird_expiry = datetime(2026, 1, 26, 18, 0, 0, tzinfo=ZoneInfo("UTC"))

        # At 2pm - order should NOT be stale (still before 6pm cutoff)
        import trader.bet_store as bet_store

        original_now = datetime.now

        try:
            # Mock "now" to be 2pm
            bet_store.datetime = MagicMock()
            bet_store.datetime.now.return_value = datetime(
                2026, 1, 26, 14, 0, 0, tzinfo=ZoneInfo("UTC")
            )
            assert is_order_stale(order, early_bird_expiry=early_bird_expiry) is False
        finally:
            bet_store.datetime = datetime

    def test_early_order_stale_after_cutoff(self):
        """Order at 10am, race 8pm - should be stale after 6pm."""
        order = MagicMock()
        order.placed_date = datetime(2026, 1, 26, 10, 0, 0, tzinfo=ZoneInfo("UTC"))

        # Cutoff was 6pm, now it's 6:30pm
        early_bird_expiry = datetime(2026, 1, 26, 18, 0, 0, tzinfo=ZoneInfo("UTC"))

        import trader.bet_store as bet_store

        try:
            bet_store.datetime = MagicMock()
            bet_store.datetime.now.return_value = datetime(
                2026, 1, 26, 18, 30, 0, tzinfo=ZoneInfo("UTC")
            )
            assert is_order_stale(order, early_bird_expiry=early_bird_expiry) is True
        finally:
            bet_store.datetime = datetime

    def test_late_order_uses_timeout(self):
        """Order at 6:30pm, race 8pm - should expire at 6:35pm (not 6pm cutoff)."""
        order = MagicMock()
        # Order placed at 6:30pm (after the 6pm cutoff)
        order.placed_date = datetime(2026, 1, 26, 18, 30, 0, tzinfo=ZoneInfo("UTC"))

        # Cutoff was 6pm (already passed when order was placed)
        early_bird_expiry = datetime(2026, 1, 26, 18, 0, 0, tzinfo=ZoneInfo("UTC"))

        import trader.bet_store as bet_store

        try:
            # At 6:33pm - 3 mins after placement, timeout is 5 mins
            bet_store.datetime = MagicMock()
            bet_store.datetime.now.return_value = datetime(
                2026, 1, 26, 18, 33, 0, tzinfo=ZoneInfo("UTC")
            )
            # max(6pm, 6:35pm) = 6:35pm, now is 6:33pm - NOT stale
            assert is_order_stale(order, early_bird_expiry=early_bird_expiry) is False

            # At 6:36pm - 6 mins after placement
            bet_store.datetime.now.return_value = datetime(
                2026, 1, 26, 18, 36, 0, tzinfo=ZoneInfo("UTC")
            )
            # max(6pm, 6:35pm) = 6:35pm, now is 6:36pm - STALE
            assert is_order_stale(order, early_bird_expiry=early_bird_expiry) is True
        finally:
            bet_store.datetime = datetime


class TestIsOrderStaleWithTimeout:
    """Tests for is_order_stale with default timeout (no early bird)."""

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
