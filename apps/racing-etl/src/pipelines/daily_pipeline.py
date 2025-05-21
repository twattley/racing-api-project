from src.storage.storage_client import get_storage_client
from src.pipelines.ingestion_pipeline import run_ingestion_pipeline
from src.pipelines.matching_pipeline import run_matching_pipeline
from src.pipelines.transformation_pipeline import run_transformation_pipeline
from src.pipelines.load_pipeline import run_load_pipeline
from src.pipelines.data_checks_pipeline import run_data_checks_pipeline
from src.backup.backup_db import backup_tables


def run_daily_pipeline():
    db_storage_client = get_storage_client("postgres")
    s3_storage_client = get_storage_client("s3")
    run_ingestion_pipeline(db_storage_client)
    run_matching_pipeline(db_storage_client)
    run_transformation_pipeline(db_storage_client)
    run_load_pipeline(db_storage_client, s3_storage_client)
    run_data_checks_pipeline(db_storage_client)
    backup_tables()


if __name__ == "__main__":
    run_daily_pipeline()
