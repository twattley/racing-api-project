import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

from trader.market_trader import MarketTrader
from tests.test_helpers import create_test_data


def test_invalidates_place_market_change(
    postgres_client, betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )
    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=create_test_data(
            {
                "minutes_to_race": [-1, 10, 10],
                "eight_to_seven_runners": [False, False, True],
            }
        ),
    )

    expected_selections_data = pd.DataFrame(
        {
            "unique_id": ["1", "2", "3"],
            "timestamp": [
                pd.Timestamp("2025-05-31 12:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 18:00:00"),
            ],
            "race_id": [1, 2, 3],
            "race_time": [
                pd.Timestamp("2025-05-31 15:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 20:00:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
            ],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "BACK", "BACK"],
            "market_type": ["WIN", "WIN", "PLACE"],
            "market_id": ["1", "2", "3"],
            "selection_id": [1, 2, 3],
            "requested_odds": [3.0, 4.0, 7.0],
            "valid": [False, True, False],
            "invalidated_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("NaT"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
            "invalidated_reason": ["Race Started", "", "Invalid 8 to 7 Place"],
            "size_matched": [0.0, 0.0, 0.0],
            "average_price_matched": [np.nan, np.nan, np.nan],
            "cashed_out": [False, False, True],
            "fully_matched": [False, False, False],
            "customer_strategy_ref": ["selection", "selection", "selection"],
            "processed_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
        }
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype("datetime64[s]")
    pd.testing.assert_frame_equal(
        trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert len(trader.postgres_client.stored_data) == 3
    assert trader.betfair_client.cash_out_market_ids == [["3"]]
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=10.0,
            price=4.0,
            selection_id=2,
            market_id="2",
            side="BACK",
            strategy="mvp",
        ),
    ]


def test_doesnt_invalidate_win_place_market_change(
    postgres_client, betfair_client, now_timestamp_fixture, set_stake_size
):
    """
    Test that a win market does not invalidate a place market when the number of runners changes from 8 to 7.

    """

    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )

    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=create_test_data(
            {
                "minutes_to_race": [-1, 10, 10],
                "eight_to_seven_runners": [False, False, True],
                "market_type": ["WIN", "WIN", "WIN"],
            }
        ),
    )

    expected_selections_data = pd.DataFrame(
        {
            "unique_id": ["1", "2", "3"],
            "timestamp": [
                pd.Timestamp("2025-05-31 12:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 18:00:00"),
            ],
            "race_id": [1, 2, 3],
            "race_time": [
                pd.Timestamp("2025-05-31 15:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 20:00:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
            ],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "BACK", "BACK"],
            "market_type": ["WIN", "WIN", "WIN"],
            "market_id": ["1", "2", "3"],
            "selection_id": [1, 2, 3],
            "requested_odds": [3.0, 4.0, 7.0],
            "valid": [False, True, True],
            "invalidated_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("NaT"),
                pd.Timestamp("NaT"),
            ],
            "invalidated_reason": ["Race Started", "", ""],
            "size_matched": [0.0, 0.0, 0.0],
            "average_price_matched": [np.nan, np.nan, np.nan],
            "cashed_out": [False, False, False],
            "fully_matched": [False, False, False],
            "customer_strategy_ref": ["selection", "selection", "selection"],
            "processed_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
        }
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype("datetime64[s]")
    pd.testing.assert_frame_equal(
        trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert len(trader.postgres_client.stored_data) == 3
    assert not trader.betfair_client.cash_out_market_ids
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=10.0,
            price=4.0,
            selection_id=2,
            market_id="2",
            side="BACK",
            strategy="mvp",
        ),
        BetFairOrder(
            size=10.0,
            price=7.0,
            selection_id=3,
            market_id="3",
            side="BACK",
            strategy="mvp",
        ),
    ]


def test_invalidates_short_price_removed_runners(
    postgres_client, betfair_client, now_timestamp_fixture, set_stake_size
):
    """
    Test that short priced runners  invalidate a win market

    """

    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )

    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=create_test_data(
            {
                "minutes_to_race": [-1, 10, 10],
                "short_price_removed_runners": [False, True, False],
            }
        ),
    )

    expected_selections_data = pd.DataFrame(
        {
            "unique_id": ["1", "2", "3"],
            "timestamp": [
                pd.Timestamp("2025-05-31 12:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 18:00:00"),
            ],
            "race_id": [1, 2, 3],
            "race_time": [
                pd.Timestamp("2025-05-31 15:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 20:00:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
            ],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "BACK", "BACK"],
            "market_type": ["WIN", "WIN", "PLACE"],
            "market_id": ["1", "2", "3"],
            "selection_id": [1, 2, 3],
            "requested_odds": [3.0, 4.0, 7.0],
            "valid": [False, False, True],
            "invalidated_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("NaT"),
            ],
            "invalidated_reason": ["Race Started", "Invalid Short Price Removed", ""],
            "size_matched": [0.0, 0.0, 0.0],
            "average_price_matched": [np.nan, np.nan, np.nan],
            "cashed_out": [False, True, False],
            "fully_matched": [False, False, False],
            "customer_strategy_ref": ["selection", "selection", "selection"],
            "processed_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
        }
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype("datetime64[s]")
    pd.testing.assert_frame_equal(
        trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert len(trader.postgres_client.stored_data) == 3
    assert trader.betfair_client.cash_out_market_ids == [["2"]]
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=10.0,
            price=7.0,
            selection_id=3,
            market_id="3",
            side="BACK",
            strategy="mvp",
        ),
    ]


def test_cashes_out_fully_matched_bets(
    postgres_client, betfair_client, now_timestamp_fixture, set_stake_size
):
    """
    Test that previously fully matched bets are cashed out when the market changes.

    """

    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )

    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=create_test_data(
            {
                "requested_odds": [3.0, 4.0, 7.0],
                "valid": [False, True, True],
                "minutes_to_race": [-1, 10, 10],
                "short_price_removed_runners": [False, True, True],
                "eight_to_seven_runners": [False, True, True],
                "fully_matched": [False, True, True],
                "average_price_matched_betfair": [np.nan, 4.0, 7.0],
                "size_matched_betfair": [0.0, 10.0, 10.0],
            }
        ),
    )

    expected_selections_data = pd.DataFrame(
        {
            "unique_id": ["1", "2", "3"],
            "timestamp": [
                pd.Timestamp("2025-05-31 12:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 18:00:00"),
            ],
            "race_id": [1, 2, 3],
            "race_time": [
                pd.Timestamp("2025-05-31 15:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 20:00:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
            ],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "BACK", "BACK"],
            "market_type": ["WIN", "WIN", "PLACE"],
            "market_id": ["1", "2", "3"],
            "selection_id": [1, 2, 3],
            "requested_odds": [3.0, 4.0, 7.0],
            "valid": [False, False, False],
            "invalidated_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
            "invalidated_reason": [
                "Race Started",
                "Invalid Short Price Removed",
                "Invalid 8 to 7 Place",
            ],
            "size_matched": [0.0, 10.0, 10.0],
            "average_price_matched": [np.nan, 4.0, 7.0],
            "cashed_out": [False, True, True],
            "fully_matched": [False, True, True],
            "customer_strategy_ref": ["selection", "selection", "selection"],
            "processed_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
        }
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype("datetime64[s]")

    # standard assertions
    assert len(trader.postgres_client.stored_data) == 3
    # standard assertions

    pd.testing.assert_frame_equal(
        trader.postgres_client.stored_data,
        expected_selections_data,
    )
    assert trader.betfair_client.cash_out_market_ids == [["3", "2"]]
    assert not trader.betfair_client.placed_orders
