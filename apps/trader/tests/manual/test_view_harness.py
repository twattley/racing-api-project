"""
Manual test harness for v_selection_state view.

Run this script to seed test data and query the view.
Tweak values and re-run to verify behavior.

Usage:
    python -m tests.manual.test_view_harness
"""

from datetime import datetime, timedelta

import pandas as pd
from api_helpers.clients.postgres_client import PostgresClient, PsqlConnection

# ============================================================================
# CONNECTION
# ============================================================================


def get_client() -> PostgresClient:
    """Get a postgres client using environment variables."""
    return PostgresClient(
        connection=PsqlConnection(
            user="postgres",
            password="test",
            host="localhost",
            port=5432,
            db="racing-api",
        ),
    )


# ============================================================================
# CLEAR DATA
# ============================================================================


def clear_test_data(client: PostgresClient, clear_prices: bool = False):
    """Clear test tables. Be careful!"""
    client.execute_query("TRUNCATE live_betting.bet_log CASCADE")
    client.execute_query("DELETE FROM live_betting.market_state")
    client.execute_query("DELETE FROM live_betting.selections")
    print("✓ Cleared bet_log, market_state, selections")

    if clear_prices:
        client.execute_query("DELETE FROM live_betting.betfair_prices")
        print("✓ Cleared updated_price_data")


# ============================================================================
# SEED TEST DATA
# ============================================================================


def seed_price_data(client: PostgresClient, rows: list[dict] = None):
    """Seed updated_price_data with test horses."""
    if rows is None:
        # Default test data - 10 runners in a race
        race_time = datetime.now() + timedelta(hours=1)
        market_id = "1.123456789"

        rows = []
        for i in range(10):
            rows.append(
                {
                    "unique_id": f"price_{i:03d}",
                    "race_time": race_time,
                    "race_date": datetime.now().date(),
                    "course": "Test Course",
                    "horse_name": f"Test Horse {i+1}",
                    "selection_id": 10000 + i,
                    "status": "ACTIVE",
                    "current_runner_count": 10,
                    "market_id_win": market_id,
                    "market_id_place": f"1.{123456790 + i}",
                    "back_price_1_win": 3.0 + (i * 0.5),
                    "lay_price_1_win": 3.2 + (i * 0.5),
                    "back_price_1_place": 1.5 + (i * 0.2),
                    "lay_price_1_place": 1.6 + (i * 0.2),
                }
            )

    df = pd.DataFrame(rows)
    client.store_data(df, table="updated_price_data", schema="live_betting")
    print(f"✓ Seeded {len(rows)} rows to updated_price_data")
    return df


def seed_selection(
    client: PostgresClient,
    unique_id: str = "test_001",
    horse_name: str = "Test Horse 1",
    selection_type: str = "BACK",
    market_type: str = "WIN",
    market_id: str = None,  # Auto-set based on market_type if not provided
    selection_id: int = 10000,
    requested_odds: float = 3.0,
    stake_points: float = 1.0,
    valid: bool = True,
    fully_matched: bool = False,
    race_time: datetime = None,
) -> pd.DataFrame:
    """Seed a single selection."""
    if race_time is None:
        race_time = datetime.now() + timedelta(hours=1)

    # Default market IDs based on market type
    if market_id is None:
        market_id = "1.123456789" if market_type == "WIN" else "1.123456790"

    row = {
        "unique_id": unique_id,
        "race_id": 12345,
        "race_time": race_time,
        "race_date": datetime.now().date(),
        "horse_id": selection_id,
        "horse_name": horse_name,
        "selection_type": selection_type,
        "market_type": market_type,
        "market_id": market_id,
        "selection_id": selection_id,
        "requested_odds": requested_odds,
        "stake_points": stake_points,
        "valid": valid,
        "fully_matched": fully_matched,
    }

    df = pd.DataFrame([row])
    client.store_data(df, table="selections", schema="live_betting")
    print(
        f"✓ Seeded selection: {unique_id} ({selection_type} {market_type} @ {requested_odds})"
    )
    return df


def seed_market_state(
    client: PostgresClient,
    unique_id: str = "test_001",
    selection_id: int = 10000,
    market_id_win: str = "1.123456789",
    market_id_place: str = "1.123456790",
    number_of_runners: int = 10,
    back_price_win: float = 3.0,
    race_time: datetime = None,
) -> pd.DataFrame:
    """Seed market state snapshot."""
    if race_time is None:
        race_time = datetime.now() + timedelta(hours=1)

    row = {
        "unique_id": unique_id,
        "selection_id": selection_id,
        "horse_id": selection_id,
        "race_id": 12345,
        "race_date": datetime.now().date(),
        "race_time": race_time,
        "market_id_win": market_id_win,
        "market_id_place": market_id_place,
        "number_of_runners": number_of_runners,
        "back_price_win": back_price_win,
    }

    df = pd.DataFrame([row])
    client.store_data(df, table="market_state", schema="live_betting")
    print(f"✓ Seeded market_state: {unique_id} ({number_of_runners} runners)")
    return df


def seed_bet_log(
    client: PostgresClient,
    selection_unique_id: str = "test_001",
    bet_id: str = "BET-000001",
    market_id: str = "1.123456789",
    selection_id: int = 10000,
    side: str = "BACK",
    requested_price: float = 3.0,
    requested_size: float = 36.0,
    matched_size: float = 0.0,
    status: str = "PLACED",
) -> pd.DataFrame:
    """Seed a bet log entry."""
    row = {
        "selection_unique_id": selection_unique_id,
        "bet_id": bet_id,
        "market_id": market_id,
        "selection_id": selection_id,
        "side": side,
        "requested_price": requested_price,
        "requested_size": requested_size,
        "matched_size": matched_size,
        "status": status,
        "placed_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(minutes=5),
    }

    df = pd.DataFrame([row])
    client.store_data(df, table="bet_log", schema="live_betting")
    print(f"✓ Seeded bet_log: {bet_id} ({side} £{requested_size} @ {requested_price})")
    return df


# ============================================================================
# QUERY VIEW
# ============================================================================


def query_view(client: PostgresClient) -> pd.DataFrame:
    """Query v_selection_state and return results."""
    df = client.fetch_data("SELECT * FROM live_betting.v_selection_state")
    return df


def show_view(client: PostgresClient):
    """Query and pretty-print the view."""
    df = query_view(client)

    print(f"\n{'='*80}")
    print(f"VIEW RESULTS: {len(df)} rows")
    print(f"{'='*80}")

    if df.empty:
        print("(no rows)")
        return df

    # Show key columns in a readable format
    key_cols = [
        "unique_id",
        "horse_name",
        "selection_type",
        "market_type",
        "requested_odds",
        "current_back_price",
        "current_lay_price",
        "original_runners",
        "current_runners",
        "has_bet",
        "total_matched",
        "calculated_stake",
        "valid",
        "minutes_to_race",
    ]
    display_cols = [c for c in key_cols if c in df.columns]

    # Print each row vertically for readability
    for idx, row in df.iterrows():
        print(f"\n--- Row {idx + 1} ---")
        for col in display_cols:
            val = row[col]
            if isinstance(val, float):
                val = f"{val:.2f}"
            print(f"  {col:25} : {val}")

    print(f"\n{'='*80}")
    return df


# ============================================================================
# UPDATE HELPERS
# ============================================================================


def update_price_data(client: PostgresClient, selection_id: int, **updates):
    """Update a row in updated_price_data."""
    set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
    query = f"""
        UPDATE live_betting.betfair_prices 
        SET {set_clauses}
        WHERE selection_id = :selection_id
    """
    params = {"selection_id": selection_id, **updates}
    client.execute_query(query, params)
    print(f"✓ Updated price_data for selection_id={selection_id}: {updates}")


def update_selection(client: PostgresClient, unique_id: str, **updates):
    """Update a selection."""
    set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
    query = f"""
        UPDATE live_betting.selections 
        SET {set_clauses}
        WHERE unique_id = :unique_id
    """
    params = {"unique_id": unique_id, **updates}
    client.execute_query(query, params)
    print(f"✓ Updated selection {unique_id}: {updates}")


# ============================================================================
# TEST SCENARIOS
# ============================================================================


def scenario_basic_back_win(client: PostgresClient):
    """Basic BACK WIN bet - should show calculated_stake."""
    print("\n" + "=" * 60)
    print("SCENARIO: Basic BACK WIN")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)
    seed_price_data(client)
    seed_selection(client, selection_type="BACK", market_type="WIN", requested_odds=3.0)
    seed_market_state(client, number_of_runners=10)

    return show_view(client)


def scenario_8_to_7_place(client: PostgresClient):
    """8→7 runners for PLACE bet - decision engine should invalidate."""
    print("\n" + "=" * 60)
    print("SCENARIO: 8→7 Runners (PLACE bet)")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)

    # Create 8 runners, then mark one as removed
    race_time = datetime.now() + timedelta(hours=1)
    market_id = "1.123456789"

    rows = []
    for i in range(8):
        rows.append(
            {
                "unique_id": f"price_{i:03d}",
                "race_time": race_time,
                "race_date": datetime.now().date(),
                "course": "Test Course",
                "horse_name": f"Test Horse {i+1}",
                "selection_id": 10000 + i,
                "status": "ACTIVE" if i < 7 else "REMOVED",  # Last one removed
                "current_runner_count": 7,  # Now 7 runners
                "market_id_win": market_id,
                "market_id_place": f"1.{123456790 + i}",
                "back_price_1_win": 3.0,
                "lay_price_1_win": 3.2,
                "back_price_1_place": 1.5,
                "lay_price_1_place": 1.6,
            }
        )

    seed_price_data(client, rows)
    seed_selection(
        client, selection_type="BACK", market_type="PLACE", requested_odds=1.5
    )
    seed_market_state(client, number_of_runners=8)  # ORIGINAL was 8

    print("\n→ EXPECTED: original_runners=8, current_runners=7, market_type=PLACE")
    print("→ Decision engine should INVALIDATE this")
    return show_view(client)


def scenario_partially_matched(client: PostgresClient):
    """Bet partially matched - should continue betting."""
    print("\n" + "=" * 60)
    print("SCENARIO: Partially Matched")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)
    seed_price_data(client)
    seed_selection(client)
    seed_market_state(client)
    seed_bet_log(client, matched_size=20.0, status="LIVE")

    print("\n→ EXPECTED: has_bet=True, total_matched=20.0")
    print("→ Decision engine should continue if price still good")
    return show_view(client)


def scenario_lay_bet(client: PostgresClient):
    """LAY bet - should use lay price and lay stake (liability)."""
    print("\n" + "=" * 60)
    print("SCENARIO: LAY Bet")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)
    seed_price_data(client)
    seed_selection(client, selection_type="LAY", market_type="WIN", requested_odds=3.2)
    seed_market_state(client, number_of_runners=10)

    print("\n→ EXPECTED: selection_type=LAY, calculated_stake based on max_lay (75)")
    print("→ Decision engine should use current_lay_price for comparison")
    return show_view(client)


def scenario_back_price_drifted(client: PostgresClient):
    """BACK bet where price drifted worse (lower) - should skip."""
    print("\n" + "=" * 60)
    print("SCENARIO: BACK Price Drifted (Worse)")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)

    # Seed price data with back price at 2.5 (worse than our 3.0 target)
    race_time = datetime.now() + timedelta(hours=1)
    rows = [
        {
            "unique_id": "price_000",
            "race_time": race_time,
            "race_date": datetime.now().date(),
            "course": "Test Course",
            "horse_name": "Test Horse 1",
            "selection_id": 10000,
            "status": "ACTIVE",
            "current_runner_count": 10,
            "market_id_win": "1.123456789",
            "market_id_place": "1.123456790",
            "back_price_1_win": 2.5,  # WORSE than requested 3.0
            "lay_price_1_win": 2.7,
            "back_price_1_place": 1.5,
            "lay_price_1_place": 1.6,
        }
    ]
    seed_price_data(client, rows)
    seed_selection(client, selection_type="BACK", market_type="WIN", requested_odds=3.0)
    seed_market_state(client, number_of_runners=10)

    print("\n→ EXPECTED: requested_odds=3.0, current_back_price=2.5")
    print("→ Decision engine should SKIP (price too low for BACK)")
    return show_view(client)


def scenario_lay_price_drifted(client: PostgresClient):
    """LAY bet where price drifted worse (higher) - should skip."""
    print("\n" + "=" * 60)
    print("SCENARIO: LAY Price Drifted (Worse)")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)

    # Seed price data with lay price at 4.0 (worse than our 3.0 target)
    race_time = datetime.now() + timedelta(hours=1)
    rows = [
        {
            "unique_id": "price_000",
            "race_time": race_time,
            "race_date": datetime.now().date(),
            "course": "Test Course",
            "horse_name": "Test Horse 1",
            "selection_id": 10000,
            "status": "ACTIVE",
            "current_runner_count": 10,
            "market_id_win": "1.123456789",
            "market_id_place": "1.123456790",
            "back_price_1_win": 3.8,
            "lay_price_1_win": 4.0,  # WORSE than requested 3.0
            "back_price_1_place": 1.5,
            "lay_price_1_place": 1.6,
        }
    ]
    seed_price_data(client, rows)
    seed_selection(client, selection_type="LAY", market_type="WIN", requested_odds=3.0)
    seed_market_state(client, number_of_runners=10)

    print("\n→ EXPECTED: requested_odds=3.0, current_lay_price=4.0")
    print("→ Decision engine should SKIP (price too high for LAY)")
    return show_view(client)


def scenario_already_invalid(client: PostgresClient):
    """Selection already marked invalid - should skip."""
    print("\n" + "=" * 60)
    print("SCENARIO: Already Invalid")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)
    seed_price_data(client)
    seed_selection(client, valid=False)
    seed_market_state(client, number_of_runners=10)

    print("\n→ EXPECTED: valid=False")
    print("→ Decision engine should SKIP")
    return show_view(client)


def scenario_stake_tiers(client: PostgresClient):
    """Test different time-to-race stake tiers."""
    print("\n" + "=" * 60)
    print("SCENARIO: Stake Tiers (Multiple Times)")
    print("=" * 60)

    clear_test_data(client, clear_prices=True)

    # Create multiple selections at different times
    times = [
        (30, "30 mins - max stake"),
        (60, "60 mins"),
        (120, "2 hours"),
        (300, "5 hours"),
        (480, "8 hours - min stake"),
    ]

    race_base = datetime.now()

    for i, (mins, desc) in enumerate(times):
        race_time = race_base + timedelta(minutes=mins)
        unique_id = f"test_{mins:03d}"

        # Seed price data for this selection
        rows = [
            {
                "unique_id": f"price_{mins:03d}",
                "race_time": race_time,
                "race_date": datetime.now().date(),
                "course": "Test Course",
                "horse_name": f"Horse {mins}min",
                "selection_id": 10000 + i,
                "status": "ACTIVE",
                "current_runner_count": 10,
                "market_id_win": f"1.{123456789 + i}",
                "market_id_place": f"1.{223456789 + i}",
                "back_price_1_win": 3.0,
                "lay_price_1_win": 3.2,
                "back_price_1_place": 1.5,
                "lay_price_1_place": 1.6,
            }
        ]

        df = pd.DataFrame(rows)
        client.store_data(df, table="updated_price_data", schema="live_betting")

        seed_selection(
            client,
            unique_id=unique_id,
            horse_name=f"Horse {mins}min",
            market_id=f"1.{123456789 + i}",
            selection_id=10000 + i,
            race_time=race_time,
        )
        seed_market_state(
            client,
            unique_id=unique_id,
            selection_id=10000 + i,
            market_id_win=f"1.{123456789 + i}",
            race_time=race_time,
        )
        print(f"  → {desc}")

    print("\n→ EXPECTED: Different calculated_stake for each time tier")
    return show_view(client)


def run_all_scenarios(client: PostgresClient):
    """Run all test scenarios."""
    scenario_basic_back_win(client)
    scenario_lay_bet(client)
    scenario_8_to_7_place(client)
    scenario_partially_matched(client)
    scenario_back_price_drifted(client)
    scenario_lay_price_drifted(client)
    scenario_already_invalid(client)
    scenario_stake_tiers(client)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    client = get_client()

    # Run a scenario
    scenario_basic_back_win(client)

    # Or run all:
    # run_all_scenarios(client)
