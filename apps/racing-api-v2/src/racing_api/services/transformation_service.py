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
    def _filter_last_two_years(data: pd.DataFrame) -> pd.DataFrame:
        today = pd.to_datetime(data[data["data_type"] == "today"]["race_date"].iloc[0])
        two_years_ago = today - pd.DateOffset(years=2)

        return data[
            (data["race_time"] >= two_years_ago)
            & (data["rank"] <= 6)
            & (data["data_type"] == "historical")
        ]

    @staticmethod
    def calculate(data: pd.DataFrame, date: str) -> pd.DataFrame:
        data = (
            data.pipe(TransformationService._round_price_data)
            .pipe(TransformationService._sort_data)
            .pipe(TransformationService._filter_last_two_years)
        )

        return data
