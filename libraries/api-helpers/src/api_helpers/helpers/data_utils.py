import pandas as pd
import re


def combine_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    Combines two pandas DataFrames based on whether they contain data.

    Args:
        df1: The first pandas DataFrame.
        df2: The second pandas DataFrame.

    Returns:
        A pandas DataFrame resulting from the combination logic:
        - If both df1 and df2 have data, returns their concatenation.
        - If only df1 has data, returns df1.
        - If only df2 has data, returns df2.
        - If both df1 and df2 are empty, returns an empty DataFrame
          (specifically, it will be an empty version of df1,
           or you can choose to return a completely new empty DataFrame).
    """
    df1_has_data = not df1.empty
    df2_has_data = not df2.empty

    if df1_has_data and df2_has_data:
        # Both DataFrames have data, concatenate them
        return pd.concat([df1, df2], ignore_index=True)
    elif df1_has_data:
        # Only df1 has data
        return df1
    elif df2_has_data:
        # Only df2 has data
        return df2
    else:
        # Both DataFrames are empty, return an empty DataFrame
        # Returning df1 (which is empty) is fine, or create a new one:
        return pd.DataFrame()


import pandas as pd


def deduplicate_dataframe(
    new_data: pd.DataFrame,
    existing_data: pd.DataFrame,
    unique_columns: list[str],
    timestamp_column: str,
) -> pd.DataFrame:
    """
    Deduplicate a Parquet file by specified columns, keeping the most recent entry based on timestamp.

    Parameters:
    - input_file: Path to the input Parquet file
    - output_file: Path to save the deduplicated Parquet file
    - unique_columns: List of column names to use for identifying duplicates
    - timestamp_column: Name of the column to use for determining the most recent entry

    Returns:
    - Deduplicated DataFrame
    """

    df_combined = pd.concat([existing_data, new_data])
    df_sorted = df_combined.sort_values(by=[timestamp_column], ascending=False)
    df_deduplicated = df_sorted.drop_duplicates(subset=unique_columns, keep="first")
    df_deduplicated = df_deduplicated.sort_values(by=[timestamp_column])

    return df_deduplicated


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
