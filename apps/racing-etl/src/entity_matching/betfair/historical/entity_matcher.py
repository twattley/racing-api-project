from api_helpers.interfaces.storage_client_interface import IStorageClient
import pandas as pd
from api_helpers.helpers.logging_config import W
from api_helpers.helpers.processing_utils import ptr
from src.storage.storage_client import get_storage_client
from src.entity_matching.interfaces.entity_matching_interface import IEntityMatching
from src.entity_matching.betfair.historical.generate_query import (
    MatchingBetfairSQLGenerator,
)


class BetfairEntityMatcher(IEntityMatching):
    def __init__(
        self,
        storage_client: IStorageClient,
        sql_generator: MatchingBetfairSQLGenerator,
    ):
        self.storage_client = storage_client
        self.sql_generator = sql_generator

    def run_matching(self):
        rp_data, bf_data = self.fetch_data()
        matched_data = self.match_data(bf_data, rp_data)
        if matched_data.empty:
            W("No data matched")
            return
        entity_data = self.create_entity_data(matched_data)
        self.store_data(entity_data)

    def fetch_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        return ptr(
            lambda: self.storage_client.fetch_data(
                "SELECT * FROM entities.matching_historical_rp_entities"
            ),
            lambda: self.storage_client.fetch_data(
                "SELECT * FROM entities.matching_historical_bf_entities"
            ),
        )  # type: ignore

    def store_data(self, entity_data: pd.DataFrame):
        upsert_sql = self.sql_generator.define_upsert_sql()
        self.storage_client.upsert_data(
            data=entity_data,
            schema="bf_raw",
            table_name="results_data",
            unique_columns=["unique_id"],
            use_base_table=True,
            upsert_procedure=upsert_sql,
        )

    def match_data(self, bf_data: pd.DataFrame, rp_data: pd.DataFrame) -> pd.DataFrame:
        rp_data = rp_data.assign(
            formatted_horse_name=rp_data["horse_name"]
            .str.lower()
            .str.replace(" ", "")
            .str.replace("'", "")
            .str.replace(r'\s*\([^)]*\)', '', regex=True)
            .str.replace(r'[^a-z]', '', regex=True)
        )
        bf_data = bf_data.assign(
            formatted_horse_name=bf_data["horse_name"]
            .str.lower()
            .str.replace(" ", "")
            .str.replace("'", "")
            .str.replace(r'\s*\([^)]*\)', '', regex=True)
            .str.replace(r'[^a-z]', '', regex=True)
        )
        direct_matches = pd.merge(
            bf_data,
            rp_data,
            on=["formatted_horse_name", "race_date"],
            how="inner",
            suffixes=("_bf", "_rp"),
        )
        direct_matches = direct_matches[
            [
                "horse_name_bf",
                "race_time",
                "price_change",
                "unique_id",
                "horse_id",
                "race_id",
            ]
        ].rename(columns={"horse_name_bf": "horse_name"})

        return direct_matches
    
    def create_entity_data(self, matched_data: pd.DataFrame) -> pd.DataFrame:
        return matched_data.assign(
            created_at=pd.Timestamp.now(),
        )


if __name__ == "__main__":
    service = BetfairEntityMatcher(
        get_storage_client("postgres"), MatchingBetfairSQLGenerator()
    )
    service.run_matching()
