from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...raw.betfair.betfair_cache import BetfairCache
from ...raw.betfair.fetch_historical_data import (
    BetfairDataProcessor,
    HistoricalBetfairDataService,
)
from ...raw.betfair.fetch_todays_data import TodaysBetfairDataService
from ...data_types.log_object import LogObject


class BFIngestor:
    def __init__(
        self,
        config: Config,
        betfair_client: BetFairClient,
        storage_client: IStorageClient,
    ):
        self.config = config
        self.betfair_client = betfair_client
        self.storage_client = storage_client

    def ingest_todays_data(self):
        service = TodaysBetfairDataService(
            config=self.config,
            betfair_client=self.betfair_client,
            storage_client=self.storage_client,
            log_object=LogObject(
                job_name="betfair",
                pipeline_stage="ingest_todays_data",
                storage_client=self.storage_client,
            ),
        )
        service.run_data_ingestion()

    def ingest_historical_data(self):
        betfair_cache = BetfairCache()
        betfair_data_processor = BetfairDataProcessor(self.config)
        service = HistoricalBetfairDataService(
            config=self.config,
            betfair_client=self.betfair_client,
            storage_client=self.storage_client,
            betfair_cache=betfair_cache,
            betfair_data_processor=betfair_data_processor,
            log_object=LogObject(
                job_name="betfair",
                pipeline_stage="ingest_historical_data",
                storage_client=self.storage_client,
            ),
        )
        service.run_data_ingestion()
