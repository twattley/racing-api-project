import random
import time
from pathlib import Path

from api_helpers.config import config
from api_helpers.helpers.file_utils import create_todays_log_file
from api_helpers.helpers.logging_config import I

from api_helpers.clients import get_postgres_client

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
    """Set a random sleep time between 0 and 10 minutes."""
    sleep_time = random.uniform(0, 600)
    I(f"Sleeping for {sleep_time:.2f} seconds before starting the pipeline...")
    time.sleep(sleep_time)


def run_daily_pipeline(db_client):
    set_random_sleep_time()
    run_ingestion_pipeline(db_client)
    run_matching_pipeline(db_client)
    run_transformation_pipeline(db_client)
    run_load_pipeline(db_client)
    run_data_checks_pipeline(db_client)
    run_data_clean_pipeline(db_client)



if __name__ == "__main__":
    pg_client = get_postgres_client()
    create_centralized_log_files()
    run_daily_pipeline(pg_client)
