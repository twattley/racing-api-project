from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient
from racing_etl.raw.interfaces.webriver_interface import IWebDriver

from ...data_types.pipeline_status import (
    IngestRPComments,
    IngestRPCommentsWorld,
    IngestRPResultsData,
    IngestRPResultsDataWorld,
    IngestRPResultsLinks,
    IngestRPTodaysData,
    IngestRPTodaysLinks,
    check_pipeline_completion,
)
from ...llm_models.chat_models import ChatModels
from ...raw.helpers.course_ref_data import CourseRefData
from ...raw.racing_post.generate_query import RawSQLGenerator
from ...raw.racing_post.results_comments_scraper import RPCommentDataScraper
from ...raw.racing_post.results_data_scraper import RPResultsDataScraper
from ...raw.racing_post.results_link_scraper import RPResultsLinkScraper
from ...raw.racing_post.todays_racecard_data_scraper import RPRacecardsDataScraper
from ...raw.racing_post.todays_racecard_links_scraper import RPRacecardsLinkScraper
from ...raw.services.racecard_links_scraper import RacecardsLinksScraperService
from ...raw.services.racecard_scraper import RacecardsDataScraperService
from ...raw.services.result_links_scraper import ResultLinksScraperService
from ...raw.services.results_scraper import ResultsDataScraperService


class RPIngestor:
    SOURCE = "rp"
    SCHEMA = f"{SOURCE}_raw"

    def __init__(
        self,
        config: Config,
        storage_client: IStorageClient,
        chat_model: ChatModels,
        driver: IWebDriver,
    ):
        self.config = config
        self.storage_client = storage_client
        self.chat_model = chat_model
        self.driver = driver.create_session()

    @check_pipeline_completion(IngestRPTodaysLinks)
    def ingest_todays_links(self, pipeline_status):
        service = RacecardsLinksScraperService(
            scraper=RPRacecardsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                ),
                pipeline_status=pipeline_status,
            ),
            storage_client=self.storage_client,
            driver=self.driver,
            schema=self.SCHEMA,
            table_name=self.config.db.raw.todays_data.links_table,
            pipeline_status=pipeline_status,
        )
        service.run_racecard_links_scraper()

    @check_pipeline_completion(IngestRPTodaysData)
    def ingest_todays_data(self, pipeline_status):

        service = RacecardsDataScraperService(
            scraper=RPRacecardsDataScraper(pipeline_status=pipeline_status),
            storage_client=self.storage_client,
            driver=self.driver,
            schema=self.SCHEMA,
            view_name=self.config.db.raw.todays_data.links_view,
            table_name=self.config.db.raw.todays_data.data_table,
            pipeline_status=pipeline_status,
        )
        service.run_racecards_scraper()

    @check_pipeline_completion(IngestRPResultsLinks)
    def ingest_results_links(self, pipeline_status):
        service = ResultLinksScraperService(
            scraper=RPResultsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                ),
                pipeline_status=pipeline_status,
            ),
            storage_client=self.storage_client,
            driver=self.driver,
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.links_view,
            table_name=self.config.db.raw.results_data.links_table,
            pipeline_status=pipeline_status,
        )
        service.run_results_links_scraper()

    @check_pipeline_completion(IngestRPResultsData)
    def ingest_results_data(self, pipeline_status):
        service = ResultsDataScraperService(
            scraper=RPResultsDataScraper(pipeline_status),
            storage_client=self.storage_client,
            driver=self.driver,
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.data_view,
            table_name=self.config.db.raw.results_data.data_table,
            upsert_procedure=RawSQLGenerator.get_results_data_upsert_sql(),
            pipeline_status=pipeline_status,
        )
        service.run_results_scraper()

    @check_pipeline_completion(IngestRPResultsDataWorld)
    def ingest_results_data_world(self, pipeline_status):
        service = ResultsDataScraperService(
            scraper=RPResultsDataScraper(pipeline_status),
            storage_client=self.storage_client,
            driver=self.driver,
            schema=self.SCHEMA,
            table_name=self.config.db.raw.results_data.data_world_table,
            view_name=self.config.db.raw.results_data.data_world_view,
            upsert_procedure=RawSQLGenerator.get_results_data_world_upsert_sql(),
            pipeline_status=pipeline_status,
        )
        service.run_results_scraper()

    @check_pipeline_completion(IngestRPComments)
    def ingest_results_comments(self, pipeline_status):
        scraper = RPCommentDataScraper(
            chat_model=self.chat_model,
            storage_client=self.storage_client,
            table_name="results_data",
            pipeline_status=pipeline_status,
        )
        scraper.scrape_data()

    @check_pipeline_completion(IngestRPCommentsWorld)
    def ingest_results_comments_world(self, pipeline_status):
        # day_of_week = datetime.now().day
        # if day_of_week == 0:
        scraper = RPCommentDataScraper(
            chat_model=self.chat_model,
            storage_client=self.storage_client,
            table_name="results_data_world",
            pipeline_status=pipeline_status,
        )
        scraper.scrape_data()
        # else:
        #     I("Not Monday. Skipping the ingestion of results comments for world data.")
