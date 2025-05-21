from datetime import datetime, timezone

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
