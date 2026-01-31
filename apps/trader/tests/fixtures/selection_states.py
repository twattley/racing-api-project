"""
Fixtures for v_selection_state view output.

These represent the rows returned by the view - the single input to the decision engine.
Each fixture is a dict that matches the view columns.
"""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from trader.models import SelectionState, SelectionType, MarketType

# Early bird cutoff - must match bet_store.EARLY_BIRD_CUTOFF_HOURS
EARLY_BIRD_CUTOFF_HOURS = 2


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
    # Derived
    has_bet: bool = False,
    fully_matched: bool = False,
    # Calculated stake (from staking tiers)
    calculated_stake: float = 40.0,
    # Minutes to race (derived from race_time)
    minutes_to_race: float = 60.0,
    # Early bird expiry (computed from race_time, can override)
    expires_at: datetime = None,
    # Short price removal flag
    short_price_removed: bool = False,
    # Place terms changed (8→<8 runners)
    place_terms_changed: bool = False,
    # Execution flags
    use_fill_or_kill: bool = False,
    within_stake_limit: bool = True,
    # Liability tracking
    total_liability: float = 0.0,
    # Cash out requested (manual void with matched money)
    cash_out_requested: bool = False,
) -> dict[str, Any]:
    """Create a single selection state row (view output)."""

    if race_time is None:
        race_time = datetime.now() + timedelta(hours=1)
    if race_date is None:
        race_date = datetime.now().date()
    if expires_at is None:
        expires_at = race_time - timedelta(hours=EARLY_BIRD_CUTOFF_HOURS)

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
        "has_bet": has_bet,
        "fully_matched": fully_matched,
        "calculated_stake": calculated_stake,
        "minutes_to_race": minutes_to_race,
        "expires_at": expires_at,
        "short_price_removed": short_price_removed,
        "place_terms_changed": place_terms_changed,
        "use_fill_or_kill": use_fill_or_kill,
        "within_stake_limit": within_stake_limit,
        "total_liability": total_liability,
        "cash_out_requested": cash_out_requested,
    }


def selection_state_df(rows: list[dict]) -> pd.DataFrame:
    """Convert list of selection state dicts to DataFrame."""
    return pd.DataFrame(rows)


def to_selection_state(row: dict) -> SelectionState:
    """Convert a selection state dict to a SelectionState object."""
    return SelectionState(
        unique_id=row["unique_id"],
        race_id=row["race_id"],
        race_time=row["race_time"],
        race_date=row["race_date"],
        horse_id=row["horse_id"],
        horse_name=row["horse_name"],
        selection_type=SelectionType(row["selection_type"]),
        market_type=MarketType(row["market_type"]),
        requested_odds=float(row["requested_odds"]),
        stake_points=float(row.get("stake_points", 1.0) or 1.0),
        market_id=str(row["market_id"]),
        selection_id=int(row["selection_id"]),
        valid=bool(row["valid"]),
        invalidated_reason=row.get("invalidated_reason"),
        original_runners=int(row.get("original_runners", 0) or 0),
        original_price=float(row.get("original_price", 0) or 0),
        current_back_price=row.get("current_back_price"),
        current_lay_price=row.get("current_lay_price"),
        runner_status=row.get("runner_status", "ACTIVE") or "ACTIVE",
        current_runners=int(row.get("current_runners", 0) or 0),
        total_matched=float(row.get("total_matched", 0) or 0),
        total_liability=float(row.get("total_liability", 0) or 0),
        bet_count=int(row.get("bet_count", 0) or 0),
        has_bet=bool(row.get("has_bet", False)),
        fully_matched=bool(row.get("fully_matched", False)),
        calculated_stake=float(row.get("calculated_stake", 0) or 0),
        minutes_to_race=float(row.get("minutes_to_race", 60) or 60),
        expires_at=row["expires_at"],
        short_price_removed=bool(row.get("short_price_removed", False)),
        place_terms_changed=bool(row.get("place_terms_changed", False)),
        cash_out_requested=bool(row.get("cash_out_requested", False)),
        use_fill_or_kill=bool(row.get("use_fill_or_kill", False)),
        within_stake_limit=bool(row.get("within_stake_limit", True)),
    )


def selection_states_list(rows: list[dict]) -> list[SelectionState]:
    """Convert list of selection state dicts to list of SelectionState objects."""
    return [to_selection_state(row) for row in rows]


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
        place_terms_changed=True,  # Computed by view
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
        place_terms_changed=False,  # WIN bets not affected
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


def fill_or_kill_imminent() -> dict:
    """Race < 2 mins away - should use fill-or-kill."""
    return make_selection_state(
        unique_id="fok_001",
        race_time=datetime.now() + timedelta(minutes=1),
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        minutes_to_race=1.0,
        use_fill_or_kill=True,
    )


def normal_order_time() -> dict:
    """Race > 2 mins away - normal order."""
    return make_selection_state(
        unique_id="normal_001",
        race_time=datetime.now() + timedelta(minutes=30),
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        minutes_to_race=30.0,
        use_fill_or_kill=False,
    )


def exceeded_stake_limit_back() -> dict:
    """BACK bet that has exceeded max stake limit."""
    return make_selection_state(
        unique_id="exceeded_back_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        total_matched=100.0,  # Already exceeded
        within_stake_limit=False,
    )


def exceeded_stake_limit_lay() -> dict:
    """LAY bet that has exceeded max liability limit."""
    return make_selection_state(
        unique_id="exceeded_lay_001",
        selection_type="LAY",
        market_type="WIN",
        requested_odds=3.0,
        current_lay_price=3.0,
        total_liability=100.0,  # Already exceeded
        within_stake_limit=False,
    )


def within_stake_limit_back() -> dict:
    """BACK bet within stake limit."""
    return make_selection_state(
        unique_id="within_back_001",
        selection_type="BACK",
        market_type="WIN",
        requested_odds=3.0,
        current_back_price=3.0,
        total_matched=10.0,
        within_stake_limit=True,
    )
