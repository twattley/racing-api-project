from datetime import date, datetime
from typing import List, Optional

from ..models.base_entity import BaseEntity


class TodaysRaceData(BaseEntity):
    race_id: int
    race_time: datetime
    race_title: str
    race_type: Optional[str]
    race_class: Optional[int]
    distance: str
    distance_yards: float
    distance_meters: float
    distance_kilometers: float
    conditions: str
    going: str
    number_of_runners: int
    hcap_range: Optional[str]
    age_range: Optional[str]
    surface: Optional[str]
    total_prize_money: Optional[int]
    first_place_prize_money: Optional[int]


class TodaysCourseData(BaseEntity):
    course: str
    course_id: int
    races: List[TodaysRaceData]


class TodaysRacesResponse(BaseEntity):
    race_date: date
    courses: List[TodaysCourseData]
