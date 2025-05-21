from typing import Literal

from api_helpers.helpers.logging_config import I
from api_helpers.interfaces.storage_client_interface import IStorageClient

from src.raw.interfaces.course_ref_data_interface import ICourseRefData


class CourseRefData(ICourseRefData):
    REF_TABLE = "entities.course"
    UK_IRE_COUNTRY_CODES = ("1", "2")

    def __init__(
        self, source: Literal["rp", "tf"], storage_client: IStorageClient
    ) -> None:
        self.source = source
        self.storage_client = storage_client

    def get_uk_ire_course_ids(self) -> dict[str, str]:
        I(f"Fetching UK and Ireland course IDs for {self.source}")
        df = self.storage_client.fetch_data(
            f"""
            SELECT DISTINCT ON({self.source}_id) {self.source}_id, {self.source}_name 
            FROM {self.REF_TABLE} 
            WHERE country_id IN {self.UK_IRE_COUNTRY_CODES}
            """
        )
        return dict(zip(df[f"{self.source}_id"], df[f"{self.source}_name"]))

    def get_world_course_ids(self) -> dict[str, str]:
        I(f"Fetching world course IDs for {self.source}")
        df = self.storage_client.fetch_data(
            f"""
            SELECT DISTINCT ON({self.source}_id) {self.source}_id, {self.source}_name 
            FROM {self.REF_TABLE} 
            WHERE country_id NOT IN {self.UK_IRE_COUNTRY_CODES}
            """
        )
        return dict(zip(df[f"{self.source}_id"], df[f"{self.source}_name"]))

    def get_uk_ire_course_names(self) -> set[str]:
        I(f"Fetching UK and Ireland course names for {self.source}")
        df = self.storage_client.fetch_data(
            f"""
            SELECT DISTINCT ON({self.source}_id) {self.source}_id, {self.source}_name 
            FROM {self.REF_TABLE} 
            WHERE country_id IN {self.UK_IRE_COUNTRY_CODES}
            """
        )
        return set(df[f"{self.source}_name"])

    def get_world_course_names(self) -> set[str]:
        I(f"Fetching world course names for {self.source}")
        df = self.storage_client.fetch_data(
            f"""
            SELECT DISTINCT ON({self.source}_id) {self.source}_id, {self.source}_name 
            FROM {self.REF_TABLE} 
            WHERE country_id NOT IN {self.UK_IRE_COUNTRY_CODES}
            """
        )
        return set(df[f"{self.source}_name"])
