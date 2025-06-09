from datetime import datetime, timezone
import pandas as pd
import pytz


def get_uk_time_now():
    utc_now = datetime.now(timezone.utc)
    uk_timezone = pytz.timezone("Europe/London")
    return utc_now.astimezone(uk_timezone)


def make_uk_time_aware(dt):
    utc_zone = pytz.utc
    uk_zone = pytz.timezone("Europe/London")
    utc_datetime = utc_zone.localize(dt)
    return utc_datetime.astimezone(uk_zone)


def convert_col_utc_to_uk(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """
    Converts a specified UTC timezone-aware DataFrame column to UK timezone,
    then makes it timezone-naive.
    If the column is already timezone-naive, it catches the specific TypeError
    and returns the DataFrame unchanged.

    Args:
        df (pd.DataFrame): The input DataFrame.
        col_name (str): The name of the column to convert.

    Returns:
        pd.DataFrame: The DataFrame with the converted column, or the
                      original DataFrame if a timezone-naive error occurs.
    """
    # Create a copy to avoid modifying the original DataFrame in place

    if df.empty:
        print("Warning: The DataFrame is empty. Returning an empty DataFrame.")
        return df

    df_copy = df.copy()

    print(df_copy)

    try:
        # Attempt the timezone conversion
        # It's expected that df_copy[col_name] is UTC timezone-aware here.
        # .dt.tz_convert("Europe/London") converts to London timezone.
        # .dt.tz_localize(None) then removes the timezone information,
        # effectively making it timezone-naive but with values now
        # representing the time in London.
        df_copy[col_name] = (
            df_copy[col_name].dt.tz_convert("Europe/London").dt.tz_localize(None)
        )
        return df_copy
    except TypeError as e:
        # Check if the error message matches the specific "tz-naive" error
        if "Cannot convert tz-naive timestamps, use tz_localize to localize" in str(e):
            print(
                f"Warning: Column '{col_name}' is timezone-naive. Returning DataFrame unchanged."
            )
            # If it's the expected error, return the original (unmodified) copy
            return df_copy
        else:
            # If it's a different TypeError, re-raise it
            raise e
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(
            f"An unexpected error occurred during timezone conversion of column '{col_name}': {e}"
        )
        raise e
