from datetime import datetime

import numpy as np
import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

from trader.market_trader import MarketTrader

now_date_str = datetime.now().strftime("%Y-%m-%d")


def test_handles_cashed_out_bets(
    postgres_client, betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        postgres_client=postgres_client,
        betfair_client=betfair_client,
    )
    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=pd.DataFrame(
            {
                "unique_id": ["1", "2", "3", "3"],
                "race_id": [1, 2, 3, 3],
                "race_time": [
                    pd.Timestamp(f"{now_date_str} 15:00:00"),
                    pd.Timestamp(f"{now_date_str} 17:00:00"),
                    pd.Timestamp(f"{now_date_str} 20:00:00"),
                    pd.Timestamp(f"{now_date_str} 20:00:00"),
                ],
                "race_date": [
                    pd.Timestamp(f"{now_date_str} 00:00:00"),
                    pd.Timestamp(f"{now_date_str} 00:00:00"),
                    pd.Timestamp(f"{now_date_str} 00:00:00"),
                    pd.Timestamp(f"{now_date_str} 00:00:00"),
                ],
                "horse_id": [1, 2, 3, 3],
                "horse_name": ["Horse A", "Horse B", "Horse C", "Horse C"],
                "selection_type": ["BACK", "BACK", "BACK", "LAY"],
                "market_type": ["WIN", "WIN", "WIN", "WIN"],
                "market_id": ["1", "2", "3", "3"],
                "selection_id": [1, 2, 3, 3],
                "requested_odds": [3.0, 4.0, 7.0, 7.0],
                "valid": [True, True, False, False],
                "invalidated_at": [pd.NaT, pd.NaT, pd.NaT, pd.NaT],
                "invalidated_reason": ["", "", "", ""],
                "cashed_out": [False, False, True, True],
                "fully_matched": [False, False, False, False],
                "processed_at": [
                    pd.Timestamp(f"{now_date_str} 12:00"),
                    pd.Timestamp(f"{now_date_str} 17:00"),
                    pd.Timestamp(f"{now_date_str} 18:00"),
                    pd.Timestamp(f"{now_date_str} 18:00"),
                ],
                "minutes_to_race": [-10, 10, 20, 20],
                "back_price_1": [np.nan, 4.0, 7.0, 7.0],
                "back_price_1_depth": [np.nan, 100.0, 100.0, 100.0],
                "back_price_2": [np.nan, 4.8, 6.8, 6.8],
                "back_price_2_depth": [np.nan, 100.0, 100.0, 100.0],
                "lay_price_1": [np.nan, 5.2, 7.2, 7.2],
                "lay_price_1_depth": [np.nan, 100.0, 100.0, 100.0],
                "lay_price_2": [np.nan, 5.4, 7.4, 7.4],
                "lay_price_2_depth": [np.nan, 100.0, 100.0, 100.0],
                "eight_to_seven_runners": [False, False, False, False],
                "short_price_removed_runners": [False, False, False, False],
                "average_price_matched_selections": [np.nan, np.nan, np.nan, np.nan],
                "size_matched_selections": [0.0, 0.0, 0.0, 0.0],
                "customer_strategy_ref_selections": [
                    "selection",
                    "selection",
                    "selection",
                    "selection",
                ],
                "average_price_matched_betfair": [np.nan, np.nan, 7.0, 7.2],
                "size_matched_betfair": [0.0, 0.0, 10.0, 9.7],
                "customer_strategy_ref_betfair": [np.nan, np.nan, np.nan, np.nan],
            }
        ),
    )

    expected_selections_data = pd.DataFrame(
        {
            "unique_id": ["1", "2", "3", "3"],
            "race_id": [1, 2, 3, 3],
            "race_time": [
                pd.Timestamp("2025-05-31 15:00:00"),
                pd.Timestamp("2025-05-31 17:00:00"),
                pd.Timestamp("2025-05-31 20:00:00"),
                pd.Timestamp("2025-05-31 20:00:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
                pd.Timestamp("2025-05-31 00:00:00"),
            ],
            "horse_id": [1, 2, 3, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C", "Horse C"],
            "selection_type": ["BACK", "BACK", "BACK", "LAY"],
            "market_type": ["WIN", "WIN", "WIN", "WIN"],
            "market_id": ["1", "2", "3", "3"],
            "selection_id": [1, 2, 3, 3],
            "requested_odds": [3.0, 4.0, 7.0, 7.0],
            "valid": [True, True, False, False],
            "invalidated_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("NaT"),
                pd.Timestamp("NaT"),
                pd.Timestamp("NaT"),
            ],
            "invalidated_reason": ["Race Started", "", "", ""],
            "size_matched": [0.0, 0.0, 10.0, 9.7],
            "average_price_matched": [np.nan, np.nan, 7.0, 7.2],
            "cashed_out": [False, False, True, True],
            "fully_matched": [False, False, True, True],
            "customer_strategy_ref": [
                "selection",
                "selection",
                "selection",
                "selection",
            ],
            "processed_at": [
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
                pd.Timestamp("2025-01-01 18:00:00"),
            ],
        }
    )
    expected_selections_data["processed_at"] = expected_selections_data[
        "processed_at"
    ].astype(
        "datetime64[s]"
    )  # standard assertions
    assert len(trader.postgres_client.stored_data) == 6
    # Check that cash outs happened for market '3'
    assert trader.betfair_client.cash_out_market_ids == [["3"]]
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=10.0,
            price=4.0,
            selection_id=2,
            market_id="2",
            side="BACK",
            strategy="2",
        )
    ]
