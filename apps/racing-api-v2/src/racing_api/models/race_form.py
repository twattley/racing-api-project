from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import date
from decimal import Decimal


class RaceForm(BaseModel):
    """Model for a single historical run with comparison data"""

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, validate_assignment=True
    )

    horse_name: Optional[str] = Field(None, max_length=132, description="Horse name")
    horse_id: Optional[int] = Field(None, description="Horse identifier")
    age: Optional[int] = Field(None, description="Horse age at time of race")
    unique_id: Optional[str] = Field(
        None, max_length=132, description="Unique record identifier"
    )
    race_id: Optional[int] = Field(None, description="Historical race identifier")
    race_date: Optional[date] = Field(None, description="Date of this historical race")
    race_class: Optional[int] = Field(None, description="Race class (smallint in DB)")
    race_type: Optional[str] = Field(None, max_length=32, description="Race type")
    distance: Optional[str] = Field(None, max_length=16, description="Race distance")
    going: Optional[str] = Field(None, max_length=32, description="Going conditions")
    surface: Optional[str] = Field(None, max_length=32, description="Surface type")
    course: Optional[str] = Field(None, max_length=132, description="Course name")
    age_range: Optional[str] = Field(
        None, max_length=32, description="Age range for this race"
    )
    hcap_range: Optional[int] = Field(None, description="Handicap range (smallint)")
    total_prize_money: Optional[int] = Field(
        None, description="Total prize money for this race"
    )
    finishing_position: Optional[str] = Field(
        None, max_length=6, description="Finishing position"
    )
    total_distance_beaten: Optional[str] = Field(
        None, max_length=16, description="Distance beaten"
    )
    official_rating: Optional[int] = Field(
        None, description="Official rating (smallint)"
    )
    rating: Optional[int] = Field(None, description="Rating (integer)")
    speed_figure: Optional[int] = Field(None, description="Speed figure")
    betfair_win_sp: Optional[Decimal] = Field(
        None, description="Betfair win starting price"
    )
    betfair_place_sp: Optional[Decimal] = Field(
        None, description="Betfair place starting price"
    )
    price_change: Optional[Decimal] = Field(None, description="Price change")
    main_race_comment: Optional[str] = Field(
        None, description="Main race comment (text)"
    )
    rp_comment: Optional[str] = Field(None, description="Racing Post comment (text)")
    tf_comment: Optional[str] = Field(None, description="Timeform comment (text)")
    total_weeks_since_run: Optional[int] = Field(
        None, description="Total weeks between this run and today's race"
    )
    distance_diff: Literal["lower", "same", "higher"] = Field(
        "same", description="Distance comparison to today's race"
    )
    class_diff: Literal["lower", "same", "higher"] = Field(
        "same", description="Class comparison to today's race"
    )
    rating_range_diff: Literal["lower", "same", "higher"] = Field(
        "same", description="Rating range comparison to today's race"
    )


class RaceFormResponse(BaseModel):
    """Container for historical horse data with advanced analysis"""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    data: List[RaceForm] = Field(
        default_factory=list, description="List of historical runs"
    )
    race_id: Optional[int] = Field(None, description="Today's race ID that was queried")

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)
