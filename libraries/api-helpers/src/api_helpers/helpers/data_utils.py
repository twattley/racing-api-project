import pandas as pd


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
