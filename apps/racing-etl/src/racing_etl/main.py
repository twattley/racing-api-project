import argparse

from api_helpers.clients import get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient

from .backup.backup_db import backup_tables
from .pipelines.data_checks_pipeline import run_data_checks_pipeline
from .pipelines.ingestion_pipeline import run_ingestion_pipeline
from .pipelines.load_pipeline import run_load_pipeline
from .pipelines.matching_pipeline import run_matching_pipeline
from .pipelines.transformation_pipeline import run_transformation_pipeline


def run_daily_pipeline():
    parser = argparse.ArgumentParser(
        description="This script runs the ingestion pipeline for racing data.",
    )
    parser.add_argument(
        "-c",
        "--comments",
        action="store_true",
    )
    parser.add_argument(
        "-wc",
        "--world-comments",
        action="store_true",
    )
    parser.add_argument(
        "-b",
        "--backup-tables",
        action="store_true",
    )
    pipeline_args = parser.parse_args()
    db_client: PostgresClient = get_postgres_client()
    run_ingestion_pipeline(db_client, pipeline_args)
    run_matching_pipeline(db_client)
    run_transformation_pipeline(db_client)
    run_load_pipeline(db_client)
    run_data_checks_pipeline(db_client)


if __name__ == "__main__":
    run_daily_pipeline()
