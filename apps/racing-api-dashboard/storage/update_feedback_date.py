from . import pg_client

def update_feedback_date(
    input_date: str,
):
    return pg_client.execute_query(
        f"UPDATE api.feedback_date SET today_date = '{input_date}'"
    )
