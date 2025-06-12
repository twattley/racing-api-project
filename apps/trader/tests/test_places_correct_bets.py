import numpy as np
import pandas as pd
import pytest
from api_helpers.clients.betfair_client import BetFairOrder

from ..src.trader.market_trader import MarketTrader
from .test_helpers import create_test_data


@pytest.mark.parametrize(
    "test_request_data, expected_selections_data, expected_placed_orders",
    [
        (
            create_test_data(
                {
                    "selection_type": ["BACK", "BACK", "BACK"],
                    "requested_odds": [3.0, 4.0, 7.0],
                    "minutes_to_race": [-1, 10, 10],
                    "average_price_matched_betfair": [np.nan, 4.0, 7.0],
                    "size_matched_betfair": [0.0, 5.0, 5.0],
                }
            ),
            pd.DataFrame(
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
                    "valid": [False, True, True],
                    "invalidated_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("NaT"),
                        pd.Timestamp("NaT"),
                    ],
                    "invalidated_reason": ["Race Started", "", ""],
                    "size_matched": [0.0, 5.0, 5.0],
                    "average_price_matched": [np.nan, 4.0, 7.0],
                    "cashed_out": [False, False, False],
                    "fully_matched": [False, False, False],
                    "customer_strategy_ref": ["selection", "selection", "selection"],
                    "processed_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                    ],
                }
            ),
            [
                BetFairOrder(
                    size=5.0,
                    price=4.0,
                    selection_id=2,
                    market_id="2",
                    side="BACK",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=5.0,
                    price=7.0,
                    selection_id=3,
                    market_id="3",
                    side="BACK",
                    strategy="mvp",
                ),
            ],
        ),
        (
            create_test_data(
                {
                    "selection_type": ["BACK", "BACK", "BACK"],
                    "back_price_1": [np.nan, 3.8, 6.8],
                    "requested_odds": [3.0, 4.0, 7.0],
                    "minutes_to_race": [-1, 10, 10],
                    "average_price_matched_betfair": [np.nan, 4.0, 7.0],
                    "size_matched_betfair": [0.0, 5.0, 5.0],
                }
            ),
            pd.DataFrame(
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
                    "valid": [False, True, True],
                    "invalidated_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("NaT"),
                        pd.Timestamp("NaT"),
                    ],
                    "invalidated_reason": ["Race Started", "", ""],
                    "size_matched": [0.0, 5.0, 5.0],
                    "average_price_matched": [np.nan, 4.0, 7.0],
                    "cashed_out": [False, False, False],
                    "fully_matched": [False, False, False],
                    "customer_strategy_ref": ["selection", "selection", "selection"],
                    "processed_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                    ],
                }
            ),
            [],
        ),
        (
            create_test_data(
                {
                    "selection_type": ["BACK", "LAY", "LAY"],
                    "lay_price_1": [np.nan, 2.0, 3.0],
                    "requested_odds": [3.0, 2.0, 3.0],
                    "minutes_to_race": [-1, 10, 10],
                    "average_price_matched_betfair": [np.nan, 2.0, 3.0],
                    "size_matched_betfair": [0.0, 5.0, 5.0],
                }
            ),
            pd.DataFrame(
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
                    "selection_type": ["BACK", "LAY", "LAY"],
                    "market_type": ["WIN", "WIN", "PLACE"],
                    "market_id": ["1", "2", "3"],
                    "selection_id": [1, 2, 3],
                    "requested_odds": [3.0, 2.0, 3.0],
                    "valid": [False, True, True],
                    "invalidated_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("NaT"),
                        pd.Timestamp("NaT"),
                    ],
                    "invalidated_reason": ["Race Started", "", ""],
                    "size_matched": [0.0, 5.0, 5.0],
                    "average_price_matched": [np.nan, 2.0, 3.0],
                    "cashed_out": [False, False, False],
                    "fully_matched": [False, False, False],
                    "customer_strategy_ref": ["selection", "selection", "selection"],
                    "processed_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                    ],
                }
            ),
            [
                BetFairOrder(
                    size=10.0,
                    price=2.0,
                    selection_id=2,
                    market_id="2",
                    side="LAY",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=2.5,
                    price=3.0,
                    selection_id=3,
                    market_id="3",
                    side="LAY",
                    strategy="mvp",
                ),
            ],
        ),
        (
            create_test_data(
                {
                    "selection_type": ["BACK", "LAY", "LAY"],
                    "lay_price_1": [np.nan, 2.0, 3.0],
                    "lay_price_1_depth": [np.nan, 1.0, 1.0],
                    "requested_odds": [3.0, 2.0, 3.0],
                    "minutes_to_race": [-1, 10, 10],
                    "average_price_matched_betfair": [np.nan, 2.0, 3.0],
                    "size_matched_betfair": [0.0, 5.0, 5.0],
                }
            ),
            pd.DataFrame(
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
                    "selection_type": ["BACK", "LAY", "LAY"],
                    "market_type": ["WIN", "WIN", "PLACE"],
                    "market_id": ["1", "2", "3"],
                    "selection_id": [1, 2, 3],
                    "requested_odds": [3.0, 2.0, 3.0],
                    "valid": [False, True, True],
                    "invalidated_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("NaT"),
                        pd.Timestamp("NaT"),
                    ],
                    "invalidated_reason": ["Race Started", "", ""],
                    "size_matched": [0.0, 5.0, 5.0],
                    "average_price_matched": [np.nan, 2.0, 3.0],
                    "cashed_out": [False, False, False],
                    "fully_matched": [False, False, False],
                    "customer_strategy_ref": ["selection", "selection", "selection"],
                    "processed_at": [
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                        pd.Timestamp("2025-01-01 18:00:00"),
                    ],
                }
            ),
            [],
        ),
    ],
)
def test_place_correct_bets(
    test_request_data,
    expected_selections_data,
    expected_placed_orders,
    get_s3_client,
    get_betfair_client,
    now_timestamp_fixture,
    set_stake_size,
):
    trader = MarketTrader(
        s3_client=get_s3_client,
        betfair_client=get_betfair_client,
    )
    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=test_request_data,
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype("datetime64[s]")

    # standard assertions
    assert len(trader.s3_client.stored_data["data"]) == 3
    assert (
        trader.s3_client.stored_data["object_path"]
        == "today/2025_01_01/trader_data/selections.parquet"
    )
    # standard assertions

    pd.testing.assert_frame_equal(
        trader.s3_client.stored_data["data"],
        expected_selections_data,
    )
    assert not trader.betfair_client.cash_out_market_ids
    assert trader.betfair_client.placed_orders == expected_placed_orders
