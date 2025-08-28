import hashlib
from typing import List, Literal
from dataclasses import dataclass
import pandas as pd
from models.feedback_date import FeedbackDate
from api_helpers.helpers.processing_utils import ptr
from storage.horse_race_info import get_horse_race_info
from storage.race_details import get_race_details
from storage.race_form_graph import get_race_form_graph
from storage.race_form import get_historical_race_form
from storage.race_times import get_todays_race_times, get_feedback_race_times
from storage.feedback_date import update_feedback_date, get_feedback_date
from storage.race_result import get_race_result_info, get_race_result_horse_performance

from models.race_times import RaceTimeEntry, RaceTimesResponse
from models.race_result import RaceResult, RaceResultInfo, HorsePerformance


def horse_race_info(race_id: int) -> pd.DataFrame:
    data = get_horse_race_info(race_id)
    return data.filter(
        items=[
            "race_id",
            "horse_name",
            "horse_id",
            "unique_id",
            "age",
            "official_rating",
            "weight_carried_lbs",
            "betfair_win_sp",
            "betfair_place_sp",
            "win_percentage",
            "place_percentage",
            "number_of_runs",
            "race_date",
        ]
    ).astype(
        {
            "race_id": "Int64",
            "horse_name": "string",
            "horse_id": "Int64",
            "unique_id": "string",
            "age": "Int64",
            "official_rating": "Int64",
            "weight_carried_lbs": "Int64",
            "betfair_win_sp": "float",
            "betfair_place_sp": "float",
            "win_percentage": "Int64",
            "place_percentage": "Int64",
            "number_of_runs": "Int64",
            "race_date": "datetime64[ns]",
        }
    )


def race_details(race_id: int) -> pd.DataFrame:
    data = get_race_details(race_id)
    return data.filter(
        items=[
            "race_id",
            "race_title",
            "race_type",
            "course",
            "distance",
            "going",
            "surface",
            "conditions",
            "race_class",
            "hcap_range",
            "age_range",
            "first_place_prize_money",
            "race_time",
            "race_date",
            "is_hcap",
        ]
    ).astype(
        {
            "race_id": "Int64",
            "race_title": "string",
            "race_type": "string",
            "course": "string",
            "distance": "string",
            "going": "string",
            "surface": "string",
            "conditions": "string",
            "race_class": "Int64",
            "hcap_range": "Int64",
            "age_range": "string",
            "first_place_prize_money": "Int64",
            "race_time": "datetime64[ns]",
            "race_date": "datetime64[ns]",
            "is_hcap": "bool",
        }
    )


def race_form_graph(race_id: int) -> pd.DataFrame:
    data = get_race_form_graph(race_id)
    todays_race_date = data["todays_race_date"].iloc[0]
    data = data.sort_values(by=["horse_name", "race_date"])
    projected_data_dicts = []
    for horse in data["horse_name"].unique():
        horse_data = data[data["horse_name"] == horse][
            ["horse_name", "horse_id", "rating", "speed_figure"]
        ]
        if horse_data.empty:
            projected_data = {
                "unique_id": hashlib.md5(
                    f"{horse}_{todays_race_date}_projected".encode()
                ).hexdigest(),
                "race_date": todays_race_date,
                "horse_name": horse,
                "horse_id": horse_data["horse_id"].iloc[0],
                "rating": None,
                "speed_figure": None,
            }
            projected_data_dicts.append(projected_data)
        else:
            projected_data = {
                "unique_id": hashlib.md5(
                    f"{horse}_{todays_race_date}_projected".encode()
                ).hexdigest(),
                "race_date": todays_race_date,
                "horse_name": horse,
                "horse_id": horse_data["horse_id"].iloc[0],
                "rating": horse_data["rating"].mean().round(0).astype(int),
                "speed_figure": horse_data["speed_figure"].mean().round(0).astype(int),
            }
            projected_data_dicts.append(projected_data)
    projected_data = pd.DataFrame(projected_data_dicts)
    data = (
        pd.concat([data, projected_data], ignore_index=True)
        .drop(columns=["todays_race_date"])
        .sort_values(by=["horse_id", "race_date"])
    )

    return data.filter(
        items=[
            "horse_name",
            "horse_id",
            "unique_id",
            "race_id",
            "race_date",
            "race_class",
            "race_type",
            "distance",
            "going",
            "surface",
            "course",
            "official_rating",
            "rating",
            "speed_figure",
        ]
    ).astype(
        {
            "horse_id": "Int64",
            "unique_id": "string",
            "race_id": "Int64",
            "race_date": "datetime64[ns]",
            "race_class": "Int64",
            "race_type": "string",
            "distance": "string",
            "going": "string",
            "surface": "string",
            "course": "string",
            "official_rating": "Int64",
            "rating": "Int64",
            "speed_figure": "Int64",
        }
    )


def historical_race_form(race_id: int) -> pd.DataFrame:
    data = get_historical_race_form(race_id)
    return data.filter(
        items=[
            "horse_name",
            "age",
            "finishing_position",
            "number_of_runners",
            "total_distance_beaten",
            "distance_beaten_signed",
            "distance_beaten_numeric",
            "distance_beaten_indicator",
            "betfair_win_sp",
            "betfair_place_sp",
            "official_rating",
            "race_id",
            "horse_id",
            "race_date",
            "race_class",
            "race_type",
            "distance",
            "going",
            "surface",
            "course",
            "total_prize_money",
            "price_change",
            "rating",
            "speed_figure",
            "age_range",
            "hcap_range",
            "main_race_comment",
            "rp_comment",
            "tf_comment",
            "unique_id",
            "weeks_since_last_ran",
            "since_ran_indicator",
            "total_weeks_since_run",
            "distance_diff",
            "class_diff",
            "rating_range_diff",
        ]
    ).astype(
        {
            "age": "Int64",
            "finishing_position": "str",
            "number_of_runners": "Int64",
            "total_distance_beaten": "str",
            "distance_beaten_signed": "float",
            "distance_beaten_numeric": "float",
            "betfair_win_sp": "float",
            "betfair_place_sp": "float",
            "official_rating": "Int64",
            "race_id": "Int64",
            "horse_id": "Int64",
            "race_date": "datetime64[ns]",
            "race_class": "category",
            "race_type": "category",
            "distance": "str",
            "going": "category",
            "surface": "category",
            "course": "category",
            "total_prize_money": "float",
            "price_change": "float",
            "rating": "float",
            "speed_figure": "float",
            "age_range": "category",
            "hcap_range": "category",
            "main_race_comment": "string",
            "rp_comment": "string",
            "tf_comment": "string",
            "unique_id": "string",
            "weeks_since_last_ran": "Int64",
            "since_ran_indicator": "category",
            "total_weeks_since_run": "Int64",
            "distance_diff": "category",
            "class_diff": "category",
            "rating_range_diff": "category",
        }
    )


def todays_race_times(data_type: Literal["today", "feedback"]) -> RaceTimesResponse:
    """Get today's race times"""
    if data_type == "today":
        data = get_todays_race_times()
    else:
        data = get_feedback_race_times()

    data = (
        data.pipe(add_all_skip_flags)
        .assign(
            race_class=data["race_class"].astype("Int64"),
            hcap_range=data["hcap_range"].astype("Int64"),
        )
        .drop_duplicates(subset=["race_id"])
    )

    races = []
    for course in data["course"].unique():
        course_races = data[data["course"] == course]
        races.append(
            {
                "course": course,
                "races": [
                    RaceTimeEntry(**row.to_dict()) for _, row in course_races.iterrows()
                ],
            }
        )
    return RaceTimesResponse(data=races)


def current_feedback_date_today() -> FeedbackDate:
    """Get current feedback date"""
    data = get_feedback_date()
    if data.empty:
        raise ValueError("No feedback date found")
    return FeedbackDate(**data.iloc[0].to_dict())


def store_current_date_today(date: str):
    """Store current date"""
    try:
        parsed_date = pd.to_datetime(date).strftime("%Y-%m-%d")
    except Exception as e:
        raise ValueError(f"Invalid date format: {e}")
    update_feedback_date(parsed_date)


def race_result_info(race_id: int) -> RaceResultInfo:
    """Get race results by race ID"""
    data = get_race_result_info(race_id)
    return RaceResult(**data.to_dict("records")[0])


def race_result_horse_performance(race_id: int) -> List[HorsePerformance]:
    data = get_race_result_horse_performance(race_id)
    return [HorsePerformance(**row.to_dict()) for _, row in data.iterrows()]


@dataclass
class RaceForm:
    race_details: pd.DataFrame
    horse_race_info: pd.DataFrame
    race_form: pd.DataFrame
    race_form_graph: pd.DataFrame


def race_form(race_id: int) -> RaceForm:

    rd, ri, rf, rg = ptr(
        lambda: race_details(race_id),
        lambda: horse_race_info(race_id),
        lambda: historical_race_form(race_id),
        lambda: race_form_graph(race_id),
    )

    return RaceForm(
        race_details=rd, horse_race_info=ri, race_form=rf, race_form_graph=rg
    )


def race_result(race_id: int) -> RaceResult:

    ri, rp = ptr(
        lambda: race_result_info(race_id),
        lambda: race_result_horse_performance(race_id),
    )

    return RaceResult(result_info=ri, horse_performance_data=rp)


# -----------------------------------------------------------------------------------


def add_all_skip_flags(data: pd.DataFrame) -> pd.DataFrame:
    """Add all skip flag conditions as separate columns, then combine into final skip_flag"""
    races_to_ignore = [
        "shergar",
        "maiden",
        "novice",
        "hurdle",
        "chase",
        "hunter",
        "heritage",
        "bumper",
        "racing league",
        "lady riders",
    ]

    # Flag 1: Race title contains ignored words
    data["skip_race_type"] = (
        data["race_title"].str.lower().str.contains("|".join(races_to_ignore), na=False)
    )

    # Flag 2: Minimum SP per race > 4
    min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
    data["skip_min_sp"] = data["race_id"].map(min_sp_per_race > 4)

    # Flag 3: >10 runners AND favorite > 4
    min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
    max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
    condition = (max_runners_per_race > 10) & (min_sp_per_race > 4)
    data["skip_runners_fav"] = data["race_id"].map(condition)

    # Flag 4: Races with ≤4 runners
    max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
    data["skip_few_runners"] = data["race_id"].map(max_runners_per_race <= 4)

    # Flag 5: Minimum SP per race ≤ 2.5
    min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
    data["skip_short_price"] = data["race_id"].map(min_sp_per_race <= 2.28)

    # Flag 6: Races where all horses are 2 years old
    max_age_per_race = data.groupby("race_id")["age"].max()
    data["skip_all_two_year_olds"] = data["race_id"].map(max_age_per_race == 2)

    # Flag 7: Races where all horses are 3 years old AND more than 8 runners
    max_age_per_race = data.groupby("race_id")["age"].max()
    max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
    condition = (max_age_per_race == 3) & (max_runners_per_race > 8)
    data["skip_all_three_year_olds_big_field"] = data["race_id"].map(condition)

    # Final skip flag: True if ANY of the conditions are True
    data["skip_flag"] = (
        data["skip_race_type"]
        | data["skip_min_sp"]
        | data["skip_runners_fav"]
        | data["skip_few_runners"]
        | data["skip_short_price"]
        | data["skip_all_two_year_olds"]
        | data["skip_all_three_year_olds_big_field"]
    )

    return data.drop(
        columns=[
            "skip_race_type",
            "skip_min_sp",
            "skip_runners_fav",
            "skip_few_runners",
            "skip_short_price",
            "skip_all_two_year_olds",
            "skip_all_three_year_olds_big_field",
        ]
    )
