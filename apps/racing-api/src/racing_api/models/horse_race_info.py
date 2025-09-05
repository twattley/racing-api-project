from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import Field

from .base_model import BaseRaceModel


class RaceDataRow(BaseRaceModel):
    """Model for a single row returned by the race data query"""

    race_id: Optional[int] = Field(None, description="Race identifier")
    horse_name: Optional[str] = Field(None, max_length=132, description="Horse name")
    horse_id: Optional[int] = Field(None, description="Horse identifier")
    unique_id: Optional[str] = Field(
        None, max_length=132, description="Unique record identifier"
    )
    draw_runners: Optional[str] = Field(
        None, max_length=16, description="Draw / Number of Runners"
    )
    headgear: Optional[str] = Field(None, max_length=32, description="Headgear worn")
    age: Optional[int] = Field(None, description="Horse age in years")
    official_rating: Optional[int] = Field(
        None, description="Official rating (smallint in DB)"
    )
    weight_carried_lbs: Optional[int] = Field(
        None, description="Weight carried in pounds (smallint in DB)"
    )
    betfair_win_sp: Optional[Decimal] = Field(
        None, description="Betfair win starting price"
    )
    betfair_place_sp: Optional[Decimal] = Field(
        None, description="Betfair place starting price"
    )
    selection_id: Optional[int] = Field(None, description="Selection identifier")
    market_id_win: Optional[str] = Field(None, description="Market identifier for win")
    market_id_place: Optional[str] = Field(
        None, description="Market identifier for place"
    )
    price_change: Optional[Decimal] = Field(None, description="Price change")
    win_percentage: Optional[int] = Field(
        None, description="Win percentage (default 0)"
    )
    place_percentage: Optional[int] = Field(
        None, description="Place percentage (default 0)"
    )
    number_of_runs: Optional[int] = Field(None, description="Total number of runs")
    race_date: Optional[date] = Field(None, description="Today's race date")


class RaceDataResponse(BaseRaceModel):
    """Container for multiple race data rows"""

    data: list[RaceDataRow] = Field(
        default_factory=list, description="List of race data rows"
    )
    race_id: Optional[int] = Field(None, description="Race ID that was queried")

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)


# fmt on
