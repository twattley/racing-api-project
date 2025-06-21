import numpy as np
import pandas as pd
from api_helpers.helpers.data_utils import print_dataframe_for_testing


def create_single_test_data(requests_overrides=None):
    requests_dict = {
        "unique_id": ["1"],
        "race_id": [1],
        "race_time": [pd.Timestamp("2025-01-01 15:00:00")],
        "race_date": [pd.Timestamp("2025-01-01 00:00:00")],
        "horse_id": [1],
        "horse_name": ["Horse A"],
        "selection_type": ["BACK"],
        "market_type": ["WIN"],
        "market_id": ["1"],
        "selection_id": [1],
        "requested_odds": [3.0],
        "valid": [True],
        "invalidated_at": [pd.NaT],
        "invalidated_reason": [""],
        "size_matched": [0.0],
        "average_price_matched": [np.nan],
        "cashed_out": [False],
        "fully_matched": [False],
        "customer_strategy_ref": ["selection"],
        "processed_at": [pd.Timestamp("2025-01-01 12:00:00")],
        "minutes_to_race": [10],
        "back_price_1": [5.0],
        "back_price_1_depth": [100.0],
        "back_price_2": [4.8],
        "back_price_2_depth": [100.0],
        "lay_price_1": [5.2],
        "lay_price_1_depth": [100.0],
        "lay_price_2": [5.4],
        "lay_price_2_depth": [100.0],
        "eight_to_seven_runners": [False],
        "short_price_removed_runners": [False],
        "average_price_matched_selections": [np.nan],
        "size_matched_selections": [0.0],
        "customer_strategy_ref_selections": ["selection"],
        "average_price_matched_betfair": [np.nan],
        "size_matched_betfair": [0.0],
        "customer_strategy_ref_betfair": [np.nan],
    }

    return pd.DataFrame(
        {
            **requests_dict,
            **(requests_overrides or {}),
        }
    )


def create_test_data(requests_overrides=None):
    requests_dict = {
        "unique_id": ["1", "2", "3"],
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


def assert_dataset_equal(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
) -> None:
    """Assert that two DataFrames are equal, ignoring index and dtype."""

    # Get only the columns that exist in both DataFrames
    expected_columns = list(expected.columns)
    actual_subset = actual[expected_columns]

    print("=" * 100)
    print("ACTUAL DATAFRAME:")
    print("=" * 100)
    print_dataframe_for_testing(actual_subset)
    print("=" * 100)
    print("EXPECTED DATAFRAME:")
    print("=" * 100)
    print_dataframe_for_testing(expected)

    if actual is None:
        if expected is not None and len(expected) > 0:
            raise AssertionError("Expected DataFrame but got None")
        return

    pd.testing.assert_frame_equal(
        actual_subset,
        expected,
    )
