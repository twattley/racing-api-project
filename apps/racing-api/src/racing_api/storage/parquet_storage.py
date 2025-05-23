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
