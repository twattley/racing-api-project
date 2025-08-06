from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import date


class RaceDataRow(BaseModel):
    """Model for a single row returned by the race data query"""

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=True, validate_assignment=True
    )

    race_id: Optional[int] = Field(None, description="Race identifier")
    horse_name: Optional[str] = Field(None, max_length=132, description="Horse name")
    horse_id: Optional[int] = Field(None, description="Horse identifier")
    unique_id: Optional[str] = Field(
        None, max_length=132, description="Unique record identifier"
    )
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
    price_change: Optional[Decimal] = Field(None, description="Price change")
    win_percentage: Optional[int] = Field(
        None, description="Win percentage (default 0)"
    )
    place_percentage: Optional[int] = Field(
        None, description="Place percentage (default 0)"
    )
    number_of_runs: Optional[int] = Field(None, description="Total number of runs")
    race_class: Optional[int] = Field(None, description="Race class (smallint in DB)")
    distance: Optional[str] = Field(
        None, max_length=16, description="Race distance as string"
    )
    total_prize_money: Optional[int] = Field(
        None, description="Total prize money for today's race"
    )
    race_date: Optional[date] = Field(None, description="Today's race date")
    draw_runners: Optional[str] = Field(
        None,
        description="Formatted draw/runners string like '(5/12)' or '5/?' or '?/12'",
    )
    hcap_range: int = Field(
        0, description="Handicap range extracted from conditions (defaults to 0)"
    )


class RaceDataResponse(BaseModel):
    """Container for multiple race data rows"""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    data: list[RaceDataRow] = Field(
        default_factory=list, description="List of race data rows"
    )
    race_id: Optional[int] = Field(None, description="Race ID that was queried")

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)


# fmt on
