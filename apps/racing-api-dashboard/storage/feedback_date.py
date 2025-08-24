from . import pg_client
import pandas as pd

def update_feedback_date(
    input_date: str,
):
    return pg_client.execute_query(
        f"UPDATE api.feedback_date SET today_date = '{input_date}'"
    )


def get_feedback_date() -> pd.DataFrame:
    return pg_client.fetch_data("SELECT today_date FROM api.feedback_date")
