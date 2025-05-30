import numpy as np
import pandas as pd


def create_test_data(requests_overrides=None):
    requests_dict = {
        "id": ["1", "2", "3"],
        "timestamp": [
            pd.Timestamp("2025-01-01 12:00:00"),
            pd.Timestamp("2025-01-01 17:00:00"),
            pd.Timestamp("2025-01-01 18:00:00"),
        ],
        "race_id": [1, 2, 3],
        "race_time": [
            pd.Timestamp("2025-01-01 15:00:00"),
            pd.Timestamp("2025-01-01 17:00:00"),
            pd.Timestamp("2025-01-01 20:00:00"),
        ],
        "race_date": [
            pd.Timestamp("2025-01-01 00:00:00"),
            pd.Timestamp("2025-01-01 00:00:00"),
            pd.Timestamp("2025-01-01 00:00:00"),
        ],
        "horse_id": [1, 2, 3],
        "horse_name": ["Horse A", "Horse B", "Horse C"],
        "selection_type": ["BACK", "BACK", "BACK"],
        "market_type": ["WIN", "WIN", "PLACE"],
        "market_id": ["1", "2", "3"],
        "selection_id": [1, 2, 3],
        "requested_odds": [3.0, 5.0, 7.0],
        "valid": [True, True, True],
        "invalidated_at": [pd.NaT, pd.NaT, pd.NaT],
        "invalidated_reason": ["", "", ""],
        "size_matched": [0.0, 0.0, 0.0],
        "average_price_matched": [np.nan, np.nan, np.nan],
        "cashed_out": [False, False, False],
        "fully_matched": [False, False, True],
        "customer_strategy_ref": ["selection", "selection", "selection"],
        "processed_at": [
            pd.Timestamp("2025-01-01 12:00:00"),
            pd.Timestamp("2025-01-01 17:00:00"),
            pd.Timestamp("2025-01-01 18:00:00"),
        ],
        "minutes_to_race": [-10, 10, 20],
        "back_price_1": [np.nan, 5.0, 7.0],
        "back_price_1_depth": [np.nan, 100.0, 100.0],
        "back_price_2": [np.nan, 4.8, 6.8],
        "back_price_2_depth": [np.nan, 100.0, 100.0],
        "lay_price_1": [np.nan, 5.2, 7.2],
        "lay_price_1_depth": [np.nan, 100.0, 100.0],
        "lay_price_2": [np.nan, 5.4, 7.4],
        "lay_price_2_depth": [np.nan, 100.0, 100.0],
        "eight_to_seven_runners": [False, False, True],
        "short_price_removed_runners": [False, False, False],
        "average_price_matched_selections": [np.nan, np.nan, np.nan],
        "size_matched_selections": [0.0, 0.0, 0.0],
        "customer_strategy_ref_selections": ["selection", "selection", "selection"],
        "average_price_matched_betfair": [np.nan, np.nan, np.nan],
        "size_matched_betfair": [0.0, 0.0, 0.0],
        "customer_strategy_ref_betfair": [np.nan, np.nan, np.nan],
    }

    return pd.DataFrame(
        {
            **requests_dict,
            **(requests_overrides or {}),
        }
    )
