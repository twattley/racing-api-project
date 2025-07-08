from datetime import datetime

import pandas as pd
from api_helpers.clients import get_postgres_client


def log_job_run_time(job_name: str):
    db_client = get_postgres_client()
    df = pd.DataFrame(
        {
            "job_name": [job_name],
            "created_at": [datetime.now().strftime("%Y-%m-%d %H:%M")],
        }
    )
    db_client.store_latest_data(
        data=df,
        table="service_job_run_times",
        schema="monitoring",
        unique_columns=["job_name"],
    )
