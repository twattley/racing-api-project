from datetime import datetime

import pandas as pd
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ....data_types.pipeline_status import PipelineStatus
from ....entity_matching.betfair.today.generate_query import MatchingBetfairSQLGenerator
from ....entity_matching.helpers.string_formatting import format_horse_name
from ....entity_matching.interfaces.entity_matching_interface import IEntityMatching


class BetfairEntityMatcher(IEntityMatching):
    def __init__(
        self,
        storage_client: IStorageClient,
        sql_generator: MatchingBetfairSQLGenerator,
        log_object: PipelineStatus,
    ):
        self.storage_client = storage_client
        self.sql_generator = sql_generator
        self.log_object = log_object

    def run_matching(self):
        rp_data, bf_data = self.fetch_data()
        if rp_data.empty:
            I("No RP data to match")
            return
        matched_data = self.match_data(bf_data, rp_data)
        if matched_data.empty:
            self.log_object.add_warning("No data matched")
            self.log_object.save_to_database()
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
            schema="entities",
            table_name="todays_betfair_horse_ids",
            unique_columns=["horse_id", "bf_horse_id"],
            upsert_procedure=upsert_sql,
        )

    def create_entity_data(self, data: pd.DataFrame) -> list[dict[str, pd.DataFrame]]:
        entity_data = data[
            [
                "horse_id_x",
                "horse_id_y",
            ]
        ].drop_duplicates()
        entity_data = entity_data.assign(race_date=datetime.now().date())
        return entity_data.rename(
            columns={
                "horse_id_x": "horse_id",
                "horse_id_y": "bf_horse_id",
            }
        )

    def match_data(self, bf_data: pd.DataFrame, rp_data: pd.DataFrame) -> pd.DataFrame:
        rp_data = rp_data.pipe(format_horse_name)
        bf_data = bf_data.pipe(format_horse_name)
        matched_data_rows = []
        for i in rp_data.itertuples():
            bf_matching_data = bf_data[
                (bf_data["filtered_horse_name"] == i.filtered_horse_name)
            ]
            if not bf_matching_data.empty:
                one_row_df = pd.DataFrame.from_records([i._asdict()])
                matched_data = one_row_df.merge(
                    bf_matching_data,
                    on=["race_time", "filtered_horse_name"],
                    how="left",
                )
                matched_data_rows.append(matched_data)

        if len(matched_data_rows) > 0:
            matches = pd.concat(matched_data_rows)
            matches = matches[matches["course_id_x"] == matches["course_id_y"]]
            unmatched = rp_data[~rp_data["horse_id"].isin(matches["horse_id_x"])]
            if not unmatched.empty:
                self.log_object.add_warning(f"Unmatched RP data {unmatched.shape[0]}")
                self.log_object.add_warning(f"Unmatched BF data {unmatched}")
            else:
                I("All RP data matched")
            self.log_object.save_to_database()
            return matches
        else:
            return pd.DataFrame()
