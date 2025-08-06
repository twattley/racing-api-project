from datetime import date, datetime
from typing import List, Optional

from pydantic import Field

from .base_model import BaseRaceModel


class RaceTimeEntry(BaseRaceModel):
    """Model for race time entries (works for both race_times queries)"""

    race_id: Optional[int] = Field(None, description="Race identifier")
    race_time: Optional[datetime] = Field(None, description="Race start time")
    race_date: Optional[date] = Field(None, description="Race date")
    race_title: Optional[str] = Field(None, max_length=132, description="Race title")
    race_type: Optional[str] = Field(None, max_length=32, description="Race type")
    race_class: Optional[int] = Field(None, description="Race class (smallint)")
    distance: Optional[str] = Field(None, max_length=16, description="Race distance")
    going: Optional[str] = Field(None, max_length=32, description="Going conditions")
    number_of_runners: Optional[int] = Field(
        None, description="Number of runners (smallint)"
    )
    hcap_range: Optional[int] = Field(None, description="Handicap range (smallint)")
    age_range: Optional[str] = Field(None, max_length=32, description="Age range")
    surface: Optional[str] = Field(None, max_length=32, description="Surface type")
    total_prize_money: Optional[int] = Field(None, description="Total prize money")
    first_place_prize_money: Optional[int] = Field(
        None, description="First place prize money"
    )
    course_id: Optional[int] = Field(None, description="Course ID (smallint)")
    course: Optional[str] = Field(None, description="Course name")
    is_hcap: bool = Field(False, description="True if handicap race")


class RaceTimesResponse(BaseRaceModel):
    """Container for race times with analysis capabilities"""

    data: List[RaceTimeEntry] = Field(
        default_factory=list, description="List of race times"
    )

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)
