import pandas as pd
from api_helpers.clients import get_postgres_client
from api_helpers.helpers.processing_utils import ptr
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ....data_types.pipeline_status import PipelineStatus
from ....entity_matching.betfair.historical.generate_query import (
    MatchingBetfairSQLGenerator,
)
from ....entity_matching.interfaces.entity_matching_interface import IEntityMatching


class BetfairEntityMatcher(IEntityMatching):
    def __init__(
        self,
        storage_client: IStorageClient,
        sql_generator: MatchingBetfairSQLGenerator,
        pipeline_status: PipelineStatus,
    ):
        self.storage_client = storage_client
        self.sql_generator = sql_generator
        self.pipeline_status = pipeline_status

    def run_matching(self):
        rp_data, bf_data = self.fetch_data()
        matched_data = self.match_data(bf_data, rp_data)
        if matched_data.empty:
            self.pipeline_status.add_warning("No matched data found")
            self.pipeline_status.save_to_database()
            return
        entity_data = self.create_entity_data(matched_data)
        self.store_data(entity_data)

    def fetch_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        return ptr(
            lambda: self.storage_client.fetch_data(
                self.sql_generator.fetch_rp_entity_data()
            ),
            lambda: self.storage_client.fetch_data(
                self.sql_generator.fetch_bf_entity_data()
            ),
        )

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
            .str.replace(r"\s*\([^)]*\)", "", regex=True)
            .str.replace(r"[^a-z]", "", regex=True)
        )
        bf_data = bf_data.assign(
            formatted_horse_name=bf_data["horse_name"]
            .str.lower()
            .str.replace(" ", "")
            .str.replace("'", "")
            .str.replace(r"\s*\([^)]*\)", "", regex=True)
            .str.replace(r"[^a-z]", "", regex=True)
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
    service = BetfairEntityMatcher(get_postgres_client(), MatchingBetfairSQLGenerator())
    service.run_matching()
