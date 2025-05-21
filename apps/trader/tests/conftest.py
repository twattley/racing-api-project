import pandas as pd
import pytest
from api_helpers.clients.betfair_client import BetFairOrder


class TestS3Client:
    def __init__(self):
        self.stored_data = []

    def store_data(self, data: pd.DataFrame, object_path: str):
        self.stored_data.append({"object_path": object_path, "data": data})


class TestBetfairClient:
    def __init__(self, cashed_out_data):
        self.cash_out_market_ids = []
        self.placed_orders = []
        self.cashed_out_data = cashed_out_data

    def cash_out_bets(self, market_ids: list[str]):
        self.cash_out_market_ids.append(list(market_ids))
        return self.cashed_out_data

    def place_order(self, betfair_order: BetFairOrder):
        self.placed_orders.append(betfair_order)


@pytest.fixture
def get_betfair_client():
    """Returns a factory function that creates a mock Betfair client."""

    def _get_betfair_client(cashed_out_data=None):
        return TestBetfairClient(cashed_out_data=cashed_out_data)

    return _get_betfair_client


@pytest.fixture
def get_s3_client():
    """Returns a factory function that creates a mock S3 client."""

    def _get_s3_client():
        return TestS3Client()

    return _get_s3_client


@pytest.fixture
def now_timestamp_fixture() -> pd.Timestamp:
    """Provides a fixed timestamp for 'now'."""
    return pd.Timestamp("2025-01-01 13:00:00", tz="Europe/London")


@pytest.fixture
def set_stake_size():
    """Fixture to set the stake size for testing."""
    return 10.0
