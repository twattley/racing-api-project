"""
Fixtures for v_selection_state view output.

These represent the rows returned by the view - the single input to the decision engine.
Each fixture is a dict that matches the view columns.
"""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd


def make_selection_state(
    # Identity
    unique_id: str = "test_selection_001",
    race_id: int = 12345,
    race_time: datetime = None,
    race_date: str = None,
    horse_id: int = 1001,
    horse_name: str = "Test Horse",
    # Bet details
    selection_type: str = "BACK",  # BACK / LAY
    market_type: str = "WIN",  # WIN / PLACE
    requested_odds: float = 3.0,
    stake_points: float = 1.0,
    # Betfair identifiers
    market_id: str = "1.234567890",
    selection_id: int = 55555,
    # Validation state
    valid: bool = True,
    invalidated_reason: str = None,
    # Original market snapshot
    original_runners: int = 10,
    original_price: float = 3.0,
    # Current live prices
    current_back_price: float = 3.0,
    current_lay_price: float = 3.2,
    # Runner status
    runner_status: str = "ACTIVE",  # ACTIVE / REMOVED
    current_runners: int = 10,
    # Betting progress
    total_matched: float = 0.0,
    bet_count: int = 0,
    latest_bet_status: str = None,
    latest_expires_at: datetime = None,
    # Derived
    has_bet: bool = False,
    fully_matched: bool = False,
    # Calculated stake (from staking tiers)
    calculated_stake: float = 40.0,
    # Minutes to race (derived from race_time)
    minutes_to_race: float = 60.0,
    # Strategy reference
    customer_strategy_ref: str = "trader",
) -> dict[str, Any]:
    """Create a single selection state row (view output)."""

    if race_time is None:
        race_time = datetime.now() + timedelta(hours=1)
    if race_date is None:
        race_date = datetime.now().date()

    return {
        "unique_id": unique_id,
        "race_id": race_id,
        "race_time": race_time,
        "race_date": race_date,
        "horse_id": horse_id,
        "horse_name": horse_name,
        "selection_type": selection_type,
        "market_type": market_type,
        "requested_odds": requested_odds,
        "stake_points": stake_points,
        "market_id": market_id,
        "selection_id": selection_id,
        "valid": valid,
        "invalidated_reason": invalidated_reason,
        "original_runners": original_runners,
        "original_price": original_price,
        "current_back_price": current_back_price,
        "current_lay_price": current_lay_price,
        "runner_status": runner_status,
        "current_runners": current_runners,
        "total_matched": total_matched,
        "bet_count": bet_count,
        "latest_bet_status": latest_bet_status,
        "latest_expires_at": latest_expires_at,
        "has_bet": has_bet,
        "fully_matched": fully_matched,
        "calculated_stake": calculated_stake,
        "minutes_to_race": minutes_to_race,
        "customer_strategy_ref": customer_strategy_ref,
    }


def selection_state_df(rows: list[dict]) -> pd.DataFrame:
    """Convert list of selection state dicts to DataFrame."""
    return pd.DataFrame(rows)


# ============================================================================
# PRESET SCENARIOS
# ============================================================================


def valid_back_win_no_bet() -> dict:
    """Valid BACK WIN selection, no bets placed yet, price matches."""
    return make_selection_state(
        unique_id="back_win_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        original_runners=10,
        current_runners=10,
        has_bet=False,
        total_matched=0.0,
    )


def valid_lay_win_no_bet() -> dict:
    """Valid LAY WIN selection, no bets placed yet."""
    return make_selection_state(
        unique_id="lay_win_001",
        selection_type="LAY",
        market_type="WIN",
        requested_odds=3.0,
        current_lay_price=3.0,
        original_runners=10,
        current_runners=10,
        has_bet=False,
    )


def valid_back_place_no_bet() -> dict:
    """Valid BACK PLACE selection, no bets placed yet."""
    return make_selection_state(
        unique_id="back_place_001",
        selection_type="BACK",
        market_type="PLACE",
        requested_odds=2.5,
        current_back_price=2.5,
        original_runners=10,
        current_runners=10,
        has_bet=False,
    )


def eight_to_seven_place_invalid() -> dict:
    """PLACE bet that should be invalidated: 8 runners → 7."""
    return make_selection_state(
        unique_id="place_8to7_001",
        selection_type="BACK",
        market_type="PLACE",
        requested_odds=2.5,
        current_back_price=2.5,
        original_runners=8,
        current_runners=7,  # Runner removed!
        has_bet=False,
    )


def eight_to_seven_win_valid() -> dict:
    """WIN bet with 8→7 runners: should still be valid (only PLACE affected)."""
    return make_selection_state(
        unique_id="win_8to7_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        original_runners=8,
        current_runners=7,
        has_bet=False,
    )


def short_price_removed() -> dict:
    """Horse with price < 12 removed from market - invalidates all bets."""
    return make_selection_state(
        unique_id="short_removed_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        original_runners=10,
        current_runners=9,
        original_price=8.0,  # Short price horse
        runner_status="REMOVED",
    )


def partially_matched() -> dict:
    """Selection with partial match - should continue betting."""
    return make_selection_state(
        unique_id="partial_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        has_bet=True,
        bet_count=1,
        total_matched=25.0,  # Half matched
        latest_bet_status="LIVE",
        fully_matched=False,
    )


def fully_matched() -> dict:
    """Selection fully matched - no more betting needed."""
    return make_selection_state(
        unique_id="full_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        has_bet=True,
        bet_count=2,
        total_matched=50.0,
        latest_bet_status="MATCHED",
        fully_matched=True,
    )


def price_drifted_back() -> dict:
    """BACK bet where price has drifted above requested - should not bet."""
    return make_selection_state(
        unique_id="drift_back_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.5,  # Drifted out
    )


def price_drifted_lay() -> dict:
    """LAY bet where price has drifted below requested - should not bet."""
    return make_selection_state(
        unique_id="drift_lay_001",
        selection_type="LAY",
        market_type="WIN",
        requested_odds=3.0,
        current_lay_price=2.5,  # Drifted in
    )


def already_invalid() -> dict:
    """Selection already marked invalid."""
    return make_selection_state(
        unique_id="invalid_001",
        valid=False,
        invalidated_reason="Previously invalidated",
    )


def race_imminent() -> dict:
    """Race starting very soon - max stake tier."""
    return make_selection_state(
        unique_id="imminent_001",
        race_time=datetime.now() + timedelta(minutes=5),
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
    )


def race_hours_away() -> dict:
    """Race hours away - min stake tier."""
    return make_selection_state(
        unique_id="hours_away_001",
        race_time=datetime.now() + timedelta(hours=10),
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
    )
