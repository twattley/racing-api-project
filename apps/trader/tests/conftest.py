import pandas as pd
import pytest
from api_helpers.clients.betfair_client import BetFairOrder, OrderResult


class TestPostgresClient:
    def __init__(self):
        self.stored_data = None

    def store_latest_data(
        self,
        data: pd.DataFrame,
        schema: str = None,
        table: str = None,
        unique_columns: list = None,
        *args,
        **kwargs
    ):
        self.stored_data = data


class TestBetfairClient:
    def __init__(self):
        self.cash_out_market_ids = []
        self.placed_orders = []

    def cash_out_bets(self, market_ids: list[str]):
        self.cash_out_market_ids.append(list(market_ids))
        return self.cash_out_market_ids

    def place_order(self, betfair_order: BetFairOrder):
        self.placed_orders.append(betfair_order)
        return OrderResult(success=True, message="Test Bet Placed")


@pytest.fixture
def postgres_client():
    """Returns a mock Postgres client instance."""
    return TestPostgresClient()


@pytest.fixture
def betfair_client():
    """Returns a mock Betfair client instance."""
    return TestBetfairClient()


@pytest.fixture
def now_timestamp_fixture() -> pd.Timestamp:
    """Provides a fixed timestamp for 'now'."""
    return pd.Timestamp("2025-01-01 13:00:00", tz="Europe/London")


@pytest.fixture
def set_stake_size():
    """Fixture to set the stake size for testing."""
    return 10.0
