import pandas as pd
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
        matched_data, unmatched_data = self.match_data(bf_data, rp_data)
        if not unmatched_data.empty:
            for _, row in unmatched_data.iterrows():
                self.pipeline_status.add_warning(
                    f"BF horse {row['horse_name']} ({row['unique_id']}) not matched"
                )

        entity_data = self.create_entity_data(matched_data)
        self.store_data(entity_data, unmatched_data)
        self.pipeline_status.save_to_database()

    def fetch_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        return ptr(
            lambda: self.storage_client.fetch_data(
                self.sql_generator.fetch_rp_entity_data()
            ),
            lambda: self.storage_client.fetch_data(
                self.sql_generator.fetch_bf_entity_data()
            ),
        )

    def store_data(self, entity_data: pd.DataFrame, unmatched_data: pd.DataFrame):
        upsert_sql = self.sql_generator.define_upsert_sql()
        self.storage_client.upsert_data(
            data=entity_data,
            schema="bf_raw",
            table_name="results_data",
            unique_columns=["unique_id"],
            use_base_table=True,
            upsert_procedure=upsert_sql,
        )
        unmatched_data["processed_at"] = pd.Timestamp.now()
        self.storage_client.store_latest_data(
            data=unmatched_data,
            schema="data_quality",
            table=f"bf_unmatched_horses_historical",
            unique_columns=["unique_id"],
        )

    def match_data(
        self, bf_data: pd.DataFrame, rp_data: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:

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

        # Get matched data with inner join
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
                "unique_id_bf",
                "horse_id",
                "race_id",
            ]
        ].rename(columns={"horse_name_bf": "horse_name", "unique_id_bf": "unique_id"})

        # Get unmatched data using left join and filtering
        all_matches = pd.merge(
            bf_data,
            rp_data,
            on=["formatted_horse_name", "race_date"],
            how="left",
            suffixes=("_bf", "_rp"),
            indicator=True,
        )
        unmatched_data = all_matches[all_matches["_merge"] == "left_only"].copy()
        unmatched_data = unmatched_data[
            [
                "horse_name_bf",
                "race_time",
                "price_change",
                "unique_id_bf",
                "formatted_horse_name",
                "race_date",
            ]
        ].rename(columns={"horse_name_bf": "horse_name", "unique_id_bf": "unique_id"})

        return direct_matches, unmatched_data

    def create_entity_data(self, matched_data: pd.DataFrame) -> pd.DataFrame:
        return matched_data.assign(
            created_at=pd.Timestamp.now(),
        )
