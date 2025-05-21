import pandas as pd
from typing import Union, List, Dict


def assert_df_data_equal(
    received_df: pd.DataFrame,
    expected_data: Union[pd.DataFrame, List, Dict],
    ignore_not_expected_columns: bool = True,
    sort_rows_by_columns: List[str] = None,
    test_columns: List[str] = None,
    uuid_shortened: List[str] = None,
    round_columns: List[str] = None,
    coerce_to_integer: List[str] = None,
    **kwargs,
):
    expected_df = (
        expected_data
        if isinstance(expected_data, pd.DataFrame)
        else pd.DataFrame(expected_data)
    )
    if expected_df.empty and received_df.empty:
        return
    elif expected_df.empty or received_df.empty:
        assert False, "One is empty, other is not"

    if ignore_not_expected_columns:
        received_df = received_df[expected_df.columns]

    if round_columns:
        for column in round_columns:
            received_df = received_df.assign(**{column: received_df[column].round(2)})
            expected_df = expected_df.assign(**{column: expected_df[column].round(2)})

    if uuid_shortened:
        for column in uuid_shortened:
            received_df = received_df.assign(**{column: received_df[column].str[:15]})
            expected_df = expected_df.assign(**{column: expected_df[column].str[:15]})

    if coerce_to_integer:
        for column in coerce_to_integer:
            received_df = received_df.assign(
                **{column: received_df[column].astype(int)}
            )
            expected_df = expected_df.assign(
                **{column: expected_df[column].astype(int)}
            )

    if sort_rows_by_columns:
        print("Sorting rows by columns: ", sort_rows_by_columns)
        received_df = received_df.sort_values(by=sort_rows_by_columns)
        expected_df = expected_df.sort_values(by=sort_rows_by_columns)

    if test_columns:
        received_df = received_df[test_columns]
        expected_df = expected_df[test_columns]

    print("[ Tests ] - Received data:")

    if test_columns:
        print(received_df[test_columns])
        print(received_df.info())
    else:
        print(received_df)
        print(received_df.info())
    print("[ Tests ] - Expected data:")
    if test_columns:
        print(expected_df[test_columns])
        print(expected_df.info())
    else:
        print(expected_df)
        print(expected_df.info())
    pd.testing.assert_frame_equal(
        received_df.sort_index(axis=1).reset_index(drop=True),
        expected_df.sort_index(axis=1).reset_index(drop=True),
        check_exact=True,
        **kwargs,
    )
