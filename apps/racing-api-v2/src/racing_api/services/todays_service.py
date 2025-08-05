from datetime import datetime

from fastapi import Depends

from ..models.form_data import InputRaceFilters
from ..repository.todays_repository import TodaysRepository, get_todays_repository
from .base_service import BaseService
from .transformation_service import TransformationService


class TodaysService(BaseService):
    todays_repository: TodaysRepository
    transformation_service: TransformationService

    def __init__(
        self,
        todays_repository: TodaysRepository,
        transformation_service: TransformationService,
    ):
        self.todays_repository = todays_repository
        self.transformation_service = transformation_service

    def get_todays_races(self):
        data = self.todays_repository.get_todays_races()
        if data.empty:
            print("No data")
        return self.format_todays_races(data[data["race_time"] >= datetime.now()])

    def get_race_by_id(self, filters: InputRaceFilters):
        data = self.todays_repository.get_todays_race_data()
        horse_ids = data[
            (data["data_type"] == "today") & (data["race_id"] == filters.race_id)
        ]["horse_id"].tolist()
        todays_data = data[data["horse_id"].isin(horse_ids)]

        race_details, combined_data = self.merge_form_data(
            todays_data,
            filters,
            self.transformation_service.calculate,
        )

        return self.format_todays_form_data(
            combined_data,
            filters,
            race_details,
        )


def get_todays_service(
    todays_repository: TodaysRepository = Depends(get_todays_repository),
):
    transformation_service = TransformationService()
    return TodaysService(todays_repository, transformation_service)
