from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date


class RaceMetadata(BaseModel):
    """Model for race metadata returned by the race info query"""

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, validate_assignment=True
    )

    race_id: Optional[int] = Field(None, description="Race identifier")
    race_title: Optional[str] = Field(None, max_length=132, description="Race title")
    race_type: Optional[str] = Field(
        None, max_length=32, description="Race type (e.g., 'Handicap', 'Maiden')"
    )
    course: Optional[str] = Field(None, max_length=132, description="Course name")
    distance: Optional[str] = Field(
        None, max_length=16, description="Race distance as string"
    )
    going: Optional[str] = Field(
        None, max_length=32, description="Going conditions (e.g., 'Good', 'Soft')"
    )
    surface: Optional[str] = Field(
        None, max_length=32, description="Surface type (e.g., 'Turf', 'All Weather')"
    )
    conditions: Optional[str] = Field(
        None, max_length=32, description="Race conditions"
    )
    race_class: Optional[int] = Field(
        None, description="Race class (smallint in DB, 1-6 typically)"
    )
    hcap_range: Optional[int] = Field(
        None, description="Handicap range (smallint in DB)"
    )
    age_range: Optional[str] = Field(
        None, max_length=32, description="Age range (e.g., '3yo+', '2yo only')"
    )
    first_place_prize_money: Optional[int] = Field(
        None, description="Prize money for first place"
    )
    race_time: Optional[datetime] = Field(None, description="Race start time")
    race_date: Optional[date] = Field(None, description="Race date")
    is_hcap: bool = Field(
        False, description="True if this is a handicap race (hcap_range is not null)"
    )
