from typing import Literal

import pandas as pd
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import PipelineStatus
from ...entity_matching.helpers.string_formatting import format_horse_name
from ...entity_matching.interfaces.entity_matching_interface import IEntityMatching
from ...entity_matching.timeform.generate_query import MatchingTimeformSQLGenerator


class TimeformEntityMatcher(IEntityMatching):
    def __init__(
        self,
        storage_client: IStorageClient,
        sql_generator: MatchingTimeformSQLGenerator,
        matching_type: Literal["historical", "todays"],
        log_object: PipelineStatus,
    ):
        self.storage_client = storage_client
        self.sql_generator = sql_generator
        self.matching_type = matching_type
        self.log_object = log_object

    def run_matching(self):
        rp_data, tf_data = self.fetch_data()
        if rp_data.empty:
            I("No RP data to match")
            return
        matched_data = self.match_data(rp_data, tf_data)
        if matched_data.empty:
            self.log_object.add_warning("No matched data found")
            return
        entity_data = self.create_entity_data(matched_data)
        self.store_data(entity_data)
        self.log_object.save_to_database()

    def fetch_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        return ptr(
            lambda: self.storage_client.fetch_data(
                self.sql_generator.fetch_rp_entity_data(self.matching_type)
            ),
            lambda: self.storage_client.fetch_data(
                self.sql_generator.fetch_tf_entity_data(self.matching_type)
            ),
        )

    def store_data(self, entity_data: list[dict[str, pd.DataFrame]]):
        for entity in entity_data:
            upsert_sql = self.sql_generator.get_upsert_sql(entity["entity"])
            self.storage_client.upsert_data(
                data=entity["data"],
                schema="entities",
                table_name=entity["entity"],
                unique_columns=["rp_id"],
                upsert_procedure=upsert_sql,
            )

    def create_entity_data(self, data: pd.DataFrame) -> list[dict[str, list[dict]]]:
        entity_data_dicts = []
        for i in ["horse", "sire", "dam", "jockey", "trainer"]:
            entity_data = data[
                [
                    f"{i}_name_x",
                    f"{i}_id_x",
                    f"{i}_id_y",
                ]
            ]
            entity_data = entity_data.rename(
                columns={
                    f"{i}_name_x": "name",
                    f"{i}_id_x": "rp_id",
                    f"{i}_id_y": "tf_id",
                }
            ).drop_duplicates()
            entity_data_dicts.append({"entity": i, "data": entity_data})

        owner_data = (
            data[["owner_name", "owner_id"]]
            .drop_duplicates()
            .rename(
                columns={
                    "owner_name": "name",
                    "owner_id": "rp_id",
                }
            )
        )
        entity_data_dicts.append({"entity": "owner", "data": owner_data})
        return entity_data_dicts

    def match_data(self, rp_data: pd.DataFrame, tf_data: pd.DataFrame) -> pd.DataFrame:
        I(f"Matching {rp_data.shape[0]} RP horses")
        rp_data = rp_data.pipe(format_horse_name)
        tf_data = tf_data.pipe(format_horse_name)
        unmatched_data = 0
        matched_data_rows = []
        for i in rp_data.itertuples():
            tf_matching_data = tf_data[
                (tf_data["race_date"] == i.race_date)
                & (tf_data["course_id"] == i.course_id)
                & (tf_data["filtered_horse_name"] == i.filtered_horse_name)
            ]
            if not tf_matching_data.empty:
                one_row_df = pd.DataFrame.from_records([i._asdict()])
                matched_data = one_row_df.merge(
                    tf_matching_data,
                    on=["race_date", "course_id", "filtered_horse_name"],
                    how="left",
                )
                matched_data_rows.append(matched_data)
            else:
                unmatched_data += 1

        self.log_object.add_warning(f"Number of unmatched rows: {unmatched_data}")
        if len(matched_data_rows) > 0:
            return pd.concat(matched_data_rows)
        else:
            return pd.DataFrame()
