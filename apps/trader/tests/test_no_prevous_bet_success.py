import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

from ..src.trader.market_trader import MarketTrader
from .test_helpers import create_test_data


def test_success_first_bet(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        s3_client=get_s3_client,
        betfair_client=get_betfair_client,
    )
    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=create_test_data({"minutes_to_race": [-1, 10, 10]}),
    )

    assert (
        trader.s3_client.stored_data["object_path"]
        == "today/2025_01_10/trader_data/selections.parquet"
    )

    expected_selections_data = pd.DataFrame(
        {
            "id": ["1", "2", "3"],
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
                pd.Timestamp("2025-05-31 18:00:00"),
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
                pd.Timestamp("2025-05-31 18:00"),
                pd.Timestamp("2025-05-31 18:00"),
                pd.Timestamp("2025-05-31 18:00"),
            ],
        }
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype("datetime64[s]")
    pd.testing.assert_frame_equal(
        trader.s3_client.stored_data["data"],
        expected_selections_data,
    )
    assert len(trader.s3_client.stored_data["data"]) == 3
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
