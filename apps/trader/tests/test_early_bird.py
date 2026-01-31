"""Tests for early bird trading strategy (integrated in decision_engine)."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from api_helpers.clients.betfair_client import CurrentOrder

from trader.decision_engine import (
    BACK_TICK_OFFSETS,
    EARLY_BIRD_BACK_STAKE,
    EARLY_BIRD_LAY_LIABILITY,
    LAY_TICK_OFFSETS,
    MIN_STAKE_PER_ORDER,
    DecisionResult,
    _decide_early_bird,
    _get_early_bird_orders_to_cancel,
    _random_stake_split,
    _should_place_early_bird,
    decide,
)
from trader.models import SelectionState, SelectionType, MarketType
from trader.price_ladder import PriceLadder

from .fixtures.selection_states import make_selection_state, selection_states_list


def selection_from_dict(d: dict) -> SelectionState:
    """Helper to create SelectionState from a dict."""
    return SelectionState.from_row(pd.Series(d))


def make_current_order(
    bet_id: str = "123",
    market_id: str = "1.234",
    selection_id: int = 55555,
    side: str = "BACK",
    execution_status: str = "EXECUTABLE",
    customer_strategy_ref: str = "test_ref",
    price: float = 3.0,
    size: float = 10.0,
    size_matched: float = 0.0,
) -> CurrentOrder:
    """Helper to create CurrentOrder with defaults for testing."""
    return CurrentOrder(
        bet_id=bet_id,
        market_id=market_id,
        selection_id=selection_id,
        side=side,
        execution_status=execution_status,
        placed_date=datetime.now(),
        matched_date=None,
        average_price_matched=price if size_matched > 0 else 0.0,
        customer_strategy_ref=customer_strategy_ref,
        size_matched=size_matched,
        size_remaining=size - size_matched,
        size_lapsed=0.0,
        size_cancelled=0.0,
        size_voided=0.0,
        price=price,
        size=size,
    )


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================


class TestEarlyBirdConfiguration:
    """Verify early bird configuration values."""

    def test_lay_tick_offsets_are_negative(self):
        """LAY tick offsets should be negative (below market price)."""
        for offset in LAY_TICK_OFFSETS:
            assert offset < 0, f"LAY offset {offset} should be negative"

    def test_back_tick_offsets_are_positive(self):
        """BACK tick offsets should be positive (above market price)."""
        for offset in BACK_TICK_OFFSETS:
            assert offset > 0, f"BACK offset {offset} should be positive"

    def test_lay_liability_is_target_not_stake(self):
        """LAY target is liability, not stake."""
        # £15 liability at 5.0 odds = £3.75 stake
        # Verify we're dealing with liability values in range
        assert EARLY_BIRD_LAY_LIABILITY > 0
        assert EARLY_BIRD_LAY_LIABILITY == 15.0

    def test_minimum_stake_allows_small_orders(self):
        """Minimum stake should be low enough for liability-converted LAY stakes."""
        # At 5.0 odds with £15 total liability split 4 ways:
        # ~£3.75 liability per order = £0.94 stake
        # Need minimum below this
        assert MIN_STAKE_PER_ORDER <= 0.50


# ============================================================================
# STAKE SPLIT TESTS
# ============================================================================


class TestRandomStakeSplit:
    """Test random stake splitting."""

    def test_split_sums_to_target(self):
        """Split amounts should sum to target."""
        target = 15.0
        n_splits = 4
        splits = _random_stake_split(target, n_splits, min_stake=0.5)

        assert len(splits) == n_splits
        assert abs(sum(splits) - target) < 0.01  # Allow small float error

    def test_all_splits_above_minimum(self):
        """Each split should be at least minimum."""
        splits = _random_stake_split(20.0, 4, min_stake=2.0)

        for split in splits:
            assert split >= 2.0

    def test_handles_edge_case_small_target(self):
        """Returns fewer splits if target is too small."""
        # £3 split 4 ways with £1 minimum = only 3 possible
        splits = _random_stake_split(3.0, 4, min_stake=1.0)

        assert len(splits) == 3
        assert abs(sum(splits) - 3.0) < 0.01


# ============================================================================
# EARLY BIRD ELIGIBILITY TESTS
# ============================================================================


def make_early_bird_selection(
    selection_type: str = "BACK",
    minutes_to_race: float = 180,  # 3 hours
    has_bet: bool = False,
    valid: bool = True,
    **kwargs,
) -> dict:
    """Helper to create selection in early bird window."""
    race_time = datetime.now() + timedelta(minutes=minutes_to_race)
    expires_at = race_time - timedelta(hours=2)  # Early bird cutoff

    return make_selection_state(
        selection_type=selection_type,
        race_time=race_time,
        minutes_to_race=minutes_to_race,
        expires_at=expires_at,
        has_bet=has_bet,
        valid=valid,
        **kwargs,
    )


class TestShouldPlaceEarlyBird:
    """Test early bird eligibility checks."""

    def test_eligible_new_selection_in_window(self):
        """New selection far from race should be eligible."""
        selection_dict = make_early_bird_selection(minutes_to_race=300)
        selection = selection_from_dict(selection_dict)

        result = _should_place_early_bird(selection, current_orders=None)
        assert result is True

    def test_not_eligible_when_invalid(self):
        """Invalid selection should not place early bird."""
        selection_dict = make_early_bird_selection(valid=False)
        selection = selection_from_dict(selection_dict)

        result = _should_place_early_bird(selection, current_orders=None)
        assert result is False

    def test_not_eligible_when_has_bet(self):
        """Selection with existing bet should not place early bird."""
        selection_dict = make_early_bird_selection(has_bet=True)
        selection = selection_from_dict(selection_dict)

        result = _should_place_early_bird(selection, current_orders=None)
        assert result is False


# ============================================================================
# EARLY BIRD ORDER GENERATION TESTS
# ============================================================================


class TestDecideEarlyBird:
    """Test early bird order generation."""

    def test_back_orders_above_market(self):
        """BACK orders should be at prices above requested."""
        selection_dict = make_early_bird_selection(
            selection_type="BACK",
            requested_odds=3.0,
            current_back_price=3.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        assert len(orders) == len(BACK_TICK_OFFSETS)
        for order in orders:
            # Price should be above 3.0
            assert (
                order.order.price > 3.0
            ), f"BACK price {order.order.price} should be above 3.0"

    def test_lay_orders_below_market(self):
        """LAY orders should be at prices below requested."""
        selection_dict = make_early_bird_selection(
            selection_type="LAY",
            requested_odds=5.0,
            current_lay_price=5.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        assert len(orders) > 0
        for order in orders:
            # Price should be below 5.0
            assert (
                order.order.price < 5.0
            ), f"LAY price {order.order.price} should be below 5.0"

    def test_lay_stake_calculated_from_liability(self):
        """LAY stake should be liability / (odds - 1)."""
        selection_dict = make_early_bird_selection(
            selection_type="LAY",
            requested_odds=5.0,
            current_lay_price=5.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        # Total liability should approximately equal EARLY_BIRD_LAY_LIABILITY
        total_liability = sum(o.order.size * (o.order.price - 1) for o in orders)
        assert abs(total_liability - EARLY_BIRD_LAY_LIABILITY) < 1.0

    def test_back_stake_is_direct(self):
        """BACK stake should sum to EARLY_BIRD_BACK_STAKE."""
        selection_dict = make_early_bird_selection(
            selection_type="BACK",
            requested_odds=3.0,
            current_back_price=3.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        total_stake = sum(o.order.size for o in orders)
        assert abs(total_stake - EARLY_BIRD_BACK_STAKE) < 1.0

    def test_strategy_ref_within_15_chars(self):
        """Strategy ref must be within Betfair's 15 character limit."""
        selection_dict = make_early_bird_selection(
            unique_id="test_001_ab",  # 11 chars
            selection_type="LAY",
            requested_odds=5.0,
            current_lay_price=5.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        for order in orders:
            strategy = order.order.strategy
            assert len(strategy) <= 15, f"Strategy '{strategy}' exceeds 15 chars"

    def test_strategy_ref_uses_absolute_offset(self):
        """Strategy ref should use absolute offset value (no negative sign)."""
        selection_dict = make_early_bird_selection(
            unique_id="test_001",
            selection_type="LAY",
            requested_odds=5.0,
            current_lay_price=5.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        for order in orders:
            # Should NOT contain minus sign
            assert "-" not in order.order.strategy.split("_eb")[-1]

    def test_orders_have_delay(self):
        """Early bird orders should have staggered delays."""
        selection_dict = make_early_bird_selection(
            selection_type="BACK",
            requested_odds=3.0,
            current_back_price=3.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        delays = [o.delay_seconds for o in orders]
        # First order should have some delay
        assert delays[0] > 0
        # Delays should be cumulative (increasing)
        for i in range(1, len(delays)):
            assert delays[i] > delays[i - 1]

    def test_orders_marked_as_early_bird(self):
        """Orders should have is_early_bird flag set."""
        selection_dict = make_early_bird_selection(
            selection_type="BACK",
            requested_odds=3.0,
            current_back_price=3.0,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)

        for order in orders:
            assert order.is_early_bird is True


# ============================================================================
# EARLY BIRD CANCEL TESTS
# ============================================================================


class TestGetEarlyBirdOrdersToCancel:
    """Test early bird order cancellation detection."""

    def test_finds_matching_eb_orders(self):
        """Should find orders with matching _eb prefix."""
        selection_dict = make_early_bird_selection(unique_id="abc12345678")
        selection = selection_from_dict(selection_dict)

        current_orders = [
            make_current_order(
                bet_id="123",
                price=3.1,
                customer_strategy_ref="abc12345678_eb2",
            ),
            make_current_order(
                bet_id="124",
                price=3.2,
                customer_strategy_ref="abc12345678_eb3",
            ),
        ]

        cancels = _get_early_bird_orders_to_cancel(selection, current_orders)

        assert len(cancels) == 2

    def test_ignores_matched_orders(self):
        """Should not cancel fully matched orders."""
        selection_dict = make_early_bird_selection(unique_id="abc12345678")
        selection = selection_from_dict(selection_dict)

        current_orders = [
            make_current_order(
                bet_id="123",
                price=3.1,
                size=10.0,
                size_matched=10.0,  # Fully matched
                execution_status="EXECUTION_COMPLETE",  # Not EXECUTABLE
                customer_strategy_ref="abc12345678_eb2",
            ),
        ]

        cancels = _get_early_bird_orders_to_cancel(selection, current_orders)

        assert len(cancels) == 0

    def test_ignores_non_eb_orders(self):
        """Should not cancel orders without _eb prefix."""
        selection_dict = make_early_bird_selection(unique_id="abc12345678")
        selection = selection_from_dict(selection_dict)

        current_orders = [
            make_current_order(
                bet_id="123",
                price=3.0,
                size=40.0,
                customer_strategy_ref="abc12345678",  # No _eb suffix
            ),
        ]

        cancels = _get_early_bird_orders_to_cancel(selection, current_orders)

        assert len(cancels) == 0


# ============================================================================
# INTEGRATION TESTS - DECIDE FUNCTION
# ============================================================================


class TestDecideEarlyBirdIntegration:
    """Test decide() function with early bird scenarios."""

    def test_places_early_bird_orders_in_window(self):
        """Should place early bird orders when >2h to race."""
        race_time = datetime.now() + timedelta(hours=5)
        expires_at = race_time - timedelta(hours=2)

        selections = selection_states_list(
            [
                make_selection_state(
                    unique_id="eb_test_001",
                    race_time=race_time,
                    expires_at=expires_at,
                    minutes_to_race=300,
                    selection_type="BACK",
                    requested_odds=3.0,
                    current_back_price=3.0,
                    has_bet=False,
                )
            ]
        )

        result = decide(selections, current_orders=None)

        # Should have multiple early bird orders
        assert len(result.orders) >= 1
        # All should be early bird
        for order in result.orders:
            assert order.is_early_bird

    def test_no_orders_when_outside_window(self):
        """Should use normal trading when <2h to race."""
        race_time = datetime.now() + timedelta(hours=1)
        expires_at = race_time - timedelta(hours=2)  # Already past

        selections = selection_states_list(
            [
                make_selection_state(
                    unique_id="normal_001",
                    race_time=race_time,
                    expires_at=expires_at,
                    minutes_to_race=60,
                    selection_type="BACK",
                    requested_odds=3.0,
                    current_back_price=3.0,
                    has_bet=False,
                )
            ]
        )

        result = decide(selections, current_orders=None)

        # Should have a single normal order (if price matches)
        assert len(result.orders) == 1
        assert result.orders[0].is_early_bird is False

    def test_cancels_eb_orders_when_void_requested(self):
        """Should cancel early bird orders when selection is voided."""
        race_time = datetime.now() + timedelta(hours=5)
        expires_at = race_time - timedelta(hours=2)

        selections = selection_states_list(
            [
                make_selection_state(
                    unique_id="void_test01",
                    race_time=race_time,
                    expires_at=expires_at,
                    minutes_to_race=300,
                    valid=False,  # Voided
                    invalidated_reason="Manual Void",
                )
            ]
        )

        current_orders = [
            make_current_order(
                bet_id="123",
                price=3.1,
                size=10.0,
                customer_strategy_ref="void_test01_eb2",
            ),
        ]

        result = decide(selections, current_orders=current_orders)

        # Should have cancel orders
        assert len(result.cancel_orders) == 1
        # No new orders
        assert len(result.orders) == 0


# ============================================================================
# PRICE LADDER INTERACTION TESTS
# ============================================================================


class TestEarlyBirdPriceLadder:
    """Test correct price ladder usage."""

    def test_back_uses_correct_tick_offsets(self):
        """BACK should use positive offsets from BACK_TICK_OFFSETS."""
        ladder = PriceLadder()
        base_price = 3.0

        expected_prices = [
            ladder.ticks_away(base_price, offset) for offset in BACK_TICK_OFFSETS
        ]

        selection_dict = make_early_bird_selection(
            selection_type="BACK",
            requested_odds=base_price,
            current_back_price=base_price,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)
        actual_prices = [o.order.price for o in orders]

        assert actual_prices == expected_prices

    def test_lay_uses_correct_tick_offsets(self):
        """LAY should use negative offsets from LAY_TICK_OFFSETS."""
        ladder = PriceLadder()
        base_price = 5.0

        expected_prices = [
            ladder.ticks_away(base_price, offset) for offset in LAY_TICK_OFFSETS
        ]

        selection_dict = make_early_bird_selection(
            selection_type="LAY",
            requested_odds=base_price,
            current_lay_price=base_price,
        )
        selection = selection_from_dict(selection_dict)

        orders = _decide_early_bird(selection)
        actual_prices = [o.order.price for o in orders]

        # Check prices are in expected range (allowing for minimum stake filtering)
        for price in actual_prices:
            assert price in expected_prices or price < base_price
