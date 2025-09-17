import random
import time
from pathlib import Path
import argparse
from typing import Sequence

from api_helpers.config import config
from api_helpers.helpers.file_utils import create_todays_log_file
from api_helpers.helpers.logging_config import I

from api_helpers.clients import get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient

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


def reset_monitoring_tables(db_client: PostgresClient, stage_ids: list[int]):
    """Reset monitoring tables before running pipelines."""
    if not stage_ids:
        I("No stage IDs provided for reset. Skipping monitoring table reset.")
        return
    I(f"Resetting monitoring tables for stage_ids={stage_ids} ...")
    # Build a safe numeric IN clause
    placeholder_list = ",".join(str(int(s)) for s in stage_ids)
    query = f"""
        UPDATE monitoring.pipeline_status
           SET date_processed = now() - interval '1 day'
         WHERE stage_id IN ({placeholder_list});
    """
    db_client.execute_query(query)
    I("Monitoring tables reset.")


def set_random_sleep_time():
    """Set a random sleep time between 0 and 10 minutes."""
    sleep_time = random.uniform(0, 600)
    I(f"Sleeping for {sleep_time:.2f} seconds before starting the pipeline...")
    time.sleep(sleep_time)


def run_daily_pipeline(db_client, random_sleep: bool = True):
    """Run the end-to-end daily pipeline."""
    if random_sleep:
        set_random_sleep_time()
    # run_ingestion_pipeline(db_client)
    # run_matching_pipeline(db_client)
    # run_transformation_pipeline(db_client)
    run_load_pipeline(db_client)
    run_data_checks_pipeline(db_client)
    run_data_clean_pipeline(db_client)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run racing ETL daily pipeline (optionally resetting monitoring stages first)."
    )
    parser.add_argument(
        "--reset-stage-ids",
        "-r",
        metavar="ID",
        nargs="*",
        help="Stage IDs to reset. Provide as space-separated values or comma-separated string. Example: -r 1 2 3 OR -r 1,2,3",
    )
    parser.add_argument(
        "--no-random-sleep",
        action="store_true",
        help="Disable the random pre-run sleep.",
    )
    return parser.parse_args()


def normalize_stage_ids(raw: Sequence[str] | None) -> list[int]:
    if not raw:
        return []
    ids: list[int] = []
    for token in raw:
        for part in token.split(","):
            part = part.strip()
            if part:
                ids.append(int(part))
    # Preserve order but remove duplicates
    seen = {}
    for i in ids:
        if i not in seen:
            seen[i] = True
    return list(seen.keys())


def main():
    args = parse_args()
    stage_ids = normalize_stage_ids(args.reset_stage_ids)
    pg_client = get_postgres_client()
    create_centralized_log_files()
    if stage_ids:
        reset_monitoring_tables(pg_client, stage_ids)
    else:
        I("No stage IDs supplied. Skipping monitoring reset.")
    run_daily_pipeline(pg_client, random_sleep=not args.no_random_sleep)


if __name__ == "__main__":
    main()
