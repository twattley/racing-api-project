import argparse

from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.clients.s3_client import S3Client
from api_helpers.helpers.logging_config import I, W

TABLES_TO_BACKUP = [
    # -----RP-----
    ("rp_raw", "results_data"),
    ("rp_raw", "results_links"),
    ("rp_raw", "results_errors"),
    ("rp_raw", "results_data_world"),
    ("rp_raw", "void_races"),
    # -----TF-----
    ("tf_raw", "results_data"),
    ("tf_raw", "results_links"),
    ("tf_raw", "results_data_world"),
    ("tf_raw", "results_errors"),
    # -----BF-----
    ("bf_raw", "results_data"),
    ("bf_raw", "raw_data"),
    # -----Entities-----
    ("entities", "course"),
    ("entities", "country"),
    ("entities", "horse"),
    ("entities", "jockey"),
    ("entities", "trainer"),
    ("entities", "owner"),
    ("entities", "sire"),
    ("entities", "dam"),
    ("entities", "surface"),
    # -----Public-----
    ("public", "results_data"),
]


def backup_tables(
    db_storage_client: PostgresClient,
    s3_storage_client: S3Client,
    pipeline_args: argparse.Namespace | None = None,
):
    if pipeline_args.backup_tables:
        I("Starting backup of tables to S3.")
        for schema, table in TABLES_TO_BACKUP:
            I(f"Backing up table: {schema}.{table}")
            data = db_storage_client.fetch_data(f"SELECT * FROM {schema}.{table}")
            s3_storage_client.store_data(
                data,
                f"backup/{schema}/{table}.parquet",
            )
    else:
        W("Skipping backup of tables: --backup-tables flag was NOT used.")
        return
    I("Backup completed successfully.")
