import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import PipelineStatus

from .fetch_historical_data import create_unique_ids


class TodaysBetfairDataService:
    def __init__(
        self,
        config: Config,
        betfair_client: BetFairClient,
        storage_client: IStorageClient,
        pipeline_status: PipelineStatus,
    ):
        self.config = config
        self.betfair_client = betfair_client
        self.storage_client = storage_client
        self.pipeline_status = pipeline_status

    SCHEMA = "bf_raw"

    def run_data_ingestion(self):
        try:
            self.pipeline_status.add_info("Fetching todays market data")
            try:
                data = self.betfair_client.create_market_data()
            except Exception as e:
                self.pipeline_status.add_error(
                    f"Error fetching todays market data: {e}"
                )
                self.pipeline_status.save_to_database()
                raise e

            data = data.assign(
                created_at=pd.Timestamp.now(),
                race_date=data["race_time"].dt.date,
            )
            self.pipeline_status.add_info(f"Found {data.shape[0]} markets")
            win_and_place = (
                pd.merge(
                    data[data["market"] == "WIN"],
                    data[data["market"] == "PLACE"],
                    on=["race_time", "course", "todays_betfair_selection_id"],
                    suffixes=("_win", "_place"),
                )
                .rename(
                    columns={
                        "horse_win": "runner_name",
                        "todays_betfair_selection_id": "horse_id",
                        "last_traded_price_win": "betfair_win_sp",
                        "last_traded_price_place": "betfair_place_sp",
                        "status_win": "status",
                        "created_at_win": "created_at",
                        "race_date_win": "race_date",
                    }
                )
                .filter(
                    items=[
                        "race_time",
                        "race_date",
                        "horse_id",
                        "runner_name",
                        "course",
                        "betfair_win_sp",
                        "betfair_place_sp",
                        "created_at",
                        "status",
                        "market_id_win",
                        "market_id_place",
                    ]
                )
                .sort_values(by="race_time", ascending=True)
            )

            win_and_place = create_unique_ids(win_and_place)
            win_and_place = win_and_place.rename(
                columns={
                    "runner_name": "horse_name",
                    "bf_unique_id": "unique_id",
                }
            ).filter(
                items=[
                    "unique_id",
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
            self.storage_client.store_data(
                data=win_and_place,
                schema=self.SCHEMA,
                table=self.config.db.raw.todays_data.data_table,
                truncate=True,
            )
            self.pipeline_status.save_to_database()

        except Exception as e:
            self.pipeline_status.add_error(f"Error during todays data ingestion: {e}")
            self.pipeline_status.save_to_database()
