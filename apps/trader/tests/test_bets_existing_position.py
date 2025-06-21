import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

from trader.market_trader import MarketTrader
from .test_helpers import create_single_test_data, assert_dataset_equal
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.clients.betfair_client import BetFairClient

import pytest


def test_back_bet_existing_position_average_improves(
    market_trader: MarketTrader,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """
    Test BACK bet with existing position where the average improves.

    Step 1: Place initial bet of £20 at 3.0
    Step 2: New market conditions allow bet at 2.7, requested_odds = 2.8
    Expected: Additional £30 bet placed, total £50 stake, average price = 2.7
    """

    # Step 1: Establish initial position
    initial_data = create_single_test_data(
        {
            "minutes_to_race": [60],
            "back_price_1": [3.0],
            "back_price_1_depth": [100.0],
            "requested_odds": [3.0],
            "size_matched": [0.0],
            "average_price_matched": [np.nan],
            "size_matched_betfair": [0.0],
            "average_price_matched_betfair": [np.nan],
            "fully_matched": [False],
        }
    )

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=initial_data,
    )

    # Verify first bet
    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=20.0, price=3.0, selection_id=1, market_id="1", side="BACK", strategy="1"
    )
    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [20.0],
                "average_price_matched": [3.0],
                "fully_matched": [False],
            }
        ),
    )

    first_run_data = market_trader.postgres_client.stored_data.copy()

    # Step 2: New market conditions with better price
    second_data = create_single_test_data(
        {
            "minutes_to_race": [10],
            "back_price_1": [2.7],
            "back_price_1_depth": [50.0],
            "requested_odds": [2.8],
            "size_matched": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched": [first_run_data["average_price_matched"].iloc[0]],
            "size_matched_betfair": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched_betfair": [
                first_run_data["average_price_matched"].iloc[0]
            ],
            "fully_matched": [first_run_data["fully_matched"].iloc[0]],
        }
    )

    # Reset clients for second trade
    postgres_client.stored_data = None
    betfair_client.placed_orders = []
    betfair_client.cash_out_market_ids = []

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture + pd.Timedelta(minutes=50),
        requests_data=second_data,
    )

    # Verify second bet
    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=30.0, price=2.7, selection_id=1, market_id="1", side="BACK", strategy="1"
    )
    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "requested_odds": [2.8],
                "valid": [True],
                "size_matched": [50.0],
                "average_price_matched": [2.82],
                "cashed_out": [False],
                "fully_matched": [True],
            }
        ),
    )


def test_back_bet_existing_position_average_worsens(
    market_trader: MarketTrader,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """
    Test BACK bet with existing position where the average would worsen.

    Step 1: Place initial bet of £20 at 3.0
    Step 2: New market conditions only allow bet at 2.2, requested_odds = 2.8
    Expected: No additional bet placed, position unchanged
    """

    # Step 1: Establish initial position
    initial_data = create_single_test_data(
        {
            "minutes_to_race": [60],
            "back_price_1": [3.0],
            "back_price_1_depth": [100.0],
            "requested_odds": [3.0],
            "size_matched": [0.0],
            "average_price_matched": [np.nan],
            "size_matched_betfair": [0.0],
            "average_price_matched_betfair": [np.nan],
            "fully_matched": [False],
        }
    )

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=initial_data,
    )

    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=20.0, price=3.0, selection_id=1, market_id="1", side="BACK", strategy="1"
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "requested_odds": [3.0],
                "size_matched": [20.0],
                "average_price_matched": [3.0],
                "cashed_out": [False],
                "fully_matched": [False],
            }
        ),
    )
    first_run_data = market_trader.postgres_client.stored_data.copy()

    # Step 2: New market conditions with worse price
    second_data = create_single_test_data(
        {
            "minutes_to_race": [10],
            "back_price_1": [2.2],  # Poor price that would worsen average
            "back_price_1_depth": [50.0],
            "requested_odds": [3.0],
            "size_matched": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched": [first_run_data["average_price_matched"].iloc[0]],
            "size_matched_betfair": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched_betfair": [
                first_run_data["average_price_matched"].iloc[0]
            ],
            "fully_matched": [first_run_data["fully_matched"].iloc[0]],
        }
    )

    # Reset clients for second trade
    postgres_client.stored_data = None
    betfair_client.placed_orders = []
    betfair_client.cash_out_market_ids = []

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=second_data,
    )

    # Verify no additional bet placed
    assert not market_trader.betfair_client.placed_orders

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "requested_odds": [3.0],
                "size_matched": [20.0],
                "average_price_matched": [3.0],
                "cashed_out": [False],
                "fully_matched": [False],
            }
        ),
    )


def test_lay_bet_existing_position_average_improves(
    market_trader: MarketTrader,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """
    Test LAY bet with existing position where the average improves.

    Step 1: Place initial LAY bet: £20 staked at 3.0 (liability = 40)
    Step 2: New market conditions allow bet at 2.7, requested_odds = 3.2, target liability = 50
    Expected: Additional ~5.88 stake, total liability = 50, weighted average ≈ 2.93
    """

    initial_data = create_single_test_data(
        {
            "selection_type": ["LAY"],
            "minutes_to_race": [60],
            "lay_price_1": [3.0],
            "lay_price_1_depth": [100.0],
            "requested_odds": [3.0],
            "size_matched": [0.0],
            "average_price_matched": [np.nan],
            "size_matched_betfair": [0.0],
            "average_price_matched_betfair": [np.nan],
            "fully_matched": [False],
        }
    )

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=initial_data,
    )

    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=25.0, price=3.0, selection_id=1, market_id="1", side="LAY", strategy="1"
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [25.0],
                "average_price_matched": [3.0],
                "cashed_out": [False],
                "fully_matched": [False],
            }
        ),
    )

    first_run_data = market_trader.postgres_client.stored_data.copy()

    # Reset clients for second trade
    postgres_client.stored_data = None
    betfair_client.placed_orders = []
    betfair_client.cash_out_market_ids = []

    second_data = create_single_test_data(
        {
            "selection_type": ["LAY"],
            "minutes_to_race": [10],
            "lay_price_1": [2.7],
            "lay_price_1_depth": [50.0],
            "requested_odds": [3.0],
            "size_matched": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched": [first_run_data["average_price_matched"].iloc[0]],
            "size_matched_betfair": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched_betfair": [
                first_run_data["average_price_matched"].iloc[0]
            ],
            "fully_matched": [first_run_data["fully_matched"].iloc[0]],
        }
    )

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=second_data,
    )

    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=14.71, price=2.7, selection_id=1, market_id="1", side="LAY", strategy="1"
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [39.71],
                "average_price_matched": [2.89],
                "cashed_out": [False],
                "fully_matched": [True],
            }
        ),
    )


def test_lay_bet_existing_position_average_worsens(
    market_trader: MarketTrader,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """
    Test LAY bet with existing position where the average would worsen.

    Step 1: Place initial LAY bet: £10 staked at 3.0 (liability = 20)
    Step 2: New market conditions only allow bet at 3.5, requested_odds = 3.2, target liability = 50
    Expected: No additional bet placed (would worsen average)
    """
    initial_data = create_single_test_data(
        {
            "selection_type": ["LAY"],
            "minutes_to_race": [60],
            "lay_price_1": [3.0],
            "lay_price_1_depth": [100.0],
            "requested_odds": [3.0],
            "size_matched": [0.0],
            "average_price_matched": [np.nan],
            "size_matched_betfair": [0.0],
            "average_price_matched_betfair": [np.nan],
            "fully_matched": [False],
        }
    )

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=initial_data,
    )

    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=25.0, price=3.0, selection_id=1, market_id="1", side="LAY", strategy="1"
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [25.0],
                "average_price_matched": [3.0],
                "cashed_out": [False],
                "fully_matched": [False],
            }
        ),
    )

    first_run_data = market_trader.postgres_client.stored_data.copy()

    # Step 2: New market conditions with worse LAY price
    second_data = create_single_test_data(
        {
            "selection_type": ["LAY"],
            "minutes_to_race": [10],
            "lay_price_1": [3.5],  # Worse price that would worsen average
            "lay_price_1_depth": [50.0],
            "requested_odds": [3.0],
            "size_matched": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched": [first_run_data["average_price_matched"].iloc[0]],
            "size_matched_betfair": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched_betfair": [
                first_run_data["average_price_matched"].iloc[0]
            ],
            "fully_matched": [first_run_data["fully_matched"].iloc[0]],
        }
    )

    # Reset clients for second trade
    postgres_client.stored_data = None
    betfair_client.placed_orders = []
    betfair_client.cash_out_market_ids = []

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture + pd.Timedelta(minutes=50),
        requests_data=second_data,
    )

    # Verify no additional bet placed
    assert not market_trader.betfair_client.placed_orders

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [25.0],
                "average_price_matched": [3.0],
                "cashed_out": [False],
                "fully_matched": [False],
            }
        ),
    )
