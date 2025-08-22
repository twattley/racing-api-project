import re

import numpy as np
import pandas as pd


class TransformationService:
    def __init__(self):
        pass

    @staticmethod
    def _sort_data(data: pd.DataFrame) -> pd.DataFrame:
        return data.sort_values(by=["horse_id", "race_date"])

    @staticmethod
    def _create_tmp_vars(data: pd.DataFrame, date: str) -> pd.DataFrame:
        return data.assign(
            race_date_tmp=pd.to_datetime(data["race_date"], errors="coerce"),
            todays_date_tmp=pd.to_datetime(date, errors="coerce"),
        )

    @staticmethod
    def _create_days_since_last_ran(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            days_since_last_ran=data.sort_values("race_date_tmp")
            .groupby("horse_id")["race_date_tmp"]
            .diff()
            .dt.days.astype("Int64")
        )

        return data.assign(weeks_since_last_ran=data["days_since_last_ran"] // 7)

    @staticmethod
    def _create_number_of_runs(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            number_of_runs=data.groupby("horse_id")["race_time"].transform(
                lambda x: x.rank(method="first").astype("Int64")
            )
        )
        return data.assign(
            number_of_runs=data["number_of_runs"].fillna(0).astype(int) - 1
        )

    @staticmethod
    def _create_days_since_performance(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            days_since_performance=(
                data["todays_date_tmp"] - data["race_date_tmp"]
            ).dt.days
        )
        return data.assign(weeks_since_performance=data["days_since_performance"] // 7)

    @staticmethod
    def _calculate_combined_ratings(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            rating=lambda data: np.where(
                data["tfr"].isnull() & data["rpr"].notnull(),
                data["rpr"],
                np.where(
                    data["rpr"].isnull() & data["tfr"].notnull(),
                    data["tfr"],
                    ((data["tfr"] + data["rpr"]) / 2),
                ),
            ),
            speed_figure=lambda data: np.where(
                data["ts"].isnull() & data["tfig"].notnull(),
                data["tfig"],
                np.where(
                    data["tfig"].isnull() & data["ts"].notnull(),
                    data["ts"],
                    ((data["ts"] + data["tfig"]) / 2),
                ),
            ),
        )
        data["rating"] = data["rating"].round(0).fillna(0).astype(int).replace(0, None)
        data["speed_figure"] = (
            data["speed_figure"].round(0).fillna(0).astype(int).replace(0, None)
        )

        data = data.assign(
            rating_from_or=np.select(
                [
                    data["official_rating"].isnull(),
                    data["official_rating"] == 0,
                    data["rating"].isnull(),
                    data["rating"] == 0,
                    (data["official_rating"].notnull())
                    & (data["rating"].notnull())
                    & (data["official_rating"] != 0)
                    & (data["rating"] != 0),
                ],
                [0, 0, 0, 0, data["rating"] - data["official_rating"]],
                default=0,
            ),
            speed_figure_from_or=np.select(
                [
                    data["official_rating"].isnull(),
                    data["official_rating"] == 0,
                    data["speed_figure"].isnull(),
                    data["speed_figure"] == 0,
                    (data["official_rating"].notnull())
                    & (data["speed_figure"].notnull())
                    & (data["official_rating"] != 0)
                    & (data["speed_figure"] != 0),
                ],
                [0, 0, 0, 0, data["speed_figure"] - data["official_rating"]],
                default=0,
            ),
        )
        return data

    @staticmethod
    def _calculate_ratings_bands(data: pd.DataFrame) -> pd.DataFrame:
        def extract_age_and_max_rating(text):
            age_range_pattern = r"(\d+yo\+?)|(\d+-(\d+))"
            matches = re.findall(age_range_pattern, text)
            age_range = next((match[0] for match in matches if match[0]), None)
            max_rating = next((match[2] for match in matches if match[2]), None)
            return pd.Series({"age_range": age_range, "max_rating": max_rating})

        data[["age_range", "hcap_range"]] = data["conditions"].apply(
            extract_age_and_max_rating
        )

        data["hcap_range"] = (
            pd.to_numeric(data["hcap_range"], errors="coerce").fillna(0).astype(int)
        )

        data["hcap_range"] = np.where(data["hcap_range"] < 20, None, data["hcap_range"])

        return data

    @staticmethod
    def _calculate_rating_diffs(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            median_horse_rating=data.groupby("horse_id")["rating"].transform("median"),
            median_horse_speed=data.groupby("horse_id")["speed_figure"].transform(
                "median"
            ),
        )
        return data.assign(
            rating_diff=pd.to_numeric(
                (data["rating"] - data["median_horse_rating"]), errors="coerce"
            )
            .round(0)
            .fillna(0)
            .astype(int),
            speed_rating_diff=pd.to_numeric(
                (data["speed_figure"] - data["median_horse_speed"]), errors="coerce"
            )
            .round(0)
            .fillna(0)
            .astype(int),
        )

    @staticmethod
    def _round_price_data(data: pd.DataFrame) -> pd.DataFrame:
        def custom_round(x):
            if x is None:
                return None
            if abs(x) >= 10:
                return round(x)
            else:
                return round(x, 1)

        return data.assign(
            betfair_win_sp=data["betfair_win_sp"].apply(custom_round),
            betfair_place_sp=data["betfair_place_sp"].apply(custom_round),
        )

    @staticmethod
    def _calculate_places(data: pd.DataFrame) -> pd.DataFrame:
        data = data.sort_values(by=["horse_id", "race_time"])
        data["shifted_finishing_position"] = data.groupby("horse_id")[
            "finishing_position"
        ].shift(1, fill_value="0")

        data = data.assign(
            first_places=(data["shifted_finishing_position"] == "1")
            .groupby(data["horse_id"])
            .cumsum(),
            second_places=(data["shifted_finishing_position"] == "2")
            .groupby(data["horse_id"])
            .cumsum(),
            third_places=(
                (data["shifted_finishing_position"] == "3")
                & (data["number_of_runners"] > 7)
            )
            .groupby(data["horse_id"])
            .cumsum(),
            fourth_places=(
                (data["shifted_finishing_position"] == "4")
                & (data["number_of_runners"] > 12)
            )
            .groupby(data["horse_id"])
            .cumsum(),
        )
        data.drop(columns=["shifted_finishing_position"], inplace=True)

        data = data.assign(
            win_percentage=(data["first_places"] / data["number_of_runs"]) * 100,
            place_percentage=(
                (
                    data["first_places"]
                    + data["second_places"]
                    + data["third_places"]
                    + data["fourth_places"]
                )
                / data["number_of_runs"]
            )
            * 100,
        )

        data = data.assign(
            win_percentage=data["win_percentage"].fillna(0).round(0).astype(int),
            place_percentage=data["place_percentage"].fillna(0).round(0).astype(int),
        )

        return data

    @staticmethod
    def _calculate_volatility(data: pd.DataFrame) -> pd.DataFrame:
        def calculate_cv(x):
            valid_ratings = x.dropna()
            if len(valid_ratings) >= 2:  # Need at least 2 ratings for std
                return valid_ratings.std() / valid_ratings.mean() * 100
            return np.nan

        cv_values = data.groupby("horse_id")["rating"].transform(calculate_cv)
        median_cv = cv_values.median()
        data = data.assign(volatility_index=cv_values.fillna(median_cv))
        data = data.assign(
            volatility_index=data["volatility_index"].round(0).astype(int)
        )
        return data

    @staticmethod
    def _create_distance_diff(data: pd.DataFrame) -> pd.DataFrame:
        todays_distance = data[data["data_type"] == "today"]["distance_yards"].iloc[0]
        return data.assign(
            distance_diff=(data["distance_yards"] - todays_distance).round(-2)
        )

    @staticmethod
    def _create_class_diff(data: pd.DataFrame) -> pd.DataFrame:
        todays_class = data[data["data_type"] == "today"]["race_class"].iloc[0]
        return data.assign(
            class_diff=np.select(
                [
                    data["race_class"] < todays_class,
                    data["race_class"] == todays_class,
                    data["race_class"] > todays_class,
                ],
                ["higher", "same", "lower"],
                default=None,
            )
        )

    @staticmethod
    def _create_rating_range_diff(data: pd.DataFrame) -> pd.DataFrame:
        todays_rating_range_diff = data[data["data_type"] == "today"][
            "hcap_range"
        ].iloc[0]
        return data.assign(
            rating_range_diff=np.select(
                [
                    data["hcap_range"] > todays_rating_range_diff,
                    data["hcap_range"] == todays_rating_range_diff,
                    data["hcap_range"] < todays_rating_range_diff,
                ],
                ["higher", "same", "lower"],
                default=None,
            )
        )

    @staticmethod
    def _cleanup_temp_vars(data: pd.DataFrame) -> pd.DataFrame:
        return data.drop(columns=["race_date_tmp", "todays_date_tmp"])

    @staticmethod
    def _create_todays_rating(data: pd.DataFrame) -> pd.DataFrame:
        today = pd.to_datetime(data[data["data_type"] == "today"]["race_date"].iloc[0])
        two_years_ago = today - pd.DateOffset(years=2)

        data = data.assign(
            speed_figure=pd.to_numeric(data["speed_figure"], errors="coerce")
            .fillna(0)
            .round(0)
            .astype(int)
            .replace(0, None),
            rating=pd.to_numeric(data["rating"], errors="coerce")
            .fillna(0)
            .round(0)
            .astype(int)
            .replace(0, None),
            rank=data.groupby("horse_id")["race_date"].rank(
                ascending=False, method="dense"
            ),
            race_time=pd.to_datetime(data["race_time"]),
        )

        hist_filtered_data = data[
            (data["race_time"] >= two_years_ago)
            & (data["rank"] <= 6)
            & (data["data_type"] == "historical")
        ].copy()

        speed_ratings = {}
        ratings = {}
        for horse in data["horse_id"].unique():
            horse_df = hist_filtered_data[hist_filtered_data["horse_id"] == horse]

            if horse_df.empty:
                continue

            min_rating = horse_df["rating"].min()
            min_unique_id = horse_df[horse_df["rating"] == min_rating].iloc[0][
                "unique_id"
            ]
            min_removed = horse_df[~(horse_df["unique_id"] == min_unique_id)]

            if min_removed.empty:
                continue

            horse_mean_speed = min_removed["speed_figure"].mean()
            horse_mean_rating = min_removed["rating"].mean()
            horse_median_speed = min_removed["speed_figure"].median()
            horse_median_rating = min_removed["rating"].median()

            if pd.isna(horse_mean_speed) or pd.isna(horse_median_speed):
                calculated_speed = 0
            else:
                calculated_speed = round((horse_median_speed + horse_mean_speed) // 2)

            if pd.isna(horse_mean_rating) or pd.isna(horse_median_rating):
                calculated_rating = 0
            else:
                calculated_rating = round(
                    (horse_median_rating + horse_mean_rating) // 2
                )

            speed_ratings[int(horse)] = calculated_speed
            ratings[int(horse)] = calculated_rating
        historical = data[data["data_type"] == "historical"]
        today = data[data["data_type"] == "today"]

        today = today.assign(
            speed_figure=today["horse_id"].map(speed_ratings),
            rating=today["horse_id"].map(ratings),
        )
        median_speed_figure = today["speed_figure"].median()
        median_rating = today["rating"].median()

        today = today.assign(
            speed_figure=today["speed_figure"].fillna(median_speed_figure),
            rating=today["rating"].fillna(median_rating),
        )

        today["rating"] = (
            today["rating"].round(0).fillna(0).astype(int).replace(0, None)
        )
        today["speed_figure"] = (
            today["speed_figure"].round(0).fillna(0).astype(int).replace(0, None)
        )

        return pd.concat([historical, today]).drop_duplicates(subset=["unique_id"])

    @staticmethod
    def calculate(data: pd.DataFrame, date: str) -> pd.DataFrame:
        data = (
            TransformationService._create_tmp_vars(data, date)
            .pipe(TransformationService._sort_data)
            .pipe(TransformationService._create_days_since_performance)
            .pipe(TransformationService._create_days_since_last_ran)
            .pipe(TransformationService._create_number_of_runs)
            .pipe(TransformationService._calculate_places)
            .pipe(TransformationService._create_distance_diff)
            .pipe(TransformationService._calculate_combined_ratings)
            .pipe(TransformationService._create_todays_rating)
            .pipe(TransformationService._calculate_rating_diffs)
            .pipe(TransformationService._round_price_data)
            .pipe(TransformationService._cleanup_temp_vars)
            .pipe(TransformationService._calculate_ratings_bands)
            .pipe(TransformationService._create_class_diff)
            .pipe(TransformationService._create_rating_range_diff)
            .pipe(TransformationService._calculate_volatility)
        )

        return data

    def transform_collateral_form_data(self, data: pd.DataFrame) -> pd.DataFrame:
        data = TransformationService._calculate_combined_ratings(data)
        return data
