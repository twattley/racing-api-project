from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..load.generate_query import LoadSQLGenerator


class DataLoaderService:
    def __init__(self, postgres_client: IStorageClient):
        self.postgres_client = postgres_client

    def load_unioned_results_data(self):
        sql = LoadSQLGenerator.get_unioned_results_data_upsert_sql()
        self.postgres_client.execute_query(sql)

    def load_todays_race_times(self):
        sql = LoadSQLGenerator.get_todays_race_times_sql()
        self.postgres_client.execute_query(sql)

    def load_todays_data(self):
        sql = LoadSQLGenerator.get_todays_data_sql()
        self.postgres_client.execute_query(sql)
