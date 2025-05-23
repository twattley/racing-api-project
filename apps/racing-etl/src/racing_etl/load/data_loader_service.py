from datetime import datetime

from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..load.generate_query import LoadSQLGenerator
from ..storage.storage_client import get_storage_client


class DataLoaderService:
    def __init__(
        self, db_storage_client: IStorageClient, s3_storage_client: IStorageClient
    ):
        self.db_storage_client = db_storage_client
        self.s3_storage_client = s3_storage_client
        self.folder_name = f"today/{datetime.now().strftime('%Y_%m_%d')}/race_data"

    def load_unioned_results_data(self):
        sql = LoadSQLGenerator.get_unioned_results_data_upsert_sql()
        self.db_storage_client.execute_query(sql)

    def load_todays_race_times(self):
        sql = LoadSQLGenerator.get_todays_race_times_sql()
        df = self.db_storage_client.fetch_data(sql)
        file_name = f"{self.folder_name}/race_times.parquet"
        print(f"Storing {file_name}")
        self.s3_storage_client.store_data(df, file_name)

    def load_todays_data(self):
        sql = LoadSQLGenerator.get_todays_data_sql()
        df = self.db_storage_client.fetch_data(sql)
        file_name = f"{self.folder_name}/results_data.parquet"
        print(f"Storing {file_name}")
        self.s3_storage_client.store_data(df, file_name)


if __name__ == "__main__":
    data_loader = DataLoaderService(
        db_storage_client=get_storage_client("postgres"),
        s3_storage_client=get_storage_client("s3"),
    )
    data_loader.load_unioned_results_data()
    data_loader.load_todays_race_times()
    data_loader.load_todays_data()
