from datetime import datetime

from src.storage.storage_client import PostgresClient, S3Client, get_storage_client

postgres_client: PostgresClient = get_storage_client("postgres")
s3_client: S3Client = get_storage_client("s3")

FOLDER = "db_backup"
FILE_TYPE = "parquet"


def load_entity_data():
    SCHEMA = "public"
    for table in [
        "horse",
        "jockey",
        "trainer",
        "owner",
        "sire",
        "dam",
        "course",
        "country",
    ]:
        df = postgres_client.fetch_data(f"SELECT * FROM {SCHEMA}.{table}")
        s3_client.store_data(df, f"{FOLDER}/{SCHEMA}/{table}.{FILE_TYPE}")


def load_main_data_tables():
    year = datetime.now().year
    for schema, table in [
        ("rp_raw", "performance_data"),
        ("rp_raw", "non_uk_ire_performance_data"),
        ("tf_raw", "performance_data"),
        ("tf_raw", "non_uk_ire_performance_data"),
        ("public", "performance_data"),
        ("public", "unioned_performance_data"),
    ]:
        df = postgres_client.fetch_data(
            f"""
            SELECT * 
            FROM {schema}.{table}
            WHERE race_date >= '{year}-01-01' AND race_date < '{year + 1}-01-01'
            """
        )
        df = df.drop(columns=["unique_id"])
        s3_client.store_data(df, f"{FOLDER}/{schema}/{year}_{table}.{FILE_TYPE}")


def load_betfair_data_tables():
    year = datetime.now().year
    for schema, table in [
        ("bf_raw", "historical_price_data"),
        ("bf_raw", "matched_historical_price_data"),
    ]:
        df = postgres_client.fetch_data(
            f"""
            SELECT * 
            FROM {schema}.{table}
            WHERE race_date >= '{year}-01-01' AND race_date < '{year + 1}-01-01'
            """
        )
        df = df.drop(columns=["bf_unique_id"])
        s3_client.store_data(df, f"{FOLDER}/{schema}/{year}_{table}.{FILE_TYPE}")


if __name__ == "__main__":
    load_entity_data()
    load_main_data_tables()
    load_betfair_data_tables()
