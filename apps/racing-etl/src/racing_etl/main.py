import argparse
import random
import time
from pathlib import Path
from typing import Sequence

from api_helpers.clients import get_postgres_client
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.config import config
from api_helpers.helpers.file_utils import create_todays_log_file
from api_helpers.helpers.logging_config import I

from .data_types.pipeline_status_types import JOB_REGISTRY
from .pipelines.clean_tables_pipeline import run_clean_tables_pipeline
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
    projects = ["racing-etl", "trader"]

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


def reset_specific_jobs(db_client: PostgresClient, job_names: list[str]):
    """Reset specific jobs by name using the JOB_REGISTRY."""
    if not job_names:
        return

    # Validate job names and collect (job_id, source_id) pairs
    invalid_jobs = [j for j in job_names if j not in JOB_REGISTRY]
    if invalid_jobs:
        available = ", ".join(sorted(JOB_REGISTRY.keys()))
        raise ValueError(
            f"Unknown job(s): {', '.join(invalid_jobs)}\n"
            f"Available jobs: {available}"
        )

    job_specs = [JOB_REGISTRY[j] for j in job_names]

    I(f"Resetting specific jobs: {', '.join(job_names)}")

    # Build WHERE clause for each (job_id, source_id) pair
    conditions = " OR ".join(
        f"(job_id = {job_id} AND source_id = {source_id})"
        for job_id, source_id in job_specs
    )

    query = f"""
        UPDATE monitoring.pipeline_status
           SET date_processed = now() - interval '1 day'
         WHERE ({conditions})
           AND date_processed = CURRENT_DATE;
    """
    db_client.execute_query(query)
    I("Specific jobs reset.")


def list_available_jobs():
    """Print all available job names."""
    print("\nAvailable jobs:")
    print("-" * 50)

    # Group by prefix
    groups = {}
    for job_name in sorted(JOB_REGISTRY.keys()):
        prefix = job_name.split("-")[0]
        if prefix not in groups:
            groups[prefix] = []
        groups[prefix].append(job_name)

    for prefix, jobs in groups.items():
        print(f"\n{prefix.upper()}:")
        for job in jobs:
            print(f"  {job}")
    print()


def set_random_sleep_time():
    """Set a random sleep time up to 1 hour before starting the pipeline."""
    sleep_time = random.uniform(0, 3600)
    I(f"Sleeping for {sleep_time:.2f} seconds before starting the pipeline...")
    time.sleep(sleep_time)


def run_daily_pipeline(db_client, random_sleep: bool = True, headless: bool = True):
    """Run the end-to-end daily pipeline."""
    # if random_sleep:
    #     set_random_sleep_time()
    run_ingestion_pipeline(db_client, headless=headless)
    run_matching_pipeline(db_client)
    run_transformation_pipeline(db_client)
    run_load_pipeline(db_client)
    run_clean_tables_pipeline(db_client)
    run_data_checks_pipeline(db_client)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run racing ETL daily pipeline (optionally resetting monitoring stages first).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline (skip already-completed jobs)
  python -m racing_etl.main

  # Force re-run specific job(s)
  python -m racing_etl.main --job rp-results-data
  python -m racing_etl.main --job rp-results-data tf-results-data

  # List all available job names
  python -m racing_etl.main --list-jobs

  # Force re-run all jobs in a stage (legacy)
  python -m racing_etl.main --reset-stage-ids 1
        """,
    )
    parser.add_argument(
        "--reset-stage-ids",
        "-r",
        metavar="ID",
        nargs="*",
        help="Stage IDs to reset. Provide as space-separated values or comma-separated string. Example: -r 1 2 3 OR -r 1,2,3",
    )
    parser.add_argument(
        "--job",
        "-j",
        metavar="NAME",
        nargs="+",
        help="Specific job(s) to force re-run. Use --list-jobs to see available names.",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="List all available job names and exit.",
    )
    parser.add_argument(
        "--no-random-sleep",
        action="store_true",
        help="Disable the random pre-run sleep.",
    )
    parser.add_argument(
        "--headless",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Run browsers in headless mode (default: True). Use --headless false for debugging.",
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

    # Handle --list-jobs
    if args.list_jobs:
        list_available_jobs()
        return

    stage_ids = normalize_stage_ids(args.reset_stage_ids)
    pg_client = get_postgres_client()
    create_centralized_log_files()

    # Reset by stage IDs (legacy)
    if stage_ids:
        reset_monitoring_tables(pg_client, stage_ids)

    # Reset specific jobs by name
    if args.job:
        reset_specific_jobs(pg_client, args.job)

    if not stage_ids and not args.job:
        I("No resets requested. Running pipeline (skipping completed jobs).")

    run_daily_pipeline(
        pg_client, random_sleep=not args.no_random_sleep, headless=args.headless
    )


if __name__ == "__main__":
    main()
