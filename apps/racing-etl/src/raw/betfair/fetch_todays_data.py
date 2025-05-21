import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient, BetfairCredentials
from api_helpers.helpers.logging_config import I
from api_helpers.interfaces.storage_client_interface import IStorageClient

from src.config import Config
from src.storage.storage_client import get_storage_client


class TodaysBetfairDataService:
    def __init__(
        self,
        config: Config,
        betfair_client: BetFairClient,
        storage_client: IStorageClient,
    ):
        self.config = config
        self.betfair_client = betfair_client
        self.storage_client = storage_client

    SCHEMA = "bf_raw"

    def run_data_ingestion(self):
        I("Fetching todays market data")
        data = self.betfair_client.create_market_data()
        data = data.assign(
            created_at=pd.Timestamp.now(),
            race_date=data["race_time"].dt.date,
        )
        I(f"Found {data.shape[0]} markets")
        win_and_place = (
            pd.merge(
                data[data["market"] == "WIN"],
                data[data["market"] == "PLACE"],
                on=["race_time", "course", "todays_betfair_selection_id"],
                suffixes=("_win", "_place"),
            )
            .rename(
                columns={
                    "horse_win": "horse_name",
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
            .sort_values(by="race_time", ascending=True)
        )
        self.storage_client.store_data(
            data=win_and_place,
            schema=self.SCHEMA,
            table=self.config.db.raw.todays_data.data_table,
            truncate=True,
        )


if __name__ == "__main__":
    config = Config()
    betfair_client = BetFairClient(
        BetfairCredentials(
            username=config.bf_username,
            password=config.bf_password,
            app_key=config.bf_app_key,
            certs_path=config.bf_certs_path,
        )
    )
    postgres_client = get_storage_client("postgres")
    service = TodaysBetfairDataService(config, betfair_client, postgres_client)
    service.run_data_ingestion()
