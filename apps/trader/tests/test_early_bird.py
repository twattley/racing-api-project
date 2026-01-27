"""Tests for early bird trading strategy."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.early_bird import (
    BACK_STAKE,
    BACK_TICK_OFFSETS,
    LAY_LIABILITY,
    LAY_TICK_OFFSETS,
    EarlyBirdOrder,
    generate_early_bird_orders,
    is_early_bird_time,
    should_use_early_bird,
    sleep_between_orders,
)
from trader.models import MarketType, SelectionState, SelectionType
from trader.price_ladder import PriceLadder


def make_selection(
    selection_type: SelectionType = SelectionType.BACK,
    current_back_price: float | None = 3.0,
    current_lay_price: float | None = 3.2,
    minutes_to_race: float = 300.0,  # 5 hours
    has_bet: bool = False,
    expires_at: datetime | None = None,
) -> SelectionState:
    """Helper to create SelectionState for tests."""
    race_time = datetime.now(ZoneInfo("UTC")) + timedelta(minutes=minutes_to_race)
    if expires_at is None:
        expires_at = race_time - timedelta(hours=2)

    return SelectionState(
        unique_id="test_001",
        race_id=12345,
        race_time=race_time,
        race_date=datetime.now().date(),
        horse_id=1001,
        horse_name="Test Horse",
        selection_type=selection_type,
        market_type=MarketType.WIN,
        requested_odds=3.0,
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
        total_matched=0.0,
        total_liability=0.0,
        bet_count=0,
        has_bet=has_bet,
        fully_matched=False,
        calculated_stake=40.0,
        minutes_to_race=minutes_to_race,
        expires_at=expires_at,
        short_price_removed=False,
        place_terms_changed=False,
        use_fill_or_kill=False,
        within_stake_limit=True,
    )


class TestGenerateEarlyBirdOrders:
    """Tests for order generation."""

    def test_back_bet_generates_orders_above_market(self):
        """BACK bet creates orders at higher prices."""
        selection = make_selection(
            selection_type=SelectionType.BACK,
            current_back_price=3.0,
        )

        orders = generate_early_bird_orders(selection)

        assert len(orders) == len(BACK_TICK_OFFSETS)
        for order in orders:
            assert order.price > 3.0
            assert order.stake == BACK_STAKE
            assert order.ticks_from_market > 0

    def test_lay_bet_generates_orders_below_market(self):
        """LAY bet creates orders at lower prices."""
        selection = make_selection(
            selection_type=SelectionType.LAY,
            current_lay_price=3.2,
        )

        orders = generate_early_bird_orders(selection)

        assert len(orders) == len(LAY_TICK_OFFSETS)
        for order in orders:
            assert order.price < 3.2
            assert order.stake == LAY_LIABILITY
            assert order.ticks_from_market < 0

    def test_back_orders_at_correct_prices(self):
        """BACK orders use correct tick offsets."""
        selection = make_selection(
            selection_type=SelectionType.BACK,
            current_back_price=3.0,
        )
        ladder = PriceLadder()

        orders = generate_early_bird_orders(selection)

        expected_prices = [
            ladder.ticks_away(3.0, offset) for offset in BACK_TICK_OFFSETS
        ]
        actual_prices = [o.price for o in orders]

        assert actual_prices == expected_prices

    def test_lay_orders_at_correct_prices(self):
        """LAY orders use correct tick offsets."""
        selection = make_selection(
            selection_type=SelectionType.LAY,
            current_lay_price=3.0,
        )
        ladder = PriceLadder()

        orders = generate_early_bird_orders(selection)

        expected_prices = [
            ladder.ticks_away(3.0, offset) for offset in LAY_TICK_OFFSETS
        ]
        actual_prices = [o.price for o in orders]

        assert actual_prices == expected_prices

    def test_no_orders_when_no_price(self):
        """Returns empty list when market price is None."""
        selection = make_selection(
            selection_type=SelectionType.BACK,
            current_back_price=None,
        )

        orders = generate_early_bird_orders(selection)

        assert orders == []

    def test_orders_at_price_boundary(self):
        """Handles prices near ladder boundary."""
        # Price near top of ladder - some offsets may be out of range
        selection = make_selection(
            selection_type=SelectionType.BACK,
            current_back_price=19.5,
        )

        orders = generate_early_bird_orders(selection)

        # Should get some orders, but maybe not all if they exceed 20.0
        assert len(orders) <= len(BACK_TICK_OFFSETS)
        for order in orders:
            assert order.price <= 20.0


class TestEarlyBirdOrder:
    """Tests for EarlyBirdOrder dataclass."""

    def test_description_above_market(self):
        """Description shows 'above' for positive offsets."""
        selection = make_selection()
        order = EarlyBirdOrder(
            selection=selection,
            price=3.15,
            stake=10.0,
            ticks_from_market=3,
        )

        assert "10.00 @ 3.15" in order.description
        assert "3 ticks above" in order.description

    def test_description_below_market(self):
        """Description shows 'below' for negative offsets."""
        selection = make_selection()
        order = EarlyBirdOrder(
            selection=selection,
            price=2.90,
            stake=15.0,
            ticks_from_market=-2,
        )

        assert "15.00 @ 2.9" in order.description
        assert "2 ticks below" in order.description


class TestIsEarlyBirdTime:
    """Tests for early bird time check."""

    def test_before_expiry_is_early_bird(self):
        """Returns True when before expires_at."""
        # expires_at is 3 hours from now
        expires_at = datetime.now(ZoneInfo("UTC")) + timedelta(hours=3)
        selection = make_selection(expires_at=expires_at)

        assert is_early_bird_time(selection) is True

    def test_after_expiry_is_not_early_bird(self):
        """Returns False when after expires_at."""
        # expires_at was 1 hour ago
        expires_at = datetime.now(ZoneInfo("UTC")) - timedelta(hours=1)
        selection = make_selection(expires_at=expires_at)

        assert is_early_bird_time(selection) is False


class TestShouldUseEarlyBird:
    """Tests for early bird eligibility."""

    def test_eligible_selection(self):
        """Selection far from race, no bets, before cutoff."""
        expires_at = datetime.now(ZoneInfo("UTC")) + timedelta(hours=3)
        selection = make_selection(
            minutes_to_race=300,  # 5 hours
            has_bet=False,
            expires_at=expires_at,
        )

        is_eligible, reason = should_use_early_bird(selection)
        assert is_eligible is True
        assert "eligible" in reason

    def test_not_eligible_after_cutoff(self):
        """Not eligible after expires_at."""
        expires_at = datetime.now(ZoneInfo("UTC")) - timedelta(hours=1)
        selection = make_selection(
            minutes_to_race=60,
            has_bet=False,
            expires_at=expires_at,
        )

        is_eligible, reason = should_use_early_bird(selection)
        assert is_eligible is False
        assert "cutoff" in reason

    def test_not_eligible_race_too_soon(self):
        """Not eligible when race is less than 3 hours away."""
        expires_at = datetime.now(ZoneInfo("UTC")) + timedelta(hours=1)
        selection = make_selection(
            minutes_to_race=120,  # 2 hours - too soon
            has_bet=False,
            expires_at=expires_at,
        )

        is_eligible, reason = should_use_early_bird(selection)
        assert is_eligible is False
        assert "too soon" in reason

    def test_not_eligible_has_bet(self):
        """Not eligible for top-ups (already has bet)."""
        expires_at = datetime.now(ZoneInfo("UTC")) + timedelta(hours=3)
        selection = make_selection(
            minutes_to_race=300,
            has_bet=True,  # Already has bet
            expires_at=expires_at,
        )

        is_eligible, reason = should_use_early_bird(selection)
        assert is_eligible is False
        assert "already has bet" in reason


class TestSleepBetweenOrders:
    """Tests for sleep function."""

    def test_no_sleep_when_disabled(self):
        """No sleep when range is (0, 0)."""
        import time

        start = time.time()
        sleep_between_orders(sleep_range=(0, 0))
        elapsed = time.time() - start

        assert elapsed < 0.1  # Should be nearly instant
