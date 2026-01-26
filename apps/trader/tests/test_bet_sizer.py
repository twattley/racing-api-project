"""
Tests for bet_sizer module.

Tests the critical stake/liability calculations for BACK and LAY bets.
"""

from datetime import datetime, timedelta

from trader.bet_sizer import calculate_sizing, is_fully_matched
from trader.models import SelectionState


def make_selection(
    selection_type: str = "BACK",
    calculated_stake: float = 10.0,
    total_matched: float = 0.0,
    total_liability: float = 0.0,
    requested_odds: float = 3.0,
    current_back_price: float | None = 3.0,
    current_lay_price: float | None = 3.2,
) -> SelectionState:
    """Helper to create SelectionState for bet_sizer tests."""
    return SelectionState(
        unique_id="test_001",
        race_id=12345,
        race_time=datetime.now() + timedelta(hours=1),
        race_date=datetime.now().date(),
        horse_id=1001,
        horse_name="Test Horse",
        selection_type=selection_type,
        market_type="WIN",
        requested_odds=requested_odds,
        stake_points=1.0,
        market_id="1.234567890",
        selection_id=55555,
        valid=True,
        invalidated_reason=None,
        original_runners=10,
        original_price=3.0,
        current_back_price=current_back_price,
        current_lay_price=current_lay_price,
        runner_status="ACTIVE",
        current_runners=10,
        total_matched=total_matched,
        total_liability=total_liability,
        bet_count=0,
        has_bet=False,
        fully_matched=False,
        calculated_stake=calculated_stake,
        minutes_to_race=60.0,
        short_price_removed=False,
        place_terms_changed=False,
        use_fill_or_kill=False,
        within_stake_limit=True,
    )


class TestBackBetSizing:
    """Tests for BACK bet calculations."""

    def test_new_back_bet_with_good_price(self):
        """New BACK bet when current price >= requested."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=0,
            requested_odds=3.0,
            current_back_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.remaining_stake == 10.0
        assert result.bet_price == 3.5
        assert "BACK 10.00 @ 3.5" in result.reason

    def test_new_back_bet_with_bad_price(self):
        """New BACK bet when current price < requested - should not bet."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=0,
            requested_odds=3.0,
            current_back_price=2.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "Back price 2.5 < requested 3.0" in result.reason

    def test_partial_back_bet(self):
        """BACK bet with some already matched."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=4.0,
            requested_odds=3.0,
            current_back_price=3.2,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.remaining_stake == 6.0
        assert "matched: 4.00/10.00" in result.reason

    def test_back_bet_fully_matched(self):
        """BACK bet that's already fully matched."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=10.0,
            requested_odds=3.0,
            current_back_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "Fully matched" in result.reason

    def test_back_bet_remaining_below_minimum(self):
        """BACK bet with remaining stake < £1."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=9.50,
            requested_odds=3.0,
            current_back_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "Fully matched" in result.reason

    def test_back_bet_no_price_available(self):
        """BACK bet when no current price."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=0,
            requested_odds=3.0,
            current_back_price=None,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "No current back price" in result.reason

    def test_back_bet_rounds_down_stake(self):
        """Remaining stake should round down to 2 decimal places."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=3.333,
            requested_odds=3.0,
            current_back_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.remaining_stake == 6.66  # Rounded down from 6.667


class TestLayBetSizing:
    """Tests for LAY bet calculations."""

    def test_new_lay_bet_with_good_price(self):
        """New LAY bet when current price <= requested."""
        # Target liability = £10 (calculated_stake for LAY = target liability)
        # Current price 2.5, stake needed = 10 / (2.5-1) = 10 / 1.5 = 6.66
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=0,
            total_liability=0.0,
            requested_odds=3.0,
            current_lay_price=2.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.remaining_stake == 6.66  # £10 liability / 1.5 = 6.66
        assert result.bet_price == 2.5
        assert "LAY" in result.reason

    def test_new_lay_bet_with_bad_price(self):
        """New LAY bet when current price > requested - should not bet."""
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=0,
            total_liability=0.0,
            requested_odds=3.0,
            current_lay_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "Lay price 3.5 > requested 3.0" in result.reason

    def test_partial_lay_bet(self):
        """LAY bet with some liability already matched."""
        # Target liability: £10
        # Matched liability: £7.50
        # Remaining liability: £2.50
        # Current price 2.5, stake needed: £2.50 / 1.5 = £1.66
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=5.0,
            total_liability=7.50,
            requested_odds=3.0,
            current_lay_price=2.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.remaining_stake == 1.66
        assert "LAY 1.66 @ 2.5 (liability: 7.50/10.00)" in result.reason

    def test_lay_bet_liability_filled(self):
        """LAY bet where liability target is met."""
        # Target liability: £10
        # Matched liability: £10
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=10.0,
            total_liability=10.0,
            requested_odds=3.0,
            current_lay_price=2.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "Liability filled" in result.reason

    def test_lay_bet_no_price_available(self):
        """LAY bet when no current price."""
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=0,
            total_liability=0.0,
            requested_odds=3.0,
            current_lay_price=None,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "No current lay price" in result.reason

    def test_lay_bet_price_at_exactly_requested(self):
        """LAY bet when current price equals requested - should bet."""
        # Target liability = £10
        # Current price 3.0, stake needed = 10 / (3.0-1) = 10 / 2 = 5
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=0,
            total_liability=0.0,
            requested_odds=3.0,
            current_lay_price=3.0,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.bet_price == 3.0
        assert result.remaining_stake == 5.0

    def test_lay_bet_invalid_price(self):
        """LAY bet with price <= 1.0."""
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=0,
            total_liability=0.0,
            requested_odds=3.0,
            current_lay_price=1.0,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
        assert "Invalid lay price" in result.reason


class TestIsFullyMatched:
    """Tests for fully_matched detection."""

    def test_back_fully_matched(self):
        """BACK bet is fully matched when total >= target."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=10.0,
            requested_odds=3.0,
        )

        assert is_fully_matched(selection) is True

    def test_back_nearly_matched(self):
        """BACK bet nearly matched (within £1 tolerance)."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=9.50,
            requested_odds=3.0,
        )

        assert is_fully_matched(selection) is True

    def test_back_not_matched(self):
        """BACK bet not matched."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=5.0,
            requested_odds=3.0,
        )

        assert is_fully_matched(selection) is False

    def test_lay_fully_matched(self):
        """LAY bet is fully matched when liability target met."""
        # Target liability = £10
        # Matched liability = £10
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=10.0,
            total_liability=10.0,
            requested_odds=3.0,
        )

        assert is_fully_matched(selection) is True

    def test_lay_not_matched(self):
        """LAY bet not matched - liability not met."""
        # Target liability = £10
        # Matched liability = £5
        selection = make_selection(
            selection_type="LAY",
            calculated_stake=10.0,
            total_matched=4.0,
            total_liability=5.0,
            requested_odds=3.0,
        )

        assert is_fully_matched(selection) is False


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_total_matched_treated_as_zero(self):
        """0 total_matched should work correctly."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=0.0,
            requested_odds=3.0,
            current_back_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is True
        assert result.remaining_stake == 10.0

    def test_very_small_remaining_amount(self):
        """Very small remaining should not trigger a bet."""
        selection = make_selection(
            selection_type="BACK",
            calculated_stake=10.0,
            total_matched=9.99,
            requested_odds=3.0,
            current_back_price=3.5,
        )

        result = calculate_sizing(selection)

        assert result.should_bet is False
