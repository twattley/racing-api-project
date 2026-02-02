"""
Tests for the decision engine.

The decision engine is a PURE FUNCTION:
- Input: list[SelectionState] objects
- Output: DecisionResult with BetFairOrder objects and cash out market IDs

No side effects, no API calls, no database writes.
This makes it trivial to test exhaustively.
"""

from apps.trader.src.trader.models import SelectionState

from trader.decision_engine import DecisionResult, decide

from .fixtures.selection_states import already_invalid  # Preset scenarios
from .fixtures.selection_states import (
    eight_to_seven_place_invalid,
    eight_to_seven_win_valid,
    fully_matched,
    make_selection_state,
    selection_states_list,
    valid_back_win_no_bet,
    valid_lay_win_no_bet,
)

# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestEightToSevenValidation:
    """8→7 runner reduction invalidates PLACE bets only."""

    def test_place_bet_invalidated_on_8_to_7(self):
        """PLACE bet with 8→7 runners should be marked invalid."""
        selections: list[SelectionState] = selection_states_list(
            [eight_to_seven_place_invalid()]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.invalidations) == 1
        assert "8→7" in result.invalidations[0][1]

    def test_place_bet_invalidated_on_8_to_6(self):
        """PLACE bet with 8→6 runners should also be invalid."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    market_type="PLACE",
                    original_runners=8,
                    current_runners=6,
                    place_terms_changed=True,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.invalidations) == 1
        assert "8→6" in result.invalidations[0][1]

    def test_win_bet_valid_on_8_to_7(self):
        """WIN bet should remain valid even with 8→7 runners."""
        selections: list[SelectionState] = selection_states_list(
            [eight_to_seven_win_valid()]
        )
        result: DecisionResult = decide(selections)

        # Should place order, not invalidate
        assert len(result.orders) == 1
        assert len(result.invalidations) == 0

    def test_place_bet_valid_when_runners_unchanged(self):
        """PLACE bet with same runner count should be valid."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    market_type="PLACE",
                    original_runners=8,
                    current_runners=8,
                    place_terms_changed=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        assert len(result.invalidations) == 0

    def test_place_bet_valid_when_started_with_more_than_8(self):
        """PLACE bet starting with 9+ runners, dropping to 8, is fine."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    market_type="PLACE",
                    original_runners=10,
                    current_runners=8,
                    place_terms_changed=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Place terms don't change when dropping from 10 to 8
        assert len(result.orders) == 1
        assert len(result.invalidations) == 0

    def test_place_bet_with_existing_bet_cashes_out_on_8_to_7(self):
        """PLACE bet with 8→7 and existing bet should cash out."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    market_type="PLACE",
                    original_runners=8,
                    current_runners=7,
                    place_terms_changed=True,
                    has_bet=True,
                    total_matched=20.0,
                    market_id="1.12345",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 1
        assert result.cash_out_market_ids[0] == "1.12345"
        assert len(result.invalidations) == 1


class TestRunnerRemoval:
    """Test runner removal handling."""

    def test_removed_runner_without_bet(self):
        """Removed runner without bet should invalidate."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    runner_status="REMOVED",
                    has_bet=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 0
        assert len(result.invalidations) == 1
        assert "Runner removed" in result.invalidations[0][1]

    def test_removed_runner_with_bet(self):
        """Removed runner with bet should invalidate AND cash out."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    runner_status="REMOVED",
                    has_bet=True,
                    market_id="1.99999",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 1
        assert len(result.invalidations) == 1


class TestShortPriceRemoval:
    """Short price removal invalidation tests."""

    def test_short_price_removed_without_bet(self):
        """Short price removed without bet should invalidate only."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    short_price_removed=True,
                    has_bet=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 0
        assert len(result.invalidations) == 1
        assert "Short-priced runner" in result.invalidations[0][1]

    def test_short_price_removed_with_bet(self):
        """Short price removed with bet should invalidate AND cash out."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    short_price_removed=True,
                    has_bet=True,
                    market_id="1.88888",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 1
        assert "1.88888" in result.cash_out_market_ids
        assert len(result.invalidations) == 1

    def test_no_short_price_removal_proceeds_normally(self):
        """Without short price removal, normal betting proceeds."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    short_price_removed=False,
                    has_bet=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1  # Should place bet


class TestAlreadyInvalid:
    """Already invalid selections should not generate new orders."""

    def test_already_invalid_returns_no_orders(self):
        """No orders for already-invalid selection."""
        selections: list[SelectionState] = selection_states_list([already_invalid()])
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 0
        # Note: invalidation is recorded so executor can update DB
        assert len(result.invalidations) == 1

    def test_cashed_out_returns_no_action_at_all(self):
        """Already cashed out selections are silently skipped."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="cashed_out_001",
                    valid=False,
                    invalidated_reason="Cashed Out",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 0
        assert len(result.invalidations) == 0  # No action - already processed


# ============================================================================
# PRICE MATCHING TESTS
# ============================================================================


class TestPriceMatching:
    """Only bet when price is acceptable."""

    def test_back_bet_at_requested_price(self):
        """BACK bet placed when price equals requested."""
        state = valid_back_win_no_bet()
        selections: list[SelectionState] = selection_states_list([state])
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        assert result.orders[0].order.side == "BACK"
        assert result.orders[0].order.price == state["requested_odds"]

    def test_back_bet_skipped_when_price_drifted_down(self):
        """BACK bet not placed when price dropped significantly."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    selection_type="BACK",
                    requested_odds=3.0,
                    current_back_price=2.5,  # Worse for BACK - drifted down
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Should wait, not place order
        assert len(result.orders) == 0
        # But should NOT invalidate - price might come back
        assert len(result.invalidations) == 0

    def test_lay_bet_at_requested_price(self):
        """LAY bet placed when price equals requested."""
        state = valid_lay_win_no_bet()
        selections: list[SelectionState] = selection_states_list([state])
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        assert result.orders[0].order.side == "LAY"

    def test_lay_bet_skipped_when_price_drifted_up(self):
        """LAY bet not placed when price increased significantly."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    selection_type="LAY",
                    requested_odds=3.0,
                    current_lay_price=4.0,  # Worse for LAY - drifted up
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Should wait, not place order
        assert len(result.orders) == 0
        # But should NOT invalidate
        assert len(result.invalidations) == 0


# ============================================================================
# FULLY MATCHED TESTS
# ============================================================================


class TestFullyMatched:
    """Fully matched selections need no more action."""

    def test_fully_matched_returns_no_action(self):
        """No action for fully matched selection."""
        selections: list[SelectionState] = selection_states_list([fully_matched()])
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 0
        assert len(result.invalidations) == 0

    def test_partial_match_places_topup_order(self):
        """Selection with partial match places top-up order for remaining stake."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    has_bet=True,
                    total_matched=20.0,  # Already matched £20
                    calculated_stake=40.0,  # Target is £40
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Should place order for remaining £20
        assert len(result.orders) == 1
        assert result.orders[0].order.size == 20.0


# ============================================================================
# ORDER CREATION TESTS
# ============================================================================


class TestOrderCreation:
    """Test that BetFairOrder objects are created correctly."""

    def test_back_order_fields(self):
        """BACK order has correct fields."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="test-back",
                    selection_type="BACK",
                    market_type="WIN",
                    calculated_stake=50.0,
                    requested_odds=4.5,
                    current_back_price=4.5,  # Must match requested for price check to pass
                    selection_id=99999,
                    market_id="1.98765432",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        order = result.orders[0].order  # Access wrapped order
        assert order.size == 50.0
        assert order.price == 4.5
        assert order.selection_id == "99999"
        assert order.market_id == "1.98765432"
        assert order.side == "BACK"
        assert order.strategy == "test-back"  # Uses unique_id as strategy

    def test_lay_order_side(self):
        """LAY order has correct side."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    selection_type="LAY",
                    current_lay_price=3.0,  # Needs to be acceptable
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        assert result.orders[0].order.side == "LAY"


# ============================================================================
# MULTIPLE SELECTIONS TESTS
# ============================================================================


class TestMultipleSelections:
    """Handle batch of selections."""

    def test_mixed_valid_invalid(self):
        """Process mix of valid and invalid selections."""
        selections: list[SelectionState] = selection_states_list(
            [
                valid_back_win_no_bet(),
                eight_to_seven_place_invalid(),
                fully_matched(),
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1  # Only valid_back_win_no_bet
        assert len(result.invalidations) == 1  # Only eight_to_seven_place_invalid
        # fully_matched produces no action

    def test_multiple_orders(self):
        """Multiple valid selections generate multiple orders."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(unique_id="sel-1", selection_id=111),
                make_selection_state(unique_id="sel-2", selection_id=222),
                make_selection_state(unique_id="sel-3", selection_id=333),
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 3

    def test_deduplicates_cash_out_markets(self):
        """Multiple invalidations in same market deduplicate."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="sel-1",
                    runner_status="REMOVED",
                    has_bet=True,
                    market_id="1.same",
                ),
                make_selection_state(
                    unique_id="sel-2",
                    runner_status="REMOVED",
                    has_bet=True,
                    market_id="1.same",
                ),
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.cash_out_market_ids) == 1
        assert result.cash_out_market_ids[0] == "1.same"


# ============================================================================
# EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_list(self):
        """Empty input returns empty result."""
        result: DecisionResult = decide([])

        assert isinstance(result, DecisionResult)
        assert len(result.orders) == 0
        assert len(result.cash_out_market_ids) == 0
        assert len(result.invalidations) == 0

    def test_null_prices_skipped(self):
        """Skip if no price available (doesn't crash)."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    current_back_price=None,
                    current_lay_price=None,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Should skip gracefully, not crash
        assert isinstance(result, DecisionResult)

    def test_null_runner_count_handled(self):
        """Null runner count doesn't trigger 8→7 rule."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    market_type="PLACE",
                    original_runners=None,
                    current_runners=None,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Should not invalidate due to null values
        # May or may not place order depending on other checks
        assert len(result.invalidations) == 0


# ============================================================================
# STAKE LIMIT FAILSAFE TESTS
# ============================================================================


class TestStakeLimitFailsafe:
    """Test within_stake_limit failsafe prevents over-betting."""

    def test_exceeded_stake_limit_back_skipped(self):
        """BACK bet exceeding stake limit should be skipped."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="exceeded_back",
                    selection_type="BACK",
                    total_matched=100.0,
                    within_stake_limit=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.invalidations) == 0  # Not invalidated, just skipped

    def test_exceeded_stake_limit_lay_skipped(self):
        """LAY bet exceeding liability limit should be skipped."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="exceeded_lay",
                    selection_type="LAY",
                    total_liability=100.0,
                    within_stake_limit=False,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 0
        assert len(result.invalidations) == 0

    def test_within_stake_limit_proceeds(self):
        """Bet within stake limit should proceed."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="within_limit",
                    selection_type="BACK",
                    total_matched=10.0,
                    within_stake_limit=True,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        assert result.orders[0].within_stake_limit is True

    def test_stake_limit_defaults_to_true(self):
        """If flag is missing, defaults to True (assume OK)."""
        row_data = make_selection_state(unique_id="limit_default")
        # Remove the flag to test default behavior
        del row_data["within_stake_limit"]
        selections: list[SelectionState] = selection_states_list([row_data])
        result: DecisionResult = decide(selections)

        # Should proceed - default is True
        assert len(result.orders) == 1

    def test_order_carries_stake_limit_flag(self):
        """OrderWithState should carry the within_stake_limit flag."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="carry_flag",
                    within_stake_limit=True,
                )
            ]
        )
        result: DecisionResult = decide(selections)

        assert len(result.orders) == 1
        assert result.orders[0].within_stake_limit is True


# ============================================================================
# CURRENT ORDERS PARAMETER TESTS
# ============================================================================


class TestCurrentOrdersParameter:
    """Test that current_orders parameter is accepted but doesn't affect decisions.

    Note: Since reconciliation cancels all executable orders before decide() runs,
    the decision engine no longer checks for existing orders. The current_orders
    parameter is kept for backwards compatibility but doesn't affect logic.
    """

    def test_generates_order_with_executable_order_present(self):
        """Should generate order even when Betfair has executable order.

        (Reconciliation should have cancelled these before decide() is called)
        """
        from unittest.mock import MagicMock

        mock_order = MagicMock()
        mock_order.customer_strategy_ref = "test_existing_001"
        mock_order.execution_status = "EXECUTABLE"
        mock_order.market_id = "1.234567890"
        mock_order.selection_id = 55555

        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="test_existing_001",
                    market_id="1.234567890",
                    selection_id=55555,
                )
            ]
        )
        result: DecisionResult = decide(selections, current_orders=[mock_order])

        # Should generate order - executor handles duplicates
        assert len(result.orders) == 1

    def test_generates_order_when_no_current_orders(self):
        """Generate order when current_orders is empty."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="new_selection",
                    market_id="1.234567890",
                    selection_id=55555,
                )
            ]
        )
        result: DecisionResult = decide(selections, current_orders=[])

        assert len(result.orders) == 1

    def test_generates_order_with_completed_order_present(self):
        """Generate order when existing order is already complete."""
        from unittest.mock import MagicMock

        mock_order = MagicMock()
        mock_order.customer_strategy_ref = "test_complete"
        mock_order.execution_status = "EXECUTION_COMPLETE"
        mock_order.market_id = "1.234567890"
        mock_order.selection_id = 55555

        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="test_complete",
                    market_id="1.234567890",
                    selection_id=55555,
                )
            ]
        )
        result: DecisionResult = decide(selections, current_orders=[mock_order])

        assert len(result.orders) == 1


class TestCashedOutSilence:
    """Already cashed out selections should not spam logs."""

    def test_cashed_out_no_invalidation_recorded(self):
        """Cashed Out selections should not add to invalidations."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="already_cashed",
                    valid=False,
                    invalidated_reason="Cashed Out",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Should not add another invalidation
        assert len(result.invalidations) == 0
        assert len(result.orders) == 0

    def test_manual_cash_out_records_invalidation(self):
        """Manual Cash Out is the trigger, should record invalidation."""
        selections: list[SelectionState] = selection_states_list(
            [
                make_selection_state(
                    unique_id="manual_void",
                    valid=False,
                    invalidated_reason="Manual Cash Out",
                )
            ]
        )
        result: DecisionResult = decide(selections)

        # Manual Cash Out should record invalidation (it's the trigger, not the result)
        assert len(result.invalidations) == 1
        assert result.invalidations[0][0] == "manual_void"
        assert len(result.orders) == 0
