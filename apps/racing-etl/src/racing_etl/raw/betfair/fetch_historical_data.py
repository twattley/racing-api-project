import bz2
import hashlib
import json
import os
from calendar import monthrange
from datetime import date, datetime, timezone
from io import StringIO
from typing import Optional

import numpy as np
import pandas as pd
import pytz
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.betfair_client import (
    BetFairClient,
    BetfairHistoricalDataParams,
)
from api_helpers.config import Config, config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import PipelineStatus
from ...raw.betfair.betfair_cache import BetfairCache


class BetfairDataProcessor:
    def __init__(self, config: Config, pipeline_status: PipelineStatus):
        self.config = config
        self.pipeline_status = pipeline_status

    def process_data(self, market_data: list[dict], filename: str) -> pd.DataFrame:
        opening_data = BetfairDataProcessor.get_market_data(market_data)
        sp_dict = BetfairDataProcessor.get_sp_data(market_data, opening_data)
        market_def = market_data[0]["mc"][0]["marketDefinition"]
        market_time = pd.to_datetime(market_def["marketTime"], utc=True)
        start_time = datetime(
            market_time.year,
            market_time.month,
            market_time.day,
            10,
            00,
            tzinfo=pytz.utc,
        )
        market = BetfairDataProcessor.create_market_dataset(
            market_data, opening_data, sp_dict
        )
        df = BetfairDataProcessor.remove_early_nr(market, start_time)
        df = create_unique_ids(df)
        if "REMOVED" not in df.status.unique():
            df = BetfairDataProcessor.create_percentage_moves(df)
            df = self.create_price_change_dataset(df)
        else:
            df = self.create_price_change_dataset_nrs(df)
        df = df.assign(race_date=df["race_time"].dt.date, filename=filename)

        return df

    @staticmethod
    def check_abandoned(market_updates: list[dict]) -> bool:
        return {
            runner["status"]
            for runner in market_updates[-1]["mc"][0]["marketDefinition"]["runners"]
        } == {"REMOVED"}

    @staticmethod
    def get_sp_data(
        market_updates: list[dict], opening_prices: pd.DataFrame
    ) -> pd.DataFrame:
        sp_data = pd.DataFrame(
            market_updates[-1]["mc"][0]["marketDefinition"]["runners"]
        )[["bsp", "id", "name", "status"]]
        sp_data["course"] = opening_prices["course"]
        sp_data["race_time"] = opening_prices["race_time"]
        sp_data["race_type"] = opening_prices["race_type"]
        sp_data["market_change_time"] = sp_data["race_time"]
        sp_data["removal_update"] = False
        sp_data.rename(
            columns={
                "id": "runner_id",
                "name": "runner_name",
                "bsp": "price",
            },
            inplace=True,
        )

        return sp_data

    @staticmethod
    def get_market_data(market_updates: list[dict]) -> pd.DataFrame:
        market_def = market_updates[0]["mc"][0]["marketDefinition"]
        race_time = pd.to_datetime(market_def["marketTime"], utc=True)
        start_time = datetime.fromtimestamp(market_updates[0]["pt"] / 1000.0).replace(
            tzinfo=pytz.utc
        )

        return pd.DataFrame(
            [
                {
                    "course": market_def["venue"],
                    "race_time": race_time,
                    "race_type": market_def["name"],
                    "runner_id": runner["id"],
                    "runner_name": runner["name"],
                    "price": np.nan,
                    "market_change_time": start_time,
                    "status": runner["status"],
                    "removal_update": False,
                }
                for runner in market_def["runners"]
            ]
        )

    @staticmethod
    def remove_early_nr(market: pd.DataFrame, start_time: pd.Timestamp) -> pd.DataFrame:
        early_nr = list(
            market[
                (market["status"] == "REMOVED")
                & (market["market_change_time"] <= start_time)
            ]["runner_name"].unique()
        )
        return market[
            ~(market["runner_name"].isin(early_nr))
            & (market["market_change_time"] >= start_time)
        ]

    @staticmethod
    def create_market_dataset(
        market_updates: list[dict], opening_data: pd.DataFrame, sp_dict: dict
    ) -> pd.DataFrame:
        race_time = opening_data["race_time"].iloc[0]
        runner_map = dict(zip(opening_data["runner_id"], opening_data["runner_name"]))
        market = []
        removals = []
        for change in market_updates[1:]:
            market_change_time = datetime.fromtimestamp(
                change["pt"] / 1000.0, timezone.utc
            )
            if market_change_time >= race_time:
                break
            for runner in change["mc"]:
                if "marketDefinition" not in runner.keys():
                    changes = runner["rc"]
                    for change in changes:
                        runner_id = change["id"]
                        runner_name = runner_map[runner_id]
                        price = change["ltp"]
                        market.append(
                            {
                                "course": np.nan,
                                "race_time": np.nan,
                                "race_type": np.nan,
                                "runner_id": runner_id,
                                "runner_name": runner_name,
                                "price": price,
                                "market_change_time": market_change_time,
                                "removal_update": False,
                            }
                        )
                elif "marketDefinition" in runner.keys():
                    market_def = runner["marketDefinition"]
                    for runner in market_def["runners"]:
                        removal_update_indicator = (
                            runner["status"] == "REMOVED"
                            and runner["name"] not in removals
                        )
                        runner_dict = {
                            "course": market_def["venue"],
                            "race_time": race_time,
                            "race_type": market_def["name"],
                            "runner_id": runner["id"],
                            "runner_name": runner["name"],
                            "status": runner["status"],
                            "price": np.nan,
                            "market_change_time": market_change_time,
                            "removal_update": removal_update_indicator,
                        }
                        market.append(runner_dict)
        market = (
            pd.concat([pd.DataFrame(market), opening_data, sp_dict])
            .sort_values("market_change_time")
            .drop_duplicates()
        )

        market["course"] = market["course"].ffill()
        market["course"] = market["course"].bfill()
        market["race_time"] = market["race_time"].ffill()
        market["race_time"] = market["race_time"].bfill()
        market["race_type"] = market["race_type"].ffill()
        market["race_type"] = market["race_type"].bfill()
        market["market_change_time"] = market["market_change_time"].ffill()
        market["market_change_time"] = market["market_change_time"].bfill()

        market["price"] = market.groupby("runner_id")["price"].bfill()
        market["price"] = market.groupby("runner_id")["price"].ffill()
        market["status"] = market.groupby("runner_id")["status"].ffill()
        market = market.reset_index(drop=True)
        return market

    @staticmethod
    def create_percentage_moves(df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values(by="market_change_time")
        df = df.assign(
            min_price=df.groupby(["runner_id"])["price"].transform("min"),
            max_price=df.groupby(["runner_id"])["price"].transform("max"),
            latest_price=df.groupby(["runner_id"])["price"].transform("last"),
            earliest_price=df.groupby(["runner_id"])["price"].transform("first"),
        )

        df = df.assign(
            price_change=round(
                ((100 / df["earliest_price"]) - (100 / df["latest_price"])), 2
            )
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )
        return df.drop_duplicates(subset=["runner_id"])

    def create_price_change_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        self.pipeline_status.add_info(
            "Creating dataset of price changes without non runners"
        )
        price_changes = []
        for horse in df.runner_name.unique():
            horse_df = (
                df[df.runner_name == horse]
                .drop_duplicates(subset=["runner_id"])
                .assign(non_runners=False)
            )
            price_changes.append(
                {
                    "horse": horse_df["runner_name"].iloc[0],
                    "course": horse_df["course"].iloc[0],
                    "race_time": horse_df["race_time"].iloc[0],
                    "race_type": horse_df["race_type"].iloc[0],
                    "runner_id": horse_df["runner_id"].iloc[0],
                    "race_key": horse_df["race_key"].iloc[0],
                    "bf_unique_id": horse_df["bf_unique_id"].iloc[0],
                    "min_price": horse_df["min_price"].iloc[0],
                    "max_price": horse_df["max_price"].iloc[0],
                    "latest_price": horse_df["latest_price"].iloc[0],
                    "earliest_price": horse_df["earliest_price"].iloc[0],
                    "price_change": horse_df["price_change"].iloc[0],
                    "non_runners": horse_df["non_runners"].iloc[0],
                }
            )
        return pd.DataFrame(price_changes)

    @staticmethod
    def get_final_starters(df: pd.DataFrame) -> list:
        return list(
            df[
                (df["race_time"] == df["market_change_time"])
                & (df["status"] != "REMOVED")
            ]["runner_name"].unique()
        )

    @staticmethod
    def get_removals(df: pd.DataFrame) -> dict:
        removals = {}
        for i in df.itertuples():
            if i.status == "REMOVED" and i.runner_name not in removals.keys():
                removals[i.runner_name] = i.Index

        return removals

    def create_price_change_dataset_nrs(self, df: pd.DataFrame) -> pd.DataFrame:
        self.pipeline_status.add_info(
            "Creating dataset of price changes with non runners"
        )
        removals = BetfairDataProcessor.get_removals(df)
        split_dfs = BetfairDataProcessor.split_dataframe_by_removals(df)
        changes = []
        for df in split_dfs:
            df = BetfairDataProcessor.create_percentage_moves(df)
            changes.append(df.drop_duplicates(subset=["runner_id"], keep="last"))
        changes = pd.concat(changes)
        changes = changes[~changes.runner_name.isin(removals.keys())]
        changes["price_change"] = changes.groupby(["runner_name"])[
            "price_change"
        ].transform("sum")
        price_changes = []
        for horse in changes.runner_name.unique():
            horse_df = changes[changes.runner_name == horse]
            price_changes.append(
                {
                    "horse": horse_df["runner_name"].iloc[0],
                    "course": horse_df["course"].iloc[0],
                    "race_time": horse_df["race_time"].iloc[0],
                    "race_type": horse_df["race_type"].iloc[0],
                    "runner_id": horse_df["runner_id"].iloc[0],
                    "race_key": horse_df["race_key"].iloc[0],
                    "bf_unique_id": horse_df["bf_unique_id"].iloc[0],
                    "min_price": np.nan,
                    "max_price": np.nan,
                    "latest_price": np.nan,
                    "earliest_price": np.nan,
                    "price_change": horse_df["price_change"].iloc[0],
                    "non_runners": True,
                }
            )
        return pd.DataFrame(price_changes)

    @staticmethod
    def split_dataframe_by_removals(df: pd.DataFrame) -> list[pd.DataFrame]:
        market_changes = {
            i.market_change_time for i in df.itertuples() if i.removal_update
        }
        df = df[~df["market_change_time"].isin(market_changes)]
        sublists = [[df.index[0]]]
        for i in range(1, len(df.index)):
            if df.index[i] - df.index[i - 1] == 1:
                sublists[-1].append(df.index[i])
            else:
                sublists.append([df.index[i]])
        return [df.loc[i[0] : i[-1]] for i in sublists]

    @staticmethod
    def decode_betfair_json_data(content: list[str]) -> list[dict]:
        tmp_buffer = StringIO()
        json.dump(content, tmp_buffer)
        tmp_buffer.seek(0)
        data = json.load(tmp_buffer)
        return [json.loads(i) for i in data]

    @staticmethod
    def open_compressed_file(file: str) -> list[dict]:
        with bz2.open(
            file,
            "rt",
        ) as f:
            content = f.read()
            content = content.strip().split("\n")
        return BetfairDataProcessor.decode_betfair_json_data(content)

    @staticmethod
    def get_last_day_in_month():
        today = date.today()
        _, last_day = monthrange(today.year, today.month)
        last_day = date(today.year, today.month, last_day)
        day = last_day.day
        month = last_day.month
        year = last_day.year
        return day, month, year


class HistoricalBetfairDataService:
    SCHEMA = "bf_raw"

    def __init__(
        self,
        config,
        betfair_client: BetFairClient,
        betfair_data_processor: BetfairDataProcessor,
        storage_client: IStorageClient,
        betfair_cache: BetfairCache,
        pipeline_status: PipelineStatus,
    ):
        self.config = config
        self.betfair_client = betfair_client
        self.betfair_data_processor = betfair_data_processor
        self.storage_client = storage_client
        self.betfair_cache = betfair_cache
        self.pipeline_status = pipeline_status

    def run_data_ingestion(self) -> Optional[pd.DataFrame]:
        params: BetfairHistoricalDataParams = self._get_params(
            self.betfair_cache.max_processed_date
        )
        try:
            file_list = self.betfair_client.get_files(params)
        except Exception as e:
            self.pipeline_status.add_error(f"Error fetching file list: {e}")
            self.pipeline_status.save_to_database()
            raise e
        file_list_set = set(file_list)
        unprocessed_files = list(file_list_set - self.betfair_cache.cached_files)

        if not unprocessed_files:
            self.pipeline_status.add_info("No unprocessed files found, exiting!")
            return None

        abandoned_data = []
        market_data = []
        for index, file_name in enumerate(unprocessed_files):
            self.pipeline_status.add_info(
                f"Processing file {index + 1} of {len(unprocessed_files)} for {params.from_year}"
            )
            try:
                raw_data = self.betfair_client.fetch_historical_data(file_name)
                data = self.betfair_data_processor.open_compressed_file(raw_data)
                if self.betfair_data_processor.check_abandoned(data):
                    self.pipeline_status.add_info(f"Abandoned market {file_name}")
                    self.betfair_cache.store_error_data(
                        pd.DataFrame({"filename": abandoned_data})
                    )
                    abandoned_data.append(file_name)
                    self._remove_file(file_name)
                    continue
                processed_data = self.betfair_data_processor.process_data(
                    data, file_name
                )
                self.pipeline_status.add_info(f"Processed: {len(processed_data)} rows")
                market_data.append(processed_data)
                self._remove_file(file_name)
            except Exception as e:
                self.pipeline_status.add_error(
                    f"Error processing file {file_name}: {e}"
                )
                self.pipeline_status.add_error(
                    f"Error processing file {file_name}: {e}"
                )
                continue

        if abandoned_data:
            self.betfair_cache.store_error_data(
                pd.DataFrame({"filename": abandoned_data})
            )
        if not market_data:
            self.pipeline_status.add_info("No market data to process, exiting!")
            return None

        market_data = pd.concat(market_data)
        market_data = market_data.assign(
            created_at=pd.Timestamp.now(tz="Europe/London"),
            price_change=market_data["price_change"].round(2),
        )
        cached_data = market_data.drop_duplicates(subset=["filename"])
        cached_data = cached_data.assign(
            filename_date_str=cached_data["filename"]
            .str.split("/")
            .str[4]
            .astype(int)
            .astype(str)
            + "-"
            + cached_data["filename"]
            .str.split("/")
            .str[5]
            .apply(lambda x: str(datetime.strptime(x, "%b").month))
            + "-"
            + cached_data["filename"].str.split("/").str[6].astype(int).astype(str)
        )
        cached_data = cached_data.assign(
            filename_date=pd.to_datetime(
                cached_data["filename_date_str"], format="%Y-%m-%d"
            )
        )
        market_data = market_data.rename(
            columns={
                "horse": "horse_name",
                "course": "course_name",
                "bf_unique_id": "unique_id",
            }
        )
        market_data = market_data[
            [
                "horse_name",
                "course_name",
                "race_time",
                "race_date",
                "race_type",
                "min_price",
                "max_price",
                "latest_price",
                "earliest_price",
                "price_change",
                "non_runners",
                "unique_id",
                "created_at",
            ]
        ]
        self.storage_client.store_data(
            market_data,
            "raw_data",
            self.SCHEMA,
        )
        self.betfair_cache.store_data(cached_data[["filename", "filename_date"]])
        self.pipeline_status.save_to_database()

    def _get_params(
        self, last_processed_date: pd.Timestamp
    ) -> BetfairHistoricalDataParams:
        constants = {
            "market_types_collection": ["WIN"],
            "countries_collection": ["GB", "IE"],
            "file_type_collection": ["M"],
        }
        calculated_params = self._calculate_date_params()

        return BetfairHistoricalDataParams(
            **calculated_params,
            **constants,
        )

    def _extract_date_from_filename(self, filename: str) -> str:
        parts = filename.split("/")
        year = int(parts[4])
        month = datetime.strptime(parts[5], "%b").month
        day = int(parts[6])

        return f"{year}-{month}-{day}"

    def _calculate_date_params(self) -> dict[str, int]:
        now = pd.Timestamp.now()
        current_month = now.replace(day=1)
        prev_month = current_month - pd.DateOffset(months=1)

        # Determine if we're in the first 3 days of the month
        early_month_period = now.day <= 5

        if early_month_period:
            # For days 1-3, end date is the last day of previous month
            _, last_day_prev = monthrange(prev_month.year, prev_month.month)
            end_month = prev_month.month
            end_year = prev_month.year
            end_day = last_day_prev
        else:
            # For day 4 onwards, end date is the last day of current month
            _, last_day_current = monthrange(now.year, now.month)
            end_month = now.month
            end_year = now.year
            end_day = last_day_current

        return {
            "from_day": 1,
            "from_month": prev_month.month,
            "from_year": prev_month.year,
            "to_day": end_day,
            "to_month": end_month,
            "to_year": end_year,
        }

    def _remove_file(self, file: str):
        try:
            os.remove(file.split("/")[-1])
        except FileNotFoundError as e:
            self.pipeline_status.add_error(f"File not found: {e}")


if __name__ == "__main__":
    betfair_cache = BetfairCache()
    config = Config()
    betfair_client = get_betfair_client()
    betfair_data_processor = BetfairDataProcessor(config)
    postgres_client = get_postgres_client()
    service = HistoricalBetfairDataService(
        config, betfair_client, betfair_data_processor, postgres_client, betfair_cache
    )
    service.run_data_ingestion()


def create_unique_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.assign(
        bf_race_key=df["course"] + df["race_time"].astype(str).str[:-6],
        bf_race_horse_key=(
            df["course"] + df["race_time"].astype(str).str[:-6] + df["runner_name"]
        ),
    )
    df = df.assign(
        race_key=df["bf_race_key"].apply(
            lambda x: hashlib.sha512(x.encode("utf-8")).hexdigest()
        ),
        bf_unique_id=df["bf_race_horse_key"].apply(
            lambda x: hashlib.sha512(x.encode("utf-8")).hexdigest()
        ),
    ).drop(columns=["bf_race_key", "bf_race_horse_key"])
    return df
