from datetime import date, datetime
from typing import List

from .base_entity import BaseEntity


class CollateralFormData(BaseEntity):
    official_rating: int | None = 0
    finishing_position: str
    total_distance_beaten: str
    betfair_win_sp: float
    rating: int | None = None
    speed_figure: int | None = None
    horse_id: int
    unique_id: str
    race_id: int
    race_time: datetime
    race_date: date
    race_type: str | None = None
    race_class: int | None = None
    distance: str | None = None
    conditions: str | None = None
    going: str | None = None
    number_of_runners: int | None = None
    surface: str | None = None
    main_race_comment: str | None = None
    tf_comment: str | None = None
    tfr_view: str | None = None


class HorseCollateralData(BaseEntity):
    horse_id: int
    horse_name: str
    distance_difference: float
    betfair_win_sp: float
    official_rating: int | None = 0
    collateral_form_data: List[CollateralFormData]


class CollateralFormResponse(BaseEntity):
    average_collateral_rating: int
    important_result_count: int
    valid_collateral_performance_count: int
    horse_collateral_data: List[HorseCollateralData]
