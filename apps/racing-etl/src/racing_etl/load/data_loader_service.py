from datetime import datetime

from api_helpers.clients import get_postgres_client, get_s3_client
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..load.generate_query import LoadSQLGenerator


class DataLoaderService:
    def __init__(self, db_client: IStorageClient, s3_client: IStorageClient):
        self.db_client = db_client
        self.s3_client = s3_client
        self.folder_name = f"today/{datetime.now().strftime('%Y_%m_%d')}/race_data"

    def load_unioned_results_data(self):
        sql = LoadSQLGenerator.get_unioned_results_data_upsert_sql()
        self.db_client.execute_query(sql)

    def load_todays_race_times(self):
        sql = LoadSQLGenerator.get_todays_race_times_sql()
        df = self.db_client.fetch_data(sql)
        file_name = f"{self.folder_name}/race_times.parquet"
        print(f"Storing {file_name}")
        self.s3_client.store_data(df, file_name)

    def load_todays_data(self):
        sql = LoadSQLGenerator.get_todays_data_sql()
        df = self.db_client.fetch_data(sql)
        file_name = f"{self.folder_name}/results_data.parquet"
        print(f"Storing {file_name}")
        self.s3_client.store_data(df, file_name)

    def load_betting_results(self):
        self.s3_client.store_data(
            self.db_client.fetch_data(
                """
            SELECT 
                race_date, 
                race_id, 
                horse_id, 
                betfair_win_sp, 
                betfair_place_sp, 
                number_of_runners, 
                finishing_position
            FROM 
                public.results_data;
            """
            ),
            "historical/betting_results/results.parquet",
        )
