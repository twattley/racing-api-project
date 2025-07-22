from datetime import date, datetime
from typing import List

from .base_entity import BaseEntity


class CollateralFormData(BaseEntity):
    finishing_position: str
    total_distance_beaten: str
    rating: int | None = None
    speed_figure: int | None = None
    horse_id: int
    unique_id: str
    race_id: int
    race_time: datetime
    race_date: date
    race_class: int | None = None
    distance: str | None = None
    conditions: str | None = None
    number_of_runners: int | None = None
    main_race_comment: str | None = None
    tf_comment: str | None = None


class HorseCollateralData(BaseEntity):
    horse_id: int
    horse_name: str
    distance_difference: float
    weight_difference: float
    current_official_rating: int
    collateral_form_data: List[CollateralFormData]


class CollateralFormResponse(BaseEntity):
    average_collateral_rating: int
    important_result_count: int
    valid_collateral_performance_count: int
    horse_collateral_data: List[HorseCollateralData]
