from src.interfaces.data_store import DataStore
from api_helpers.helpers.logging_config import I
import pandas as pd


class ParquetDataStore(DataStore):
    def __init__(self, raw_data_path: str, latest_data_path: str):
        self.raw_data_path = raw_data_path
        self.latest_data_path = latest_data_path

    def get_data(self, date: str):
        file_name = f"{self.raw_data_path}_{date}.parquet"
        try:
            data = pd.read_parquet(file_name)
            I(f"Loaded {len(data)} rows from {file_name}")
            return data
        except FileNotFoundError:
            return pd.DataFrame(
                columns=[
                    "race_time",
                    "race_date",
                    "horse_id",
                    "horse_name",
                    "course",
                    "betfair_win_sp",
                    "betfair_place_sp",
                    "created_at",
                    "status",
                    "market_id_win",
                    "market_id_place",
                ]
            )

    def store_raw_data(self, data: pd.DataFrame, date: str):
        file_name = f"{self.raw_data_path}_{date}.parquet"
        I(f"Storing {len(data)} rows to {file_name}.")
        data.to_parquet(file_name, index=False, engine="pyarrow")

    def store_data_updates(self, data: pd.DataFrame, date: str):
        file_name = f"{self.latest_data_path}_{date}.parquet"
        I(f"Storing {len(data)} rows to {file_name}")
        data.to_parquet(file_name, index=False, engine="pyarrow")
