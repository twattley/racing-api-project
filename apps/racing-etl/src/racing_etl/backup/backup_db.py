from datetime import datetime

from ..storage.storage_client import get_storage_client

db_storage_client = get_storage_client("postgres")
s3_storage_client = get_storage_client("s3")

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


def backup_tables():
    day_of_week = datetime.now().day
    if day_of_week == 0:
        for schema, table in TABLES_TO_BACKUP:
            data = db_storage_client.fetch_data(f"SELECT * FROM {schema}.{table}")
            s3_storage_client.store_data(
                data,
                f"backup/{schema}/{table}.parquet",
            )


if __name__ == "__main__":
    backup_tables()
