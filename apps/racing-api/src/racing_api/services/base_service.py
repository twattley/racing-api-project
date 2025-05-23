from datetime import timedelta
from typing import Callable

import numpy as np
import pandas as pd

from ..models.form_data import InputRaceFilters

FILTER_WEEKS = 52
FILTER_YEARS = 3
FILTER_PERIOD = FILTER_WEEKS * FILTER_YEARS


class BaseService:
    def __init__(self):
        pass

    def data_to_dict(self, data: pd.DataFrame) -> list[dict]:
        return [
            {k: v if pd.notna(v) else None for k, v in d.items()}
            for d in data.to_dict(orient="records")
        ]

    def format_todays_races(self, data: pd.DataFrame) -> list[dict]:
        data = data.assign(
            race_class=data["race_class"].fillna(0).astype(int).replace(0, None)
        )

        grouped = data.groupby("course_id")
        courses = []

        for course_id, group in grouped:
            races = group.to_dict(orient="records")
            course_info = {
                "course": group["course"].iloc[0],
                "course_id": course_id,
                "races": races,
            }
            courses.append(course_info)

        return [
            {
                "race_date": data["race_date"].iloc[0],
                "courses": courses,
            }
        ]

    def _filter_by_recent_races(self, data: pd.DataFrame, date: str) -> pd.DataFrame:
        date_filter = date - timedelta(weeks=FILTER_PERIOD)
        return data[data["race_date"] > date_filter]

    def _filter_by_active_status(self, data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(status=data["status"].fillna("ACTIVE"))
        todays_active_runners = data[
            (data["data_type"] == "today") & (data["status"] == "ACTIVE")
        ]["horse_id"].unique()
        return data[data["horse_id"].isin(todays_active_runners)]

    def format_todays_form_data(
        self,
        data: pd.DataFrame,
        filters: InputRaceFilters,
        transformation_function: Callable,
    ) -> list[dict]:
        date = data[data["data_type"] == "today"]["race_date"].iloc[0]
        data = (
            data.pipe(self._filter_by_active_status)
            .pipe(transformation_function, date)
            .pipe(self._filter_by_recent_races, date)
        )
        today = data[data["data_type"] == "today"].sort_values(
            by=["race_id", "betfair_win_sp"], ascending=[True, True]
        )
        todays_distance = today["distance"].iloc[0]
        todays_surface = today["surface"].iloc[0]
        todays_course = today["course"].iloc[0]

        historical = data[data["data_type"] == "historical"]

        distance_list = filters.get_distance_list()
        surface_list = filters.get_surface_list()
        course_list = filters.get_course_list()
        race_class_list = filters.get_race_class_list()
        distance_beaten_list = filters.get_distance_beaten_list()

        historical_distances = (
            historical.sort_values(by="distance_meters")["distance"].unique().tolist()
        )
        historical_distances = [d for d in historical_distances if d != todays_distance]
        historical_courses = (
            historical.sort_values(by="course")["course"].unique().tolist()
        )
        historical_courses = [c for c in historical_courses if c != todays_course]

        filters = {
            "distance": [todays_distance] + historical_distances,
            "surface": [todays_surface]
            + [
                s
                for s in ["polytrack", "tapeta", "turf", "fibresand"]
                if s != todays_surface
            ],
            "course": [todays_course] + historical_courses,
            "race_class": [1, 2, 3, 4, 5, 6, 7, None],
            "distance_beaten": [1, 3, 5],
        }
        today["horse_number"] = today.groupby("race_id").cumcount() + 1
        today["draw"] = today["draw"].fillna(0).astype(int)

        race_details = today.drop_duplicates(subset=["unique_id"])

        race_details = race_details.assign(
            is_hcap=np.where(race_details["hcap_range"].isna(), False, True)
        ).to_dict(orient="records")[0]

        today = today.assign(
            todays_horse_age=today["age"],
            todays_official_rating=today["official_rating"],
            todays_betfair_win_sp=today["betfair_win_sp"],
            todays_rating=today["rating"],
            todays_weight_carried=today["weight_carried_lbs"],
            todays_headgear=today["headgear"],
            todays_price_change=today["price_change"],
            todays_draw=np.where(
                today["draw"].isna(),
                "",
                "("
                + today["draw"].astype(str)
                + "/"
                + today["number_of_runners"].astype(str)
                + ")",
            ),
            todays_betfair_selection_id=today["todays_betfair_selection_id"],
            todays_market_id_win=today["market_id_win"],
            todays_market_id_place=today["market_id_place"],
            todays_total_matched_win=today["total_matched_win"],
            todays_back_price_1_win=today["back_price_1_win"],
            todays_back_price_1_depth_win=today["back_price_1_depth_win"],
            todays_back_price_2_win=today["back_price_2_win"],
            todays_back_price_2_depth_win=today["back_price_2_depth_win"],
            todays_back_price_3_win=today["back_price_3_win"],
            todays_back_price_3_depth_win=today["back_price_3_depth_win"],
            todays_back_price_4_win=today["back_price_4_win"],
            todays_back_price_4_depth_win=today["back_price_4_depth_win"],
            todays_back_price_5_win=today["back_price_5_win"],
            todays_back_price_5_depth_win=today["back_price_5_depth_win"],
            todays_lay_price_1_win=today["lay_price_1_win"],
            todays_lay_price_1_depth_win=today["lay_price_1_depth_win"],
            todays_lay_price_2_win=today["lay_price_2_win"],
            todays_lay_price_2_depth_win=today["lay_price_2_depth_win"],
            todays_lay_price_3_win=today["lay_price_3_win"],
            todays_lay_price_3_depth_win=today["lay_price_3_depth_win"],
            todays_lay_price_4_win=today["lay_price_4_win"],
            todays_lay_price_4_depth_win=today["lay_price_4_depth_win"],
            todays_lay_price_5_win=today["lay_price_5_win"],
            todays_lay_price_5_depth_win=today["lay_price_5_depth_win"],
            todays_total_matched_event_win=today["total_matched_event_win"],
            todays_percent_back_win_book_win=today["percent_back_win_book_win"],
            todays_percent_lay_win_book_win=today["percent_lay_win_book_win"],
            todays_market_place=today["market_place"],
            todays_total_matched_place=today["total_matched_place"],
            todays_back_price_1_place=today["back_price_1_place"],
            todays_back_price_1_depth_place=today["back_price_1_depth_place"],
            todays_back_price_2_place=today["back_price_2_place"],
            todays_back_price_2_depth_place=today["back_price_2_depth_place"],
            todays_back_price_3_place=today["back_price_3_place"],
            todays_back_price_3_depth_place=today["back_price_3_depth_place"],
            todays_back_price_4_place=today["back_price_4_place"],
            todays_back_price_4_depth_place=today["back_price_4_depth_place"],
            todays_back_price_5_place=today["back_price_5_place"],
            todays_back_price_5_depth_place=today["back_price_5_depth_place"],
            todays_lay_price_1_place=today["lay_price_1_place"],
            todays_lay_price_1_depth_place=today["lay_price_1_depth_place"],
            todays_lay_price_2_place=today["lay_price_2_place"],
            todays_lay_price_2_depth_place=today["lay_price_2_depth_place"],
            todays_lay_price_3_place=today["lay_price_3_place"],
            todays_lay_price_3_depth_place=today["lay_price_3_depth_place"],
            todays_lay_price_4_place=today["lay_price_4_place"],
            todays_lay_price_4_depth_place=today["lay_price_4_depth_place"],
            todays_lay_price_5_place=today["lay_price_5_place"],
            todays_lay_price_5_depth_place=today["lay_price_5_depth_place"],
            todays_total_matched_event_place=today["total_matched_event_place"],
            todays_percent_back_win_book_place=today["percent_back_win_book_place"],
            todays_percent_lay_win_book_place=today["percent_lay_win_book_place"],
        ).rename(
            columns={
                "horse_number": "todays_horse_number",
                "betfair_place_sp": "todays_betfair_place_sp",
                "days_since_last_ran": "todays_days_since_last_ran",
                "first_places": "todays_first_places",
                "second_places": "todays_second_places",
                "third_places": "todays_third_places",
                "fourth_places": "todays_fourth_places",
                "win_percentage": "todays_win_percentage",
                "place_percentage": "todays_place_percentage",
                "volatility_index": "todays_volatility_index",
            }
        )

        today = today.assign(
            todays_price_change=today["todays_price_change"]
            .fillna(0)
            .round(0)
            .astype(int)
        )

        historical = historical.merge(
            today[
                [
                    "horse_id",
                    "todays_horse_number",
                    "todays_betfair_win_sp",
                    "todays_betfair_place_sp",
                    "todays_official_rating",
                    "todays_rating",
                    "todays_horse_age",
                    "todays_days_since_last_ran",
                    "todays_first_places",
                    "todays_second_places",
                    "todays_third_places",
                    "todays_fourth_places",
                    "todays_win_percentage",
                    "todays_place_percentage",
                    "todays_volatility_index",
                    "todays_weight_carried",
                    "todays_headgear",
                    "todays_price_change",
                    "todays_market_id_win",
                    "todays_market_id_place",
                    "todays_betfair_selection_id",
                    "todays_total_matched_win",
                    "todays_back_price_1_win",
                    "todays_back_price_1_depth_win",
                    "todays_back_price_2_win",
                    "todays_back_price_2_depth_win",
                    "todays_back_price_3_win",
                    "todays_back_price_3_depth_win",
                    "todays_back_price_4_win",
                    "todays_back_price_4_depth_win",
                    "todays_back_price_5_win",
                    "todays_back_price_5_depth_win",
                    "todays_lay_price_1_win",
                    "todays_lay_price_1_depth_win",
                    "todays_lay_price_2_win",
                    "todays_lay_price_2_depth_win",
                    "todays_lay_price_3_win",
                    "todays_lay_price_3_depth_win",
                    "todays_lay_price_4_win",
                    "todays_lay_price_4_depth_win",
                    "todays_lay_price_5_win",
                    "todays_lay_price_5_depth_win",
                    "todays_total_matched_event_win",
                    "todays_percent_back_win_book_win",
                    "todays_percent_lay_win_book_win",
                    "todays_market_place",
                    "todays_total_matched_place",
                    "todays_back_price_1_place",
                    "todays_back_price_1_depth_place",
                    "todays_back_price_2_place",
                    "todays_back_price_2_depth_place",
                    "todays_back_price_3_place",
                    "todays_back_price_3_depth_place",
                    "todays_back_price_4_place",
                    "todays_back_price_4_depth_place",
                    "todays_back_price_5_place",
                    "todays_back_price_5_depth_place",
                    "todays_lay_price_1_place",
                    "todays_lay_price_1_depth_place",
                    "todays_lay_price_2_place",
                    "todays_lay_price_2_depth_place",
                    "todays_lay_price_3_place",
                    "todays_lay_price_3_depth_place",
                    "todays_lay_price_4_place",
                    "todays_lay_price_4_depth_place",
                    "todays_lay_price_5_place",
                    "todays_lay_price_5_depth_place",
                    "todays_total_matched_event_place",
                    "todays_percent_back_win_book_place",
                    "todays_percent_lay_win_book_place",
                ]
            ],
            on="horse_id",
        )

        if distance_list:
            historical = historical[historical["distance"].isin(distance_list)]
        if surface_list:
            historical = historical[historical["surface"].isin(surface_list)]
        if course_list:
            historical = historical[historical["course"].isin(course_list)]
        if race_class_list:
            historical = historical[historical["race_class"].isin(race_class_list)]
        if distance_beaten_list:
            historical = historical[
                historical["distance_beaten"].isin(distance_beaten_list)
            ]

        combined_data = pd.concat([historical, today]).sort_values(
            by=["todays_betfair_win_sp", "horse_id", "race_date"],
            ascending=[True, True, False],
        )
        combined_data = combined_data.assign(
            price_change=historical["price_change"].fillna(0).round(0).astype(int)
        )
        combined_data = combined_data.round(2)
        grouped = combined_data.groupby(["horse_id", "horse_name"], sort=False)

        data = {
            "filters": filters,
            "race_id": race_details["race_id"],
            "course": race_details["course"],
            "distance": race_details["distance"],
            "going": race_details["going"],
            "surface": race_details["surface"],
            "race_class": race_details["race_class"],
            "hcap_range": race_details["hcap_range"],
            "is_hcap": race_details["is_hcap"],
            "age_range": race_details["age_range"],
            "conditions": race_details["conditions"],
            "first_place_prize_money": race_details["first_place_prize_money"],
            "race_type": race_details["race_type"],
            "race_title": race_details["race_title"],
            "race_time": race_details["race_time"],
            "race_date": race_details["race_date"],
            "market_id_win": race_details["market_id_win"],
            "market_id_place": race_details["market_id_place"],
            "horse_data": [
                {
                    "horse_name": name,
                    "horse_id": horse_id,
                    "todays_betfair_selection_id": group[
                        "todays_betfair_selection_id"
                    ].iloc[0],
                    "todays_horse_number": group["todays_horse_number"].iloc[0],
                    "todays_horse_age": group["todays_horse_age"].iloc[0],
                    "todays_first_places": group["todays_first_places"].iloc[0],
                    "todays_second_places": group["todays_second_places"].iloc[0],
                    "todays_third_places": group["todays_third_places"].iloc[0],
                    "todays_fourth_places": group["todays_fourth_places"].iloc[0],
                    "todays_win_percentage": group["todays_win_percentage"].iloc[0],
                    "todays_place_percentage": group["todays_place_percentage"].iloc[0],
                    "number_of_runs": group["number_of_runs"].iloc[0],
                    "todays_betfair_win_sp": group["todays_betfair_win_sp"].iloc[0],
                    "todays_betfair_place_sp": group["todays_betfair_place_sp"].iloc[0],
                    "todays_official_rating": group["todays_official_rating"].iloc[0],
                    "todays_rating": group["todays_rating"].iloc[0],
                    "todays_weight_carried": group["todays_weight_carried"].iloc[0],
                    "todays_headgear": group["todays_headgear"].iloc[0],
                    "todays_price_change": group["todays_price_change"].iloc[0],
                    "todays_draw": group["todays_draw"].iloc[0],
                    "todays_days_since_last_ran": (
                        None
                        if pd.isna(group["todays_days_since_last_ran"].iloc[0])
                        else int(group["todays_days_since_last_ran"].iloc[0])
                    ),
                    "todays_volatility_index": group["todays_volatility_index"].iloc[0],
                    "todays_market_id_win": group["todays_market_id_win"].iloc[0],
                    "todays_market_id_place": group["todays_market_id_place"].iloc[0],
                    "todays_total_matched_win": group["todays_total_matched_win"].iloc[
                        0
                    ],
                    "todays_back_price_1_win": group["todays_back_price_1_win"].iloc[0],
                    "todays_back_price_1_depth_win": group[
                        "todays_back_price_1_depth_win"
                    ].iloc[0],
                    "todays_back_price_2_win": group["todays_back_price_2_win"].iloc[0],
                    "todays_back_price_2_depth_win": group[
                        "todays_back_price_2_depth_win"
                    ].iloc[0],
                    "todays_back_price_3_win": group["todays_back_price_3_win"].iloc[0],
                    "todays_back_price_3_depth_win": group[
                        "todays_back_price_3_depth_win"
                    ].iloc[0],
                    "todays_back_price_4_win": group["todays_back_price_4_win"].iloc[0],
                    "todays_back_price_4_depth_win": group[
                        "todays_back_price_4_depth_win"
                    ].iloc[0],
                    "todays_back_price_5_win": group["todays_back_price_5_win"].iloc[0],
                    "todays_back_price_5_depth_win": group[
                        "todays_back_price_5_depth_win"
                    ].iloc[0],
                    "todays_lay_price_1_win": group["todays_lay_price_1_win"].iloc[0],
                    "todays_lay_price_1_depth_win": group[
                        "todays_lay_price_1_depth_win"
                    ].iloc[0],
                    "todays_lay_price_2_win": group["todays_lay_price_2_win"].iloc[0],
                    "todays_lay_price_2_depth_win": group[
                        "todays_lay_price_2_depth_win"
                    ].iloc[0],
                    "todays_lay_price_3_win": group["todays_lay_price_3_win"].iloc[0],
                    "todays_lay_price_3_depth_win": group[
                        "todays_lay_price_3_depth_win"
                    ].iloc[0],
                    "todays_lay_price_4_win": group["todays_lay_price_4_win"].iloc[0],
                    "todays_lay_price_4_depth_win": group[
                        "todays_lay_price_4_depth_win"
                    ].iloc[0],
                    "todays_lay_price_5_win": group["todays_lay_price_5_win"].iloc[0],
                    "todays_lay_price_5_depth_win": group[
                        "todays_lay_price_5_depth_win"
                    ].iloc[0],
                    "todays_total_matched_event_win": group[
                        "todays_total_matched_event_win"
                    ].iloc[0],
                    "todays_percent_back_win_book_win": group[
                        "todays_percent_back_win_book_win"
                    ].iloc[0],
                    "todays_percent_lay_win_book_win": group[
                        "todays_percent_lay_win_book_win"
                    ].iloc[0],
                    "todays_total_matched_place": group[
                        "todays_total_matched_place"
                    ].iloc[0],
                    "todays_back_price_1_place": group[
                        "todays_back_price_1_place"
                    ].iloc[0],
                    "todays_back_price_1_depth_place": group[
                        "todays_back_price_1_depth_place"
                    ].iloc[0],
                    "todays_back_price_2_place": group[
                        "todays_back_price_2_place"
                    ].iloc[0],
                    "todays_back_price_2_depth_place": group[
                        "todays_back_price_2_depth_place"
                    ].iloc[0],
                    "todays_back_price_3_place": group[
                        "todays_back_price_3_place"
                    ].iloc[0],
                    "todays_back_price_3_depth_place": group[
                        "todays_back_price_3_depth_place"
                    ].iloc[0],
                    "todays_back_price_4_place": group[
                        "todays_back_price_4_place"
                    ].iloc[0],
                    "todays_back_price_4_depth_place": group[
                        "todays_back_price_4_depth_place"
                    ].iloc[0],
                    "todays_back_price_5_place": group[
                        "todays_back_price_5_place"
                    ].iloc[0],
                    "todays_back_price_5_depth_place": group[
                        "todays_back_price_5_depth_place"
                    ].iloc[0],
                    "todays_lay_price_1_place": group["todays_lay_price_1_place"].iloc[
                        0
                    ],
                    "todays_lay_price_1_depth_place": group[
                        "todays_lay_price_1_depth_place"
                    ].iloc[0],
                    "todays_lay_price_2_place": group["todays_lay_price_2_place"].iloc[
                        0
                    ],
                    "todays_lay_price_2_depth_place": group[
                        "todays_lay_price_2_depth_place"
                    ].iloc[0],
                    "todays_lay_price_3_place": group["todays_lay_price_3_place"].iloc[
                        0
                    ],
                    "todays_lay_price_3_depth_place": group[
                        "todays_lay_price_3_depth_place"
                    ].iloc[0],
                    "todays_lay_price_4_place": group["todays_lay_price_4_place"].iloc[
                        0
                    ],
                    "todays_lay_price_4_depth_place": group[
                        "todays_lay_price_4_depth_place"
                    ].iloc[0],
                    "todays_lay_price_5_place": group["todays_lay_price_5_place"].iloc[
                        0
                    ],
                    "todays_lay_price_5_depth_place": group[
                        "todays_lay_price_5_depth_place"
                    ].iloc[0],
                    "todays_total_matched_event_place": group[
                        "todays_total_matched_event_place"
                    ].iloc[0],
                    "todays_percent_back_win_book_place": group[
                        "todays_percent_back_win_book_place"
                    ].iloc[0],
                    "todays_percent_lay_win_book_place": group[
                        "todays_percent_lay_win_book_place"
                    ].iloc[0],
                    "performance_data": group.drop(
                        columns=[
                            "horse_id",
                            "horse_name",
                            "first_places",
                            "second_places",
                            "third_places",
                            "fourth_places",
                            "todays_betfair_win_sp",
                            "todays_betfair_place_sp",
                        ]
                    ).to_dict(orient="records"),
                }
                for (horse_id, name), group in grouped
            ],
        }
        return self.sanitize_nan(data)

    def sanitize_nan(self, data):
        """Replace NaN values and pandas NA with None in nested structures."""
        if isinstance(data, dict):
            return {k: self.sanitize_nan(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_nan(item) for item in data]
        elif isinstance(data, float) and np.isnan(data):
            return None
        elif pd.isna(data) or data is pd.NA:  # Catch pandas NA values
            return None
        elif isinstance(data, pd.Int64Dtype):  # Handle Int64 type
            return int(data) if pd.notna(data) else None
        elif isinstance(data, pd.Series):
            return data.where(pd.notna(data), None)
        return data
