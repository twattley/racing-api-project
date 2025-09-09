from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base_model import BaseRaceModel


class RaceFormGraph(BaseRaceModel):
    """Model for a single historical run of a horse"""

    horse_name: Optional[str] = Field(None, max_length=132, description="Horse name")
    horse_id: Optional[int] = Field(None, description="Horse identifier")
    unique_id: Optional[str] = Field(
        None, max_length=132, description="Unique record identifier"
    )
    race_id: Optional[int] = Field(None, description="Historical race identifier")
    race_date: Optional[date] = Field(None, description="Date of this historical race")
    race_class: Optional[int] = Field(None, description="Race class (smallint in DB)")
    race_type: Optional[str] = Field(None, max_length=32, description="Race type")
    betfair_win_sp: Optional[float] = Field(
        None, description="Betfair starting price (numeric in DB)"
    )
    distance: Optional[str] = Field(None, max_length=16, description="Race distance")
    going: Optional[str] = Field(None, max_length=32, description="Going conditions")
    surface: Optional[str] = Field(None, max_length=32, description="Surface type")
    course: Optional[str] = Field(None, max_length=132, description="Course name")
    official_rating: Optional[int] = Field(
        None, description="Official rating at time of race (smallint)"
    )
    rating: Optional[int] = Field(None, description="Rating (integer)")
    speed_figure: Optional[int] = Field(None, description="Speed figure (integer)")


class RaceFormGraphResponse(BaseModel):
    """Container for historical horse data with analysis capabilities"""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    race_id: Optional[int] = Field(None, description="Today's race ID that was queried")
    data: List[RaceFormGraph] = Field(
        default_factory=list, description="List of historical runs"
    )

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)
