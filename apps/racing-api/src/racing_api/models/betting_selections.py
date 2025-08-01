from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from .base_entity import BaseEntity


class BettingSelection(BaseEntity):
    horse_id: int
    bet_type: str
    confidence: float


class BettingSelections(BaseEntity):
    race_date: str
    race_id: int
    selections: List[BettingSelection]


class BettingSelectionsAnalysis(BaseEntity):
    betting_type: str
    confidence: float
    horse_name: str
    age: int
    horse_sex: str
    finishing_position: str
    total_distance_beaten: str
    betfair_win_sp: float | None = None
    betfair_place_sp: float | None = None
    official_rating: int | None = None
    ts: int | None = None
    rpr: int | None = None
    tfr: int | None = None
    tfig: int | None = None
    in_play_high: float | None = None
    in_play_low: float | None = None
    in_race_comment: str | None = None
    tf_comment: str | None = None
    tfr_view: str | None = None
    race_id: int
    horse_id: int
    jockey_id: int | None = None
    trainer_id: int | None = None
    owner_id: int | None = None
    sire_id: int | None = None
    dam_id: int | None = None
    unique_id: str | None = None
    race_time: datetime | None = None
    race_date: date | None = None
    race_title: str | None = None
    race_type: str | None = None
    race_class: int | None = None
    distance: str | None = None
    distance_yards: float | None = None
    conditions: str | None = None
    going: str | None = None
    number_of_runners: int | None = None
    hcap_range: str | None = None
    age_range: str | None = None
    surface: str | None = None
    country: str | None = None
    main_race_comment: str | None = None
    meeting_id: str
    course_id: int | None = None
    course: str | None = None
    dam: str | None = None
    sire: str | None = None
    trainer: str | None = None
    jockey: str | None = None
    price_move: float | None = None
    final_odds: float | None = None
    adjusted_final_odds: float | None = None
    bet_result: float | None = None
    running_total: float | None = None
    bet_number: int | None = None


class BettingSelectionsAnalysisResponse(BaseEntity):
    number_of_bets: int
    bet_number: list[int]
    running_total: list[float]
    overall_total: float
    roi_percentage: float
    result_dict: List[BettingSelectionsAnalysis]


class MarketPrices(BaseEntity):
    """Model for storing price information for a horse."""

    horse_name: str
    selection_id: Union[int, str]
    back_price: Optional[float]
    lay_price: Optional[float]


class MarketState(BaseEntity):
    """Model for storing the state of both WIN and PLACE markets."""

    race_id: Union[int, str]
    race_date: str
    race_time: datetime
    market_id_win: str
    market_id_place: str
    win: List[MarketPrices]
    place: List[MarketPrices]


class HorseSelection(BaseEntity):
    """Model for an individual horse selection."""

    id: str = Field(
        ..., description="Unique identifier for this specific selection record"
    )
    timestamp: datetime
    race_id: Union[int, str]
    race_date: str
    race_time: Optional[str]
    horse_id: int
    horse_name: str
    selection_type: str = Field(..., description="Either 'back' or 'lay'")
    original_price: float
    adjusted_price: float
    market_type: str = Field(..., description="Either 'WIN' or 'PLACE'")
    market_id: str = Field(..., description="Betfair market ID")
    selection_id: Union[int, str] = Field(..., description="Betfair selection ID")
    combinedOdds: Optional[str] = Field(
        default=None, description="The combined odds if part of a Dutch bet"
    )


class BetfairSelectionSubmission(BaseEntity):
    """Model for the selection submission payload."""

    selections: List[HorseSelection]
    market_state: MarketState


class SelectionResponse(BaseEntity):
    """Response model for the submission endpoint."""

    success: bool
    message: str
    submission_id: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None


class VoidBetRequest(BaseEntity):
    """Model for voiding/cashing out a specific bet selection."""

    market_id: str
    selection_id: Union[int, str]
    horse_name: str
    market_type: str
    selection_type: str
    race_time: str
    bet_id: str
    requested_odds: float
    size_matched: float
    price_matched: Optional[float] = None
