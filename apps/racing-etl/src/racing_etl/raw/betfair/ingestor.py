from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import (
    IngestBFResultsData,
    IngestBFTodaysData,
    check_pipeline_completion,
)
from ...raw.betfair.betfair_cache import BetfairCache
from ...raw.betfair.fetch_historical_data import (
    BetfairDataProcessor,
    HistoricalBetfairDataService,
)
from ...raw.betfair.fetch_todays_data import TodaysBetfairDataService


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

    @check_pipeline_completion(IngestBFTodaysData)
    def ingest_todays_data(self, pipeline_status):
        service = TodaysBetfairDataService(
            config=self.config,
            betfair_client=self.betfair_client,
            storage_client=self.storage_client,
            pipeline_status=pipeline_status,
        )
        service.run_data_ingestion()

    @check_pipeline_completion(IngestBFResultsData)
    def ingest_results_data(self, pipeline_status):
        betfair_cache = BetfairCache(pipeline_status)
        betfair_data_processor = BetfairDataProcessor(self.config, pipeline_status)
        service = HistoricalBetfairDataService(
            config=self.config,
            betfair_client=self.betfair_client,
            storage_client=self.storage_client,
            betfair_cache=betfair_cache,
            betfair_data_processor=betfair_data_processor,
            pipeline_status=pipeline_status,
        )
        service.run_data_ingestion()
