from api_helpers.clients import get_betfair_client, get_postgres_client
import pandas as pd
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..data_types.pipeline_status import (
    LoadTodaysData,
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
            pipeline_status.save_to_database()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load unioned results data",
                exception=e,
            )
            pipeline_status.save_to_database()
            raise e

    @check_pipeline_completion(LoadTodaysRaceTimes)
    def load_todays_race_times(self, pipeline_status):
        try:
            sql = LoadSQLGenerator.get_todays_race_times_sql()
            self.postgres_client.execute_query(sql)
            pipeline_status.save_to_database()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load today's race times",
                exception=e,
            )
            pipeline_status.save_to_database()
            raise e

    @check_pipeline_completion(LoadTodaysData)
    def load_todays_data(self, pipeline_status):
        try:
            sql = LoadSQLGenerator.get_todays_data_sql()
            self.postgres_client.execute_query(sql)
            pipeline_status.save_to_database()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load today's data",
                exception=e,
            )
            pipeline_status.save_to_database()
            raise e

    @check_pipeline_completion(LoadTodaysRaceTimes)
    def load_todays_betfair_market_ids(self, pipeline_status):

        try:
            bf_client = get_betfair_client()
            pg_client = get_postgres_client()       

            # Betfair market lookup (WIN/PLACE) per selection
            bf = bf_client.create_market_data()
            win = bf.loc[bf["market"] == "WIN", ["todays_betfair_selection_id", "market_id"]].rename(
                columns={"market_id": "market_id_win"}
            )
            place = bf.loc[bf["market"] == "PLACE", ["todays_betfair_selection_id", "market_id"]].rename(
                columns={"market_id": "market_id_place"}
            )
            bf_merged = pd.merge(win, place, on="todays_betfair_selection_id", how="outer")

            # Today's horses with race_id
            df = pg_client.fetch_data(
                """
                SELECT bf.*, td.race_id
                FROM bf_raw.today_horse bf
                JOIN public.todays_data td
                ON bf.horse_id = td.horse_id
                """
            )

            # Attach WIN/PLACE market ids and return one row per race
            market_ids = (
                df.merge(
                    bf_merged,
                    left_on="bf_horse_id",
                    right_on="todays_betfair_selection_id",
                    how="left",
                )[["race_id", "market_id_win", "market_id_place"]]
                .drop_duplicates(subset=["race_id"])
                .reset_index(drop=True)
            )

            if market_ids.empty:
                pipeline_status.add_error(
                    message="No market IDs found for today's Betfair data"
                )
            else:
                pg_client.store_data(
                    market_ids,
                    table="today_betfair_market_ids",
                    schema="bf_raw",
                truncate=True,
            )
            pipeline_status.save_to_database()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load today's Betfair market IDs",
                exception=e,
            )
            pipeline_status.save_to_database()
