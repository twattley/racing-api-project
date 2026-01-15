from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import IngestBFTodaysData, check_pipeline_completion
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
