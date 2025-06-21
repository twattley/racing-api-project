import pandas as pd
import pytest
from pathlib import Path
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.clients.postgres_client import PostgresClient
from trader.market_trader import MarketTrader
from trader.utils import load_staking_config


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
        self.cumulative_totals = {}
        self.existing_positions = {}  # Track existing positions by strategy_id

    def cash_out_bets(self, market_ids: list[str]):
        self.cash_out_market_ids.append(list(market_ids))
        return self.cash_out_market_ids

    def place_order(self, betfair_order: BetFairOrder):
        self.placed_orders.append(betfair_order)

        strategy_id = betfair_order.strategy
        if strategy_id not in self.cumulative_totals:
            self.cumulative_totals[strategy_id] = {
                "total_size": 0.0,
                "total_value": 0.0,
            }

        current_total = self.cumulative_totals[strategy_id]
        new_total_size = current_total["total_size"] + betfair_order.size

        # Calculate value differently for BACK vs LAY bets
        if betfair_order.side == "LAY":
            # For LAY bets, track liability: size * (price - 1)
            new_value_contribution = betfair_order.size * (betfair_order.price - 1)
            new_total_value = current_total["total_value"] + new_value_contribution
            # Average price for LAY = (total_liability / total_size) + 1
            average_price = (
                (new_total_value / new_total_size) + 1
                if new_total_size > 0
                else betfair_order.price
            )
        else:
            # For BACK bets, track total value: size * price
            new_value_contribution = betfair_order.size * betfair_order.price
            new_total_value = current_total["total_value"] + new_value_contribution
            # Average price for BACK = total_value / total_size
            average_price = (
                new_total_value / new_total_size
                if new_total_size > 0
                else betfair_order.price
            )

        self.cumulative_totals[strategy_id] = {
            "total_size": new_total_size,
            "total_value": new_total_value,
        }

        return OrderResult(
            success=True,
            message="Test Bet Placed",
            size_matched=new_total_size,
            average_price_matched=round(average_price, 2),
        )

    def set_existing_position(
        self, strategy_id: str, size: float, price: float, side: str
    ):
        """Initialize existing position for cumulative calculations"""
        if side == "LAY":
            # For LAY bets, track liability
            total_value = size * (price - 1)
        else:
            # For BACK bets, track total value
            total_value = size * price

        self.cumulative_totals[strategy_id] = {
            "total_size": size,
            "total_value": total_value,
        }


@pytest.fixture
def postgres_client() -> PostgresClient:
    """Returns a mock Postgres client instance."""
    return TestPostgresClient()


@pytest.fixture
def betfair_client() -> BetFairClient:
    """Returns a mock Betfair client instance."""
    return TestBetfairClient()


@pytest.fixture
def now_timestamp_fixture() -> pd.Timestamp:
    """Provides a fixed timestamp for 'now'."""
    return pd.Timestamp("2025-01-01 13:00:00", tz="Europe/London")


@pytest.fixture
def market_trader(postgres_client, betfair_client) -> MarketTrader:
    """Returns a MarketTrader instance configured with test staking config."""
    # Get the path to the test config relative to the project root

    test_staking_config = load_staking_config(test_config=True)
    return MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
        staking_config=test_staking_config,
    )
