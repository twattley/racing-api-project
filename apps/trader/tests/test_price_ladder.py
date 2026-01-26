"""Tests for Betfair price ladder utility."""

from trader.price_ladder import LADDER, PriceLadder, ladder


class TestLadderGeneration:
    """Test the ladder is generated correctly."""

    def test_ladder_starts_at_1_01(self):
        assert LADDER[0] == 1.01

    def test_ladder_ends_at_20(self):
        assert LADDER[-1] == 20.0

    def test_ladder_has_correct_length(self):
        # 1.01-2.00: 100 prices (0.01 increments)
        # 2.02-3.00: 50 prices (0.02 increments)
        # 3.05-4.00: 20 prices (0.05 increments)
        # 4.10-6.00: 20 prices (0.10 increments)
        # 6.20-10.00: 20 prices (0.20 increments)
        # 10.50-20.00: 20 prices (0.50 increments)
        assert len(LADDER) == 230

    def test_2_00_in_ladder(self):
        assert 2.0 in LADDER

    def test_2_01_not_in_ladder(self):
        assert 2.01 not in LADDER

    def test_3_03_not_in_ladder(self):
        assert 3.03 not in LADDER

    def test_3_05_in_ladder(self):
        assert 3.05 in LADDER


class TestIsValid:
    """Test price validation."""

    def test_valid_prices(self):
        valid = [1.01, 1.50, 2.00, 2.02, 3.00, 3.05, 4.00, 5.00, 6.00, 10.00, 20.00]
        for price in valid:
            assert ladder.is_valid(price), f"{price} should be valid"

    def test_invalid_prices(self):
        invalid = [1.001, 2.01, 2.03, 3.01, 3.03, 4.05, 5.05, 6.10, 10.20]
        for price in invalid:
            assert not ladder.is_valid(price), f"{price} should be invalid"


class TestSnap:
    """Test snapping to valid prices."""

    def test_snap_already_valid(self):
        assert ladder.snap(3.00) == 3.00

    def test_snap_rounds_to_nearest(self):
        assert ladder.snap(3.03) == 3.05  # closer to 3.05 than 3.00

    def test_snap_rounds_down_when_closer(self):
        assert ladder.snap(3.01) == 3.00  # closer to 3.00 than 3.05

    def test_snap_below_min(self):
        assert ladder.snap(0.5) == 1.01

    def test_snap_above_max(self):
        assert ladder.snap(100.0) == 20.0


class TestSnapDown:
    """Test snapping down to valid prices."""

    def test_snap_down_already_valid(self):
        assert ladder.snap_down(3.00) == 3.00

    def test_snap_down_to_lower(self):
        assert ladder.snap_down(3.03) == 3.00

    def test_snap_down_3_04(self):
        assert ladder.snap_down(3.04) == 3.00


class TestSnapUp:
    """Test snapping up to valid prices."""

    def test_snap_up_already_valid(self):
        assert ladder.snap_up(3.00) == 3.00

    def test_snap_up_to_higher(self):
        assert ladder.snap_up(3.01) == 3.05

    def test_snap_up_3_03(self):
        assert ladder.snap_up(3.03) == 3.05


class TestTicksAway:
    """Test moving ticks on the ladder."""

    def test_ticks_up_from_3_00(self):
        # 3.00 → 3.05 → 3.10 → 3.15 → 3.20
        assert ladder.ticks_away(3.00, 4) == 3.20

    def test_ticks_down_from_3_00(self):
        # 3.00 → 2.98 → 2.96
        assert ladder.ticks_away(3.00, -2) == 2.96

    def test_ticks_from_invalid_price_snaps_first(self):
        # 3.03 snaps to 3.05, then +2 = 3.15
        assert ladder.ticks_away(3.03, 2) == 3.15

    def test_ticks_clamped_at_min(self):
        assert ladder.ticks_away(1.01, -100) == 1.01

    def test_ticks_clamped_at_max(self):
        assert ladder.ticks_away(20.0, 100) == 20.0

    def test_zero_ticks_returns_snapped_price(self):
        assert ladder.ticks_away(3.00, 0) == 3.00


class TestTicksBetween:
    """Test counting ticks between prices."""

    def test_same_price_is_zero(self):
        assert ladder.ticks_between(3.00, 3.00) == 0

    def test_one_tick_apart(self):
        assert ladder.ticks_between(3.00, 3.05) == 1

    def test_negative_when_lower(self):
        assert ladder.ticks_between(3.05, 3.00) == -1

    def test_multiple_ticks(self):
        # 3.00 → 3.05 → 3.10 → 3.15 → 3.20 = 4 ticks
        assert ladder.ticks_between(3.00, 3.20) == 4


class TestModuleLevelInstance:
    """Test the module-level ladder instance."""

    def test_module_instance_works(self):
        assert ladder.ticks_away(2.0, 1) == 2.02
