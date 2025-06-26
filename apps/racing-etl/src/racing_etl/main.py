import argparse
import random
import time
from pathlib import Path

from api_helpers.clients import get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.config import config
from api_helpers.helpers.file_utils import create_todays_log_file
from api_helpers.helpers.logging_config import I

from .pipelines.clean_tables_pipeline import run_data_clean_pipeline
from .pipelines.data_checks_pipeline import run_data_checks_pipeline
from .pipelines.ingestion_pipeline import run_ingestion_pipeline
from .pipelines.load_pipeline import run_load_pipeline
from .pipelines.matching_pipeline import run_matching_pipeline
from .pipelines.transformation_pipeline import run_transformation_pipeline


def create_centralized_log_files():
    """Create today's log files for all projects in the centralized logs directory."""
    # Use the monorepo root from config
    logs_root = Path(config.monorepo_root) / "logs"

    # Define the projects that need log files - all use uniform "execution_" prefix
    projects = ["racing-etl", "trader", "betfair-live-prices"]

    I("Creating centralized log files for all projects...")

    for project_name in projects:
        log_dir = logs_root / project_name
        log_file = create_todays_log_file(log_dir, "execution_")
        I(f"Created log file for {project_name}: {log_file}")


def set_random_sleep_time():
    """Set a random sleep time between 0 and 30 seconds."""
    sleep_time = random.uniform(0, 30)
    I(f"Sleeping for {sleep_time:.2f} seconds before starting the pipeline...")
    time.sleep(sleep_time)


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
    parser.add_argument(
        "-oc",
        "--only-comments",
        action="store_true",
    )
    parser.add_argument(
        "-owc",
        "--only-world-comments",
        action="store_true",
    )
    pipeline_args = parser.parse_args()
    I(f"Running pipeline with args: {pipeline_args}")
    set_random_sleep_time()
    create_centralized_log_files()
    I('Log files created in "logs" directory.')
    db_client: PostgresClient = get_postgres_client()
    if pipeline_args and pipeline_args.only_comments:
        I("Condition met: --only-comments flag was used only running ingestion pipeline.")
        run_ingestion_pipeline(db_client, pipeline_args)
        return
    if pipeline_args and pipeline_args.only_world_comments:
        I("Condition met: --only-world-comments flag was used only running ingestion pipeline.")
        run_ingestion_pipeline(db_client, pipeline_args)
        return
    run_ingestion_pipeline(db_client, pipeline_args)
    run_matching_pipeline(db_client)
    run_transformation_pipeline(db_client)
    run_load_pipeline(db_client)
    run_data_checks_pipeline(db_client)
    run_data_clean_pipeline(db_client)


if __name__ == "__main__":
    run_daily_pipeline()
