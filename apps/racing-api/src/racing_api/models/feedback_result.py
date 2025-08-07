from datetime import date, datetime
from typing import List

from ..models.base_entity import BaseEntity


class TodaysRacesResultDataResponse(BaseEntity):
    horse_name: str
    horse_id: int
    age: int
    draw: int | None = None
    headgear: str | None = None
    weight_carried: str | None = None
    finishing_position: str | None = None
    total_distance_beaten: str | None = None
    betfair_win_sp: float | None = None
    official_rating: int | None = 0
    ts: int | None = None
    rpr: int | None = None
    tfr: int | None = None
    tfig: int | None = None
    in_play_high: float | None = None
    in_play_low: float | None = None
    tf_comment: str | None = None
    tfr_view: str | None = None
    rp_comment: str | None = None


class TodaysRacesResultResponse(BaseEntity):
    race_time: datetime
    race_date: date
    race_title: str
    race_type: str | None = None
    race_class: int | None = None
    distance: str
    conditions: str
    going: str
    number_of_runners: int
    hcap_range: int | None = None
    age_range: str | None = None
    surface: str | None = None
    total_prize_money: int | None = None
    winning_time: str | None = None
    relative_time: float | None = None
    relative_to_standard: str | None = None
    main_race_comment: str | None = None
    course_id: int
    course: str
    race_id: int
    race_results: List[TodaysRacesResultDataResponse]


class SimulatedBetResponse(BaseEntity):
    horse_name: str
    adj_finishing_position: str
    bet_type: str
    bet_market: str
    p_and_l: float


class TodaysRacesResultWithSimulationResponse(BaseEntity):
    # Original race data
    race_time: datetime
    race_date: date
    race_title: str
    race_type: str | None = None
    race_class: int | None = None
    distance: str
    conditions: str
    going: str
    number_of_runners: int
    hcap_range: int | None = None
    age_range: str | None = None
    surface: str | None = None
    total_prize_money: int | None = None
    winning_time: str | None = None
    relative_time: float | None = None
    relative_to_standard: str | None = None
    main_race_comment: str | None = None
    course_id: int
    course: str
    race_id: int
    race_results: List[TodaysRacesResultDataResponse]

    # New simulation data with defaults for empty results
    simulated_bets: List[SimulatedBetResponse] = []
    race_pnl: float | None = None
    has_simulation: bool = False
