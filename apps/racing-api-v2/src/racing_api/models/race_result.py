from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base_model import BaseRaceModel


class RaceResult(BaseRaceModel):
    """Model for a single horse's complete race result"""
    
    
    race_time: datetime = Field(..., description="Race start time")
    race_date: date = Field(..., description="Race date")
    race_title: Optional[str] = Field(None, max_length=132, description="Race title")§
    race_type: Optional[str] = Field(None, max_length=32, description="Race type")
    race_class: Optional[int] = Field(None, description="Race class (smallint)")
    distance: Optional[str] = Field(None, max_length=16, description="Race distance")§
    conditions: Optional[str] = Field(None, max_length=32, description="Race conditions")
    going: Optional[str] = Field(None, max_length=32, description="Going conditions")
    number_of_runners: Optional[int] = Field(None, description="Number of runners (smallint)")
    hcap_range: Optional[int] = Field(None, description="Handicap range (smallint)")
    age_range: Optional[str] = Field(None, max_length=32, description="Age range")
    surface: Optional[str] = Field(None, max_length=32, description="Surface type")
    total_prize_money: Optional[int] = Field(None, description="Total prize money")
    main_race_comment: Optional[str] = Field(None, description="Main race comment (text)")
    course_id: int = Field(..., description="Course ID (smallint)")
    course: Optional[str] = Field(None, max_length=132, description="Course name")
    race_id: int = Field(..., description="Race identifier")
    horse_name: str = Field(..., max_length=132, description="Horse name")
    horse_id: int = Field(..., description="Horse identifier")
    age: int = Field(..., description="Horse age")
    draw: Optional[int] = Field(None, description="Draw position")
    headgear: Optional[str] = Field(None, max_length=64, description="Headgear worn")
    finishing_position: Optional[str] = Field(None, max_length=6, description="Finishing position")
    total_distance_beaten: Optional[str] = Field(None, max_length=16, description="Total distance beaten")
    betfair_win_sp: Optional[Decimal] = Field(None, description="Betfair win starting price")
    official_rating: Optional[int] = Field(None, description="Official rating (smallint)")
    ts: Optional[int] = Field(None, description="TS rating (smallint)")
    rpr: Optional[int] = Field(None, description="RPR rating (smallint)")
    tfr: Optional[int] = Field(None, description="TFR rating (smallint)")
    tfig: Optional[int] = Field(None, description="TFIG rating (smallint)")
    in_play_high: Optional[Decimal] = Field(None, description="In-play high price")
    in_play_low: Optional[Decimal] = Field(None, description="In-play low price")
    tf_comment: Optional[str] = Field(None, description="Timeform comment (text)")
    tfr_view: Optional[str] = Field(None, max_length=16, description="TFR view")
    rp_comment: Optional[str] = Field(None, description="Racing Post comment (text)")
    unique_id: str = Field(
        ..., max_length=132, description="Unique record identifier"
    )


class RaceResultsResponse(BaseRaceModel):
    """Container for complete race results with analysis capabilities"""
    
    data: List[RaceResult] = Field(default_factory=list, description="List of race results")
    race_id: Optional[int] = Field(None, description="Race ID that was queried")
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __iter__(self):
        return iter(self.data)
    