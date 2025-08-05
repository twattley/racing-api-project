import re

import numpy as np
import pandas as pd
from api_helpers.helpers.logging_config import I


class DataTransformer:
    DISTANCE_MAP = {
        "1m": 1760,
        "1m½f": 1870,
        "1m1½f": 2090,
        "1m1f": 1980,
        "1m2½f": 2310,
        "1m2f": 2200,
        "1m3½f": 2530,
        "1m3f": 2420,
        "1m4½f": 2750,
        "1m4f": 2640,
        "1m5½f": 2970,
        "1m5f": 2860,
        "1m6½f": 3190,
        "1m6f": 3080,
        "1m7½f": 3410,
        "1m7f": 3300,
        "2m": 3520,
        "2m½f": 3630,
        "2m1½f": 3850,
        "2m1f": 3740,
        "2m2½f": 4070,
        "2m2f": 3960,
        "2m3½f": 4290,
        "2m3f": 4180,
        "2m4½f": 4510,
        "2m4f": 4400,
        "2m5½f": 4730,
        "2m5f": 4620,
        "2m6½f": 4950,
        "2m6f": 4840,
        "2m7½f": 5170,
        "2m7f": 5060,
        "3m": 5280,
        "3m½f": 5390,
        "3m1½f": 5610,
        "3m1f": 5500,
        "3m2½f": 5830,
        "3m2f": 5720,
        "3m3½f": 6150,
        "3m3f": 5940,
        "3m4½f": 6270,
        "3m4f": 6160,
        "3m5½f": 6490,
        "3m5f": 6380,
        "3m6½f": 6710,
        "3m6f": 6600,
        "3m7½f": 6930,
        "3m7f": 6820,
        "4m": 7040,
        "4m½f": 7150,
        "4m1½f": 7370,
        "4m1f": 7260,
        "4m2½f": 7590,
        "4m2f": 7480,
        "4m3f": 7700,
        "4m4f": 7920,
        "5½f": 1210,
        "5f": 1100,
        "6½f": 1430,
        "6f": 1320,
        "7½f": 1650,
        "7f": 1540,
    }

    COLOUR_MAP = {
        "b": "Bay",
        "ch": "Chestnut",
        "bb": "Blood Bay",
        "bl": "Blue",
        "br": "Brown",
        "gr": "Grey",
        "rg": "Roan",
        "ro": "Roan",
        "bg": "Bay",
        "gb": "Grey Bay",
        "bz": "Bronze",
        "bk": "Black",
        "sk": "Skewbald",
        "wh": "White",
    }
    SEX_MAP = {
        "c": "Colt",
        "f": "Filly",
        "g": "Gelding",
        "h": "Horse",
        "m": "Mare",
        "r": "Ridgling",
    }

    @staticmethod
    def check_todays_data(data: pd.DataFrame) -> bool:
        return data["data_type"].unique() == ["today"]

    @staticmethod
    def time_to_seconds(time_str):
        """Convert a time string in format 'Xm Ys' to total seconds."""
        parts = re.split("[msh]", time_str.strip())
        seconds = 0.0
        if "m" in time_str:
            seconds += float(parts[0]) * 60
            parts.pop(0)
        if parts and parts[0]:
            seconds += float(parts[0])
        return seconds

    @staticmethod
    def process_time_strings(s: str) -> tuple[float, str, float]:
        if s in {"0.00s (standard time)", "0.00s", ""}:
            return np.nan, np.nan, np.nan
        if "(standard time)" in s:
            return (
                round(
                    DataTransformer.time_to_seconds(s.replace("(standard time)", "")), 2
                ),
                "standard",
                0.0,
            )
        if "(" not in s:
            return round(DataTransformer.time_to_seconds(s), 2), None, None
        outside, inside = re.match(r"([^\(]+)\(([^)]+)\)", s).groups()
        relative_to_standard = inside.split("by")[0].strip()
        relative_time = DataTransformer.time_to_seconds(inside.split("by")[1].strip())
        total_seconds_time = DataTransformer.time_to_seconds(outside.strip())

        return (
            round(total_seconds_time, 2),
            relative_to_standard,
            round(relative_time, 2),
        )

    @staticmethod
    def create_pounds(data: pd.DataFrame) -> pd.DataFrame:
        I("Creating pounds")
        data["weight_carried_st"] = (
            data["weight_carried"]
            .str.split("-")
            .str.get(0)
            .str.extract(r"(\d+)")
            .astype("Int64")
        )
        data["weight_carried_extra_lbs"] = (
            data["weight_carried"]
            .str.split("-")
            .str.get(1)
            .str.extract(r"(\d+)")
            .astype("Int64")
        )
        data["weight_carried_lbs"] = (data["weight_carried_st"] * 14) + data[
            "weight_carried_extra_lbs"
        ]

        return data

    @staticmethod
    def get_tf_rating_view(rating: str) -> str:
        if pd.isna(rating) or not rating:
            return "neutral"
        if rating.endswith("+"):
            return "positive"
        elif rating.endswith("?"):
            return "questionable"
        else:
            return "neutral"

    @staticmethod
    def get_tf_rating_values(data: pd.DataFrame) -> pd.DataFrame:
        if DataTransformer.check_todays_data(data):
            return data.assign(tfr_view=None)
        I("Getting tf rating values")
        return data.assign(
            tfr_view=data["tfr"].apply(DataTransformer.get_tf_rating_view)
        )

    @staticmethod
    def get_surface_type(rating: str) -> str:
        if pd.isna(rating) or not rating:
            return "turf"
        if rating.startswith("a"):
            return "artificial"
        elif rating.startswith("t"):
            return "tapeta"
        elif rating.startswith("p"):
            return "polytrack"
        elif rating.startswith("f"):
            return "fibresand"
        else:
            return "turf"

    @staticmethod
    def get_surfaces_from_tf_rating(data: pd.DataFrame) -> pd.DataFrame:
        if DataTransformer.check_todays_data(data):
            return data.assign(surface=None)
        I("Getting surfaces from tf rating")
        return data.assign(surface=data["tfr"].apply(DataTransformer.get_surface_type))

    @staticmethod
    def get_inplay_high_and_low(data: pd.DataFrame) -> pd.DataFrame:
        if DataTransformer.check_todays_data(data):
            return data.assign(in_play_low=np.nan, in_play_high=np.nan)
        I("Getting inplay high and low")
        return data.assign(
            in_play_low=pd.to_numeric(
                data["in_play_prices"].str.split("/").str.get(1), errors="coerce"
            ).astype(float),
            in_play_high=pd.to_numeric(
                data["in_play_prices"].str.split("/").str.get(0), errors="coerce"
            ).astype(float),
        )

    @staticmethod
    def convert_headgear(e: str) -> str:
        if not e:
            return np.nan
        headgear_mapping = {
            "b": "blinkers",
            "t": "tongue tie",
            "p": "cheekpieces",
            "v": "visor",
            "h": "hood",
            "e/s": "eye shield",
            "e": "eye shield",
        }

        headgear = []
        for i, value in headgear_mapping.items():
            if f"{i}1" in e:
                headgear.append(f"{value} (first time)")
                e = e.replace(f"{i}1", "")
            elif i in e:
                headgear.append(value)
                e = e.replace(i, "")

        first_time_headgear = [i for i in headgear if "first time" in i]

        if first_time_headgear:
            first_time_headgear.extend([i for i in headgear if "first time" not in i])
            return ", ".join(first_time_headgear)

        if not headgear and e:
            raise ValueError(f"Unknown headgear code: {e}")
        return ", ".join(headgear)

    @staticmethod
    def convert_horse_type_to_colour_sex(data: pd.DataFrame) -> pd.DataFrame:
        if set(data["horse_type"]) == {""}:
            return data.assign(horse_colour="Unknown", horse_sex="Unknown")
        return data.assign(
            horse_colour=data["horse_type"]
            .str.split(" ")
            .str.get(0)
            .str.strip()
            .map(DataTransformer.COLOUR_MAP),
            horse_sex=data["horse_type"]
            .str.replace("1", "")
            .str.split(" ")
            .str.get(1)
            .str.strip()
            .map(DataTransformer.SEX_MAP),
        )

    @staticmethod
    def create_distance_beaten_data(data: pd.DataFrame) -> pd.DataFrame:
        if DataTransformer.check_todays_data(data):
            return data.assign(
                total_distance_beaten=np.nan,
            )
        I("Creating distance beaten data")
        data = data.drop(columns=["total_distance_beaten"]).rename(
            columns={"adj_total_distance_beaten": "total_distance_beaten"}
        )
        return data

    @staticmethod
    def calculate_ratings_bands(data: pd.DataFrame) -> pd.DataFrame:
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
    def clean_race_class_field(data: pd.DataFrame) -> pd.DataFrame:
        I("Cleaning race class field")
        data["race_class"] = (
            data["race_class"]
            .str.replace("(Class", "")
            .str.replace(")", "")
            .str.strip()
            .astype("Int64")
        )
        return data

    @staticmethod
    def create_distance_data(data: pd.DataFrame) -> pd.DataFrame:
        I("Creating yards from furlongs")
        data = data.assign(
            distance_yards=data["distance"].map(DataTransformer.DISTANCE_MAP)
        )
        data = data.assign(
            distance_meters=lambda x: x["distance_yards"] * 0.9144,
        )
        data = data.assign(distance_kilometers=lambda x: x["distance_meters"] / 1000)
        return data

    @staticmethod
    def create_time_data(data: pd.DataFrame) -> pd.DataFrame:
        if DataTransformer.check_todays_data(data):
            return data.assign(
                time_seconds=np.nan,
                relative_to_standard=None,
                relative_time=np.nan,
            )
        I("Creating time data")
        data[["time_seconds", "relative_to_standard", "relative_time"]] = data[
            "winning_time"
        ].apply(lambda x: pd.Series(DataTransformer.process_time_strings(x)))
        return data

    @staticmethod
    def convert_tf_rating(data: pd.DataFrame) -> pd.DataFrame:
        if DataTransformer.check_todays_data(data):
            return data
        I("Converting tf rating")
        return data.assign(tfr=data["tfr"].str.extract(r"(\d+)").astype("Int64"))

    @staticmethod
    def create_headgear_data(data: pd.DataFrame) -> pd.DataFrame:
        I("Creating headgear data")
        return data.assign(
            headgear=lambda x: x["headgear"].apply(DataTransformer.convert_headgear)
        )

    @staticmethod
    def calculate_combined_ratings(data: pd.DataFrame) -> pd.DataFrame:
        data = data.assign(
            tfr_numeric=pd.to_numeric(data["tfr"], errors="coerce"),
            rpr_numeric=pd.to_numeric(data["rpr"], errors="coerce"),
            ts_numeric=pd.to_numeric(data["ts"], errors="coerce"),
            tfig_numeric=pd.to_numeric(data["tfig"], errors="coerce"),
        )
        data = data.assign(
            rating=lambda data: np.where(
                data["tfr_numeric"].isnull() & data["rpr_numeric"].notnull(),
                data["rpr_numeric"],
                np.where(
                    data["rpr_numeric"].isnull() & data["tfr_numeric"].notnull(),
                    data["tfr_numeric"],
                    ((data["tfr_numeric"] + data["rpr_numeric"]) / 2),
                ),
            ),
            speed_figure=lambda data: np.where(
                data["ts_numeric"].isnull() & data["tfig_numeric"].notnull(),
                data["tfig_numeric"],
                np.where(
                    data["tfig_numeric"].isnull() & data["ts_numeric"].notnull(),
                    data["ts_numeric"],
                    ((data["ts_numeric"] + data["tfig_numeric"]) / 2),
                ),
            ),
        )

        data = data.drop(
            columns=[
                "tfr_numeric",
                "rpr_numeric",
                "ts_numeric",
                "tfig_numeric",
            ]
        )
        data["rating"] = data["rating"].round(0).fillna(0).astype(int).replace(0, None)
        data["speed_figure"] = (
            data["speed_figure"].round(0).fillna(0).astype(int).replace(0, None)
        )
        return data

    @staticmethod
    def create_artificial_sp(df) -> pd.DataFrame:
        I("Creating artificial sp")
        df["betfair_win_sp"] = pd.to_numeric(df["betfair_win_sp"], errors="coerce")
        df["industry_sp_tmp"] = df["industry_sp"].str.replace(
            r"[a-zA-Z]", "", regex=True
        )
        df["numerator"] = pd.to_numeric(
            df["industry_sp_tmp"].str.split("/").str[0], errors="coerce"
        )
        df["denominator"] = pd.to_numeric(
            df["industry_sp_tmp"].str.split("/").str[1], errors="coerce"
        )
        df["industry_sp_clean"] = (df["numerator"] / df["denominator"]) + 1
        df["industry_sp_clean"] = df["industry_sp_clean"].round(2)
        df["industry_sp_clean"] = np.where(
            df["industry_sp"].str.contains("Ev"), 2, df["industry_sp_clean"]
        )
        df["betfair_win_sp"] = df["betfair_win_sp"].fillna(df["industry_sp_clean"])

        return df

    @staticmethod
    def transform_data(
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        data = (
            data.pipe(DataTransformer.get_surfaces_from_tf_rating)
            .pipe(DataTransformer.get_tf_rating_values)
            .pipe(DataTransformer.create_pounds)
            .pipe(DataTransformer.get_inplay_high_and_low)
            .pipe(DataTransformer.create_distance_data)
            .pipe(DataTransformer.create_time_data)
            .pipe(DataTransformer.create_headgear_data)
            .pipe(DataTransformer.convert_tf_rating)
            .pipe(DataTransformer.clean_race_class_field)
            .pipe(DataTransformer.convert_horse_type_to_colour_sex)
            .pipe(DataTransformer.create_distance_beaten_data)
            .pipe(DataTransformer.create_artificial_sp)
            .pipe(DataTransformer.calculate_combined_ratings)
            .pipe(DataTransformer.calculate_ratings_bands)
        )
        return data
