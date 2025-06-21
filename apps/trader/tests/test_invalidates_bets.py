import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

import pytest

from trader.market_trader import MarketTrader
from .test_helpers import create_single_test_data, assert_dataset_equal
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.clients.betfair_client import BetFairClient


@pytest.mark.parametrize(
    "overwrite_data, expected_selections_data, placed_orders, cash_out_ids",
    [
        (
            {
                "selection_type": ["BACK"],
                "market_type": ["WIN"],
                "requested_odds": [3.0],
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "eight_to_seven_runners": [True],
            },
            pd.DataFrame(
                {
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
            [],
        ),
        (
            {
                "selection_type": ["BACK"],
                "market_type": ["PLACE"],
                "requested_odds": [3.0],
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "eight_to_seven_runners": [True],
            },
            pd.DataFrame(
                {
                    "valid": [False],
                    "size_matched": [0.0],
                    "invalidated_reason": ["Invalid 8 to 7 Place"],
                    "cashed_out": [True],
                    "fully_matched": [False],
                }
            ),
            [],
            [["1"]],
        ),
        (
            {
                "selection_type": ["BACK"],
                "market_type": ["WIN"],
                "requested_odds": [3.0],
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "short_price_removed_runners": [True],
            },
            pd.DataFrame(
                {
                    "valid": [False],
                    "size_matched": [0.0],
                    "invalidated_reason": ["Invalid Short Price Removed"],
                    "cashed_out": [True],
                    "fully_matched": [False],
                }
            ),
            [],
            [["1"]],
        ),
        (
            {
                "selection_type": ["BACK"],
                "market_type": ["PLACE"],
                "requested_odds": [3.0],
                "minutes_to_race": [10],
                "back_price_1": [3.0],
                "short_price_removed_runners": [True],
            },
            pd.DataFrame(
                {
                    "valid": [False],
                    "size_matched": [0.0],
                    "invalidated_reason": ["Invalid Short Price Removed"],
                    "cashed_out": [True],
                    "fully_matched": [False],
                }
            ),
            [],
            [["1"]],
        ),
    ],
)
def test_invalidates_bets(
    market_trader: MarketTrader,
    now_timestamp_fixture: pd.Timestamp,
    overwrite_data: dict,
    expected_selections_data: pd.DataFrame,
    placed_orders: list[BetFairOrder],
    cash_out_ids: list[str],
):
    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=create_single_test_data(overwrite_data),
    )

    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert market_trader.betfair_client.cash_out_market_ids == cash_out_ids

    assert market_trader.betfair_client.placed_orders == placed_orders


def test_invalidates_fully_matched_bets(
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    now_timestamp_fixture: pd.Timestamp,
):
    """Test that fully matched bets that become invalidated are cashed out"""
    # Create a scenario where we have fully matched bets that become invalid
    test_data = create_single_test_data(
        {
            "selection_type": ["BACK"],
            "market_type": ["PLACE"],
            "requested_odds": [3.0],
            "minutes_to_race": [10],
            "back_price_1": [3.0],
            "eight_to_seven_runners": [True],  # This will invalidate the PLACE bet
            "size_matched_betfair": [50.0],  # Bet is fully matched
            "average_price_matched_betfair": [3.0],
            "fully_matched": [True],  # Already fully matched
        }
    )

    expected_selections_data = pd.DataFrame(
        {
            "valid": [False],  # Invalid due to 8 to 7 place
            "size_matched": [50.0],  # Keep the matched size
            "invalidated_reason": ["Invalid 8 to 7 Place"],
            "average_price_matched": [3.0],  # Keep the matched price
            "cashed_out": [True],  # Should be cashed out
            "fully_matched": [True],  # Remains fully matched
        }
    )

    market_trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )

    market_trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        requests_data=test_data,
    )

    # Verify the bet was marked as invalid and cashed out
    assert_dataset_equal(
        market_trader.postgres_client.stored_data,
        expected_selections_data,
    )

    # Verify that the fully matched invalid bet was cashed out
    assert market_trader.betfair_client.cash_out_market_ids == [["1"]]

    # Verify no new orders were placed (since bet is invalid and fully matched)
    assert market_trader.betfair_client.placed_orders == []
