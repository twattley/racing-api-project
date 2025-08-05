from datetime import date, datetime
from typing import List

from .base_entity import BaseEntity


class TodaysHorseFormData(BaseEntity):
    age: int
    horse_sex: str | None = None
    days_since_last_ran: int | None = None
    days_since_performance: int | None = None
    weeks_since_last_ran: int | None = None
    weeks_since_performance: int | None = None
    draw: int | None = None
    headgear: str | None = None
    weight_carried: str
    weight_carried_lbs: int
    extra_weight: int | None = None
    jockey_claim: int | None = None
    finishing_position: str | None = None
    total_distance_beaten: str | None = None
    industry_sp: str | None = None
    betfair_win_sp: float | None = None
    betfair_place_sp: float | None = None
    official_rating: int | None = None
    ts: int | None = None
    rpr: int | None = None
    tfr: int | None = None
    tfig: int | None = None
    rating: int | None = None
    speed_figure: int | None = None
    rating_diff: float | None = None
    speed_rating_diff: float | None = None
    rating_from_or: int | None = None
    speed_rating_from_or: int | None = None
    in_play_high: float | None = None
    in_play_low: float | None = None
    in_race_comment: str | None = None
    tf_comment: str | None = None
    rp_comment: str | None = None
    tfr_view: str | None = None
    race_id: int
    jockey_id: int | None = None
    trainer_id: int | None = None
    owner_id: int | None = None
    sire_id: int | None = None
    dam_id: int | None = None
    unique_id: str
    race_time: datetime
    race_date: date
    race_title: str
    race_type: str | None = None
    race_class: int | None = None
    distance: str
    # distance_yards: float
    # distance_meters: float
    # distance_kilometers: float
    conditions: str | None = None
    going: str | None = None
    number_of_runners: int | None = None
    hcap_range: int | None = None
    age_range: str | None = None
    surface: str | None = None
    total_prize_money: int | None = None
    first_place_prize_money: int | None = None
    winning_time: str | None = None
    time_seconds: float | None = None
    relative_time: float | None = None
    relative_to_standard: str | None = None
    country: str | None = None
    main_race_comment: str | None = None
    meeting_id: str
    course_id: int
    course: str
    dam: str | None = None
    sire: str | None = None
    trainer: str | None = None
    jockey: str | None = None
    data_type: str
    distance_diff: float | None = None
    class_diff: str | None = None
    rating_range_diff: str | None = None
    price_change: int | None = None


class TodaysPerformanceDataResponse(BaseEntity):
    horse_name: str
    horse_id: int
    todays_horse_number: int
    todays_horse_age: int
    todays_first_places: int | None = None
    todays_second_places: int | None = None
    todays_third_places: int | None = None
    todays_fourth_places: int | None = None
    number_of_runs: int | None = None
    todays_betfair_win_sp: float | None = None
    todays_betfair_place_sp: float | None = None
    todays_official_rating: int | None = 0
    todays_days_since_last_ran: int | None = None
    todays_rating: int | None = None
    todays_win_percentage: int | None = None
    todays_place_percentage: int | None = None
    todays_volatility_index: int | None = None
    todays_weight_carried: int | None = None
    todays_headgear: str | None = None
    todays_price_change: int | None = None
    todays_draw: str | None = None
    todays_betfair_selection_id: int | None = None
    todays_market_id_win: str | None = None
    todays_market_id_place: str | None = None
    todays_total_matched_win: float | None = None
    todays_back_price_1_win: float | None = None
    todays_back_price_1_depth_win: float | None = None
    todays_back_price_2_win: float | None = None
    todays_back_price_2_depth_win: float | None = None
    todays_back_price_3_win: float | None = None
    todays_back_price_3_depth_win: float | None = None
    todays_back_price_4_win: float | None = None
    todays_back_price_4_depth_win: float | None = None
    todays_back_price_5_win: float | None = None
    todays_back_price_5_depth_win: float | None = None
    todays_lay_price_1_win: float | None = None
    todays_lay_price_1_depth_win: float | None = None
    todays_lay_price_2_win: float | None = None
    todays_lay_price_2_depth_win: float | None = None
    todays_lay_price_3_win: float | None = None
    todays_lay_price_3_depth_win: float | None = None
    todays_lay_price_4_win: float | None = None
    todays_lay_price_4_depth_win: float | None = None
    todays_lay_price_5_win: float | None = None
    todays_lay_price_5_depth_win: float | None = None
    todays_total_matched_event_win: int | None = None
    todays_percent_back_win_book_win: int | None = None
    todays_percent_lay_win_book_win: int | None = None
    todays_total_matched_place: float | None = None
    todays_back_price_1_place: float | None = None
    todays_back_price_1_depth_place: float | None = None
    todays_back_price_2_place: float | None = None
    todays_back_price_2_depth_place: float | None = None
    todays_back_price_3_place: float | None = None
    todays_back_price_3_depth_place: float | None = None
    todays_back_price_4_place: float | None = None
    todays_back_price_4_depth_place: float | None = None
    todays_back_price_5_place: float | None = None
    todays_back_price_5_depth_place: float | None = None
    todays_lay_price_1_place: float | None = None
    todays_lay_price_1_depth_place: float | None = None
    todays_lay_price_2_place: float | None = None
    todays_lay_price_2_depth_place: float | None = None
    todays_lay_price_3_place: float | None = None
    todays_lay_price_3_depth_place: float | None = None
    todays_lay_price_4_place: float | None = None
    todays_lay_price_4_depth_place: float | None = None
    todays_lay_price_5_place: float | None = None
    todays_lay_price_5_depth_place: float | None = None
    todays_total_matched_event_place: int | None = None
    todays_percent_back_win_book_place: int | None = None
    todays_percent_lay_win_book_place: int | None = None
    performance_data: List[TodaysHorseFormData]


class TodaysRaceFormDetails(BaseEntity):
    race_id: int
    course: str
    distance: str
    going: str | None = None
    surface: str | None = None
    race_class: int | None = None
    hcap_range: int | None = None
    age_range: str | None = None
    conditions: str | None = None
    first_place_prize_money: int | None = None
    race_type: str | None = None
    race_title: str
    race_time: datetime
    race_date: date
    is_hcap: bool | None = None
