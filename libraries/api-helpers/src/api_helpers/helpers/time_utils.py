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
    df = df.copy()
    df[col_name] = df[col_name].dt.tz_convert("Europe/London").dt.tz_localize(None)
    return df
