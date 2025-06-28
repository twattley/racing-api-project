import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

from trader.market_trader import MarketTrader
from .test_helpers import create_single_test_data, assert_dataset_equal
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.clients.betfair_client import BetFairClient

import pytest


@pytest.mark.parametrize(
    "overwrite_data, expected_selections_data, placed_orders",
    [
        # Test case 1: BACK - no money down, first bet - conditions met
        (
            {
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "back_price_1_depth": [50.0],
                "requested_odds": [3.0],
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
        # Test case 2: BACK - no money down, first bet - insufficient liquidity
        (
            {
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "back_price_1_depth": [25.0],  # Less than stake size (50)
                "requested_odds": [3.0],
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
                    "size_matched": [25.0],
                    "invalidated_reason": [""],
                    "average_price_matched": [3.0],
                    "cashed_out": [False],
                    "fully_matched": [False],
                }
            ),
            [
                BetFairOrder(
                    size=25.0,
                    price=3.0,
                    selection_id=1,
                    market_id="1",
                    side="BACK",
                    strategy="1",
                )
            ],
        ),
        # Test case 3: BACK - no money down, first bet - odds too low
        (
            {
                "minutes_to_race": [10],
                "back_price_1": [2.5],  # Below requested odds of 3.0
                "back_price_1_depth": [50.0],
                "requested_odds": [3.0],
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
                    "size_matched": [0.0],
                    "invalidated_reason": [""],
                    "average_price_matched": [np.nan],
                    "cashed_out": [False],
                    "fully_matched": [False],
                }
            ),
            [],
        ),
        # Test case 4: LAY - no money down, first bet - conditions met
        # Stake size is 50, so liability = 50 * 1.5 = 75, lay_price_1 = 3.0
        # Bet size = 75 / (3.0 - 1) = 37.5
        (
            {
                "minutes_to_race": [10],
                "selection_type": ["LAY"],
                "lay_price_1": [3.0],
                "lay_price_1_depth": [50.0],
                "requested_odds": [3.0],
            },
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "race_id": [1],
                    "horse_id": [1],
                    "selection_type": ["LAY"],
                    "market_type": ["WIN"],
                    "market_id": ["1"],
                    "selection_id": [1],
                    "requested_odds": [3.0],
                    "valid": [True],
                    "size_matched": [37.5],  # 75 / (3.0 - 1)
                    "invalidated_reason": [""],
                    "average_price_matched": [3.0],
                    "cashed_out": [False],
                    "fully_matched": [
                        False
                    ],  # Not fully matched due to insufficient depth
                }
            ),
            [
                BetFairOrder(
                    size=37.5,
                    price=3.0,
                    selection_id=1,
                    market_id="1",
                    side="LAY",
                    strategy="1",
                )
            ],
        ),
        # Test case 5: LAY - no money down, first bet - insufficient liquidity
        (
            {
                "minutes_to_race": [10],
                "selection_type": ["LAY"],
                "lay_price_1": [3.0],
                "lay_price_1_depth": [20.0],  # Less than needed stake (37.5)
                "requested_odds": [3.0],
            },
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "race_id": [1],
                    "horse_id": [1],
                    "selection_type": ["LAY"],
                    "market_type": ["WIN"],
                    "market_id": ["1"],
                    "selection_id": [1],
                    "requested_odds": [3.0],
                    "valid": [True],
                    "size_matched": [20.0],
                    "invalidated_reason": [""],
                    "average_price_matched": [3.0],
                    "cashed_out": [False],
                    "fully_matched": [False],
                }
            ),
            [
                BetFairOrder(
                    size=20.0,  # Only matched what was available
                    price=3.0,
                    selection_id=1,
                    market_id="1",
                    side="LAY",
                    strategy="1",
                )
            ],
        ),
        # Test case 6: LAY - no money down, first bet - odds too high
        (
            {
                "minutes_to_race": [10],
                "selection_type": ["LAY"],
                "lay_price_1": [3.5],  # Above requested odds of 3.0
                "lay_price_1_depth": [50.0],
                "requested_odds": [3.0],
            },
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "race_id": [1],
                    "horse_id": [1],
                    "selection_type": ["LAY"],
                    "market_type": ["WIN"],
                    "market_id": ["1"],
                    "selection_id": [1],
                    "requested_odds": [3.0],
                    "valid": [True],
                    "size_matched": [0.0],
                    "invalidated_reason": [""],
                    "average_price_matched": [np.nan],
                    "cashed_out": [False],
                    "fully_matched": [False],
                }
            ),
            [],
        ),
    ],
    ids=[
        "BACK - first bet - conditions met",
        "BACK - first bet - insufficient liquidity",
        "BACK - first bet - odds too low",
        "LAY - first bet - conditions met",
        "LAY - first bet - insufficient liquidity",
        "LAY - first bet - odds too high",
    ],
)
def test_bets_no_existing_position(
    market_trader: MarketTrader,
    now_timestamp_fixture: pd.Timestamp,
    overwrite_data: dict,
    expected_selections_data: pd.DataFrame,
    placed_orders: list[BetFairOrder],
):
    """
    Test bet placement when there is no existing position (first bet scenarios).

    This covers the basic scenarios where no money has been placed yet:
    - BACK bets: conditions met, insufficient liquidity, odds too low
    - LAY bets: conditions met, insufficient liquidity, odds too high
    """
    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=create_single_test_data(overwrite_data),
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert market_trader.betfair_client.placed_orders == placed_orders
