"""
Tests for bet_sizer module.

Tests the critical stake/liability calculations for BACK and LAY bets.
"""

import pandas as pd
from trader.bet_sizer import calculate_sizing, is_fully_matched


class TestBackBetSizing:
    """Tests for BACK bet calculations."""

    def test_new_back_bet_with_good_price(self):
        """New BACK bet when current price >= requested."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": 3.5,
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.remaining_stake == 10.0
        assert result.bet_price == 3.5
        assert "BACK 10.00 @ 3.5" in result.reason

    def test_new_back_bet_with_bad_price(self):
        """New BACK bet when current price < requested - should not bet."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": 2.5,
                "current_lay_price": 2.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "Back price 2.5 < requested 3.0" in result.reason

    def test_partial_back_bet(self):
        """BACK bet with some already matched."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 4.0,
                "requested_odds": 3.0,
                "current_back_price": 3.2,
                "current_lay_price": 3.3,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.remaining_stake == 6.0
        assert "matched: 4.00/10.00" in result.reason

    def test_back_bet_fully_matched(self):
        """BACK bet that's already fully matched."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 10.0,
                "requested_odds": 3.0,
                "current_back_price": 3.5,
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "Fully matched" in result.reason

    def test_back_bet_remaining_below_minimum(self):
        """BACK bet with remaining stake < £1."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 9.50,
                "requested_odds": 3.0,
                "current_back_price": 3.5,
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "Fully matched" in result.reason

    def test_back_bet_no_price_available(self):
        """BACK bet when no current price."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": None,
                "current_lay_price": None,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "No current back price" in result.reason

    def test_back_bet_rounds_down_stake(self):
        """Remaining stake should round down to 2 decimal places."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 3.333,
                "requested_odds": 3.0,
                "current_back_price": 3.5,
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.remaining_stake == 6.66  # Rounded down from 6.667


class TestLayBetSizing:
    """Tests for LAY bet calculations."""

    def test_new_lay_bet_with_good_price(self):
        """New LAY bet when current price <= requested."""
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,  # Target liability = 10 * (3-1) = £20
                "current_back_price": 2.4,
                "current_lay_price": 2.5,  # Stake needed = 20 / (2.5-1) = £13.33
                "average_matched_price": None,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.remaining_stake == 13.33  # £20 liability / 1.5 = 13.33
        assert result.bet_price == 2.5
        assert "LAY" in result.reason

    def test_new_lay_bet_with_bad_price(self):
        """New LAY bet when current price > requested - should not bet."""
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": 3.4,
                "current_lay_price": 3.5,
                "average_matched_price": None,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "Lay price 3.5 > requested 3.0" in result.reason

    def test_partial_lay_bet(self):
        """LAY bet with some liability already matched."""
        # Target: stake 10 @ 3.0 = £20 liability
        # Matched: 5 @ 2.5 = 5 * 1.5 = £7.50 liability
        # Remaining liability: £20 - £7.50 = £12.50
        # Current price 2.5, stake needed: £12.50 / 1.5 = £8.33
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 5.0,
                "requested_odds": 3.0,
                "current_back_price": 2.4,
                "current_lay_price": 2.5,
                "average_matched_price": 2.5,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.remaining_stake == 8.33
        assert "liability: 7.50/20.00" in result.reason

    def test_lay_bet_liability_filled(self):
        """LAY bet where liability target is met."""
        # Target: stake 10 @ 3.0 = £20 liability
        # Matched: 10 @ 3.0 = 10 * 2.0 = £20 liability
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 10.0,
                "requested_odds": 3.0,
                "current_back_price": 2.4,
                "current_lay_price": 2.5,
                "average_matched_price": 3.0,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "Liability filled" in result.reason

    def test_lay_bet_no_price_available(self):
        """LAY bet when no current price."""
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": None,
                "current_lay_price": None,
                "average_matched_price": None,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "No current lay price" in result.reason

    def test_lay_bet_price_at_exactly_requested(self):
        """LAY bet when current price equals requested - should bet."""
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": 2.9,
                "current_lay_price": 3.0,
                "average_matched_price": None,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.bet_price == 3.0
        # Target liability = 10 * 2 = 20, stake at 3.0 = 20/2 = 10
        assert result.remaining_stake == 10.0

    def test_lay_bet_invalid_price(self):
        """LAY bet with price <= 1.0."""
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": 0.9,
                "current_lay_price": 1.0,
                "average_matched_price": None,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "Invalid lay price" in result.reason


class TestIsFullyMatched:
    """Tests for fully_matched detection."""

    def test_back_fully_matched(self):
        """BACK bet is fully matched when total >= target."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 10.0,
                "requested_odds": 3.0,
                "average_matched_price": 3.2,
            }
        )

        assert is_fully_matched(row) is True

    def test_back_nearly_matched(self):
        """BACK bet nearly matched (within £1 tolerance)."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 9.50,
                "requested_odds": 3.0,
                "average_matched_price": 3.2,
            }
        )

        assert is_fully_matched(row) is True

    def test_back_not_matched(self):
        """BACK bet not matched."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 5.0,
                "requested_odds": 3.0,
                "average_matched_price": 3.2,
            }
        )

        assert is_fully_matched(row) is False

    def test_lay_fully_matched(self):
        """LAY bet is fully matched when liability target met."""
        # Target liability = 10 * (3-1) = £20
        # Matched: 10 @ 3.0 = 10 * 2 = £20
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 10.0,
                "requested_odds": 3.0,
                "average_matched_price": 3.0,
            }
        )

        assert is_fully_matched(row) is True

    def test_lay_not_matched(self):
        """LAY bet not matched - liability not met."""
        # Target liability = 10 * (3-1) = £20
        # Matched: 5 @ 3.0 = 5 * 2 = £10
        row = pd.Series(
            {
                "selection_type": "LAY",
                "calculated_stake": 10.0,
                "total_matched": 5.0,
                "requested_odds": 3.0,
                "average_matched_price": 3.0,
            }
        )

        assert is_fully_matched(row) is False


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_total_matched_treated_as_zero(self):
        """None or NaN total_matched should be treated as 0."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": None,
                "requested_odds": 3.0,
                "current_back_price": 3.5,
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is True
        assert result.remaining_stake == 10.0

    def test_nan_back_price(self):
        """NaN price should be treated as unavailable."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 0,
                "requested_odds": 3.0,
                "current_back_price": float("nan"),
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
        assert "No current back price" in result.reason

    def test_very_small_remaining_amount(self):
        """Very small remaining should not trigger a bet."""
        row = pd.Series(
            {
                "selection_type": "BACK",
                "calculated_stake": 10.0,
                "total_matched": 9.99,
                "requested_odds": 3.0,
                "current_back_price": 3.5,
                "current_lay_price": 3.6,
            }
        )

        result = calculate_sizing(row)

        assert result.should_bet is False
