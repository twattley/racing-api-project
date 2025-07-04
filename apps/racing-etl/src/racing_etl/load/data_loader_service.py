from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..data_types.pipeline_status import (
    IngestRPTodaysData,
    LoadTodaysRaceTimes,
    LoadUnionedData,
    check_pipeline_completion,
)
from ..load.generate_query import LoadSQLGenerator


class DataLoaderService:
    def __init__(self, postgres_client: IStorageClient):
        self.postgres_client = postgres_client

    @check_pipeline_completion(LoadUnionedData)
    def load_unioned_results_data(self, pipeline_status):
        try:
            sql = LoadSQLGenerator.get_unioned_results_data_upsert_sql()
            self.postgres_client.execute_query(sql)
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load unioned results data",
                exception=e,
            )
            raise e

    @check_pipeline_completion(LoadTodaysRaceTimes)
    def load_todays_race_times(self, pipeline_status):
        try:
            sql = LoadSQLGenerator.get_todays_race_times_sql()
            self.postgres_client.execute_query(sql)
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load today's race times",
                exception=e,
            )
            raise e

    @check_pipeline_completion(IngestRPTodaysData)
    def load_todays_data(self, pipeline_status):
        try:
            sql = LoadSQLGenerator.get_todays_data_sql()
            self.postgres_client.execute_query(sql)
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load today's data",
                exception=e,
            )
            raise e
