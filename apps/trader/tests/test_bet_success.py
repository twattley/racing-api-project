import numpy as np
import pandas as pd
import pytest
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder
from api_helpers.clients.postgres_client import PostgresClient
from trader.market_trader import MarketTrader

from .test_helpers import assert_dataset_equal, create_single_test_data

import pandas as pd
import re


def print_dataframe_for_testing(df):

    print("pd.DataFrame({")

    for col in df.columns:
        value = df[col].iloc[0]
        if re.match(r"\d{4}-\d{2}-\d{2}", str(value)):
            str_test = (
                "[" + " ".join([f"pd.Timestamp('{x}')," for x in list(df[col])]) + "]"
            )
            print(f"'{col}':{str_test},")
        else:
            print(f"'{col}':{list(df[col])},")
    print("})")


@pytest.mark.parametrize(
    "overwrite_data, expected_selections_data, placed_orders",
    [
        (
            {
                "minutes_to_race": [-1],
                "back_price_1": [3.0],
                "back_price_1_depth": [50.0],
            },
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "race_id": [1],
                    "horse_id": [1],
                    "selection_type": ["BACK"],
                    "market_type": ["WIN"],
                    "market_id": ["1"],
                    "selection_id": [1],
                    "requested_odds": [3.0],
                    "valid": [False],
                    "size_matched": [0.0],
                    "invalidated_reason": ["Race Started"],
                    "average_price_matched": [np.nan],
                    "cashed_out": [False],
                    "fully_matched": [False],
                }
            ),
            [],
        ),
        (
            {
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "back_price_1_depth": [50.0],
            },
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "race_id": [1],
                    "horse_id": [1],
                    "selection_type": ["BACK"],
                    "market_type": ["WIN"],
                    "market_id": ["1"],
                    "selection_id": [1],
                    "requested_odds": [3.0],
                    "valid": [True],
                    "size_matched": [50.0],
                    "invalidated_reason": [""],
                    "average_price_matched": [3.0],
                    "cashed_out": [False],
                    "fully_matched": [True],
                }
            ),
            [
                BetFairOrder(
                    size=50.0,
                    price=3.0,
                    selection_id=1,
                    market_id="1",
                    side="BACK",
                    strategy="1",
                )
            ],
        ),
    ],
)
def test_success_bet(
    market_trader: MarketTrader,
    now_timestamp_fixture: pd.Timestamp,
    overwrite_data: dict,
    expected_selections_data: pd.DataFrame,
    placed_orders: list[BetFairOrder],
):
    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=create_single_test_data(overwrite_data),
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert not market_trader.betfair_client.cash_out_market_ids

    assert market_trader.betfair_client.placed_orders == placed_orders


def test_time_progression_staking_back_bets(
    market_trader: MarketTrader,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """Test that demonstrates time-based staking changes as race approaches"""

    initial_data = create_single_test_data(
        {
            "minutes_to_race": [480],
            "back_price_1": [3.0],
            "back_price_1_depth": [100.0],
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
        size=2.0, price=3.0, selection_id=1, market_id="1", side="BACK", strategy="1"
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [2.0],
                "average_price_matched": [3.0],
                "fully_matched": [False],
            }
        ),
    )

    first_run_data = market_trader.postgres_client.stored_data.copy()

    second_period_data = create_single_test_data(
        {
            "minutes_to_race": [60],
            "back_price_1": [3.0],
            "back_price_1_depth": [100.0],
            "size_matched": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched": [first_run_data["average_price_matched"].iloc[0]],
            "size_matched_betfair": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched_betfair": [
                first_run_data["average_price_matched"].iloc[0]
            ],
            "fully_matched": [first_run_data["fully_matched"].iloc[0]],
        }
    )

    postgres_client.stored_data = None
    betfair_client.placed_orders = []
    betfair_client.cash_out_market_ids = []

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture + pd.Timedelta(hours=7),
        requests_data=second_period_data,
    )

    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=18.0, price=3.0, selection_id=1, market_id="1", side="BACK", strategy="1"
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


def test_time_progression_staking_lay_bets(
    market_trader: MarketTrader,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """Test that demonstrates time-based staking changes for LAY bets as race approaches"""

    initial_data = create_single_test_data(
        {
            "selection_type": ["LAY"],
            "minutes_to_race": [480],
            "lay_price_1": [2.5],
            "lay_price_1_depth": [100.0],
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
        size=3.33, price=2.5, selection_id=1, market_id="1", side="LAY", strategy="1"
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [3.33],
                "average_price_matched": [2.5],
                "fully_matched": [False],
            }
        ),
    )

    first_run_data = market_trader.postgres_client.stored_data.copy()

    second_period_data = create_single_test_data(
        {
            "selection_type": ["LAY"],
            "minutes_to_race": [90],
            "lay_price_1": [2.5],
            "lay_price_1_depth": [100.0],
            "size_matched": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched": [first_run_data["average_price_matched"].iloc[0]],
            "size_matched_betfair": [first_run_data["size_matched"].iloc[0]],
            "average_price_matched_betfair": [
                first_run_data["average_price_matched"].iloc[0]
            ],
            "fully_matched": [first_run_data["fully_matched"].iloc[0]],
        }
    )

    postgres_client.stored_data = None
    betfair_client.placed_orders = []
    betfair_client.cash_out_market_ids = []

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture + pd.Timedelta(hours=6, minutes=30),
        requests_data=second_period_data,
    )

    assert market_trader.betfair_client.placed_orders[0] == BetFairOrder(
        size=20.0, price=2.5, selection_id=1, market_id="1", side="LAY", strategy="1"
    )

    final_data = market_trader.postgres_client.stored_data
    expected_total_stake = 35.0 / (2.5 - 1)
    assert abs(final_data["size_matched"].iloc[0] - expected_total_stake) < 0.01
    assert final_data["fully_matched"].iloc[0] == False

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        pd.DataFrame(
            {
                "valid": [True],
                "size_matched": [23.33],
                "average_price_matched": [2.5],
                "fully_matched": [False],
            }
        ),
    )
