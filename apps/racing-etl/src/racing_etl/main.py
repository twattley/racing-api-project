from api_helpers.clients import get_postgres_client, get_s3_client

from .backup.backup_db import backup_tables
from .pipelines.data_checks_pipeline import run_data_checks_pipeline
from .pipelines.ingestion_pipeline import run_ingestion_pipeline
from .pipelines.load_pipeline import run_load_pipeline
from .pipelines.matching_pipeline import run_matching_pipeline
from .pipelines.transformation_pipeline import run_transformation_pipeline


def run_daily_pipeline():
    db_client = get_postgres_client()
    s3_client = get_s3_client()
    run_ingestion_pipeline(db_client)
    run_matching_pipeline(db_client)
    run_transformation_pipeline(db_client)
    run_load_pipeline(db_client, s3_client)
    run_data_checks_pipeline(db_client)
    backup_tables()


if __name__ == "__main__":
    run_daily_pipeline()
