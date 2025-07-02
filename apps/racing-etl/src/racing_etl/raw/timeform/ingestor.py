from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...raw.helpers.course_ref_data import CourseRefData
from ...raw.services.racecard_links_scraper import RacecardsLinksScraperService
from ...raw.services.racecard_scraper import RacecardsDataScraperService
from ...raw.services.result_links_scraper import ResultLinksScraperService
from ...raw.services.results_scraper import ResultsDataScraperService
from ...raw.timeform.generate_query import RawSQLGenerator
from ...raw.timeform.results_data_scraper import TFResultsDataScraper
from ...raw.timeform.results_link_scraper import TFResultsLinkScraper
from ...raw.timeform.todays_racecard_data_scraper import TFRacecardsDataScraper
from ...raw.timeform.todays_racecard_links_scraper import TFRacecardsLinkScraper
from ...raw.webdriver.web_driver import WebDriver
from ...data_types.log_object import LogObject


class TFIngestor:
    SOURCE = "tf"
    SCHEMA = f"{SOURCE}_raw"
    PIPELINE_STAGE = "ingestion"

    def __init__(
        self,
        config: Config,
        storage_client: IStorageClient,
    ):
        self.config = config
        self.storage_client = storage_client

    def ingest_todays_links(self):
        job_name = 'tf_todays_links'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            return
        service = RacecardsLinksScraperService(
            scraper=TFRacecardsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                )
            ),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            table_name=self.config.db.raw.todays_data.links_table,
            log_object=LogObject(
                job_name="timeform",
                pipeline_stage="ingest_todays_links",
                storage_client=self.storage_client,
            ),
        )
        service.run_racecard_links_scraper()

    def ingest_todays_data(self):
        job_name = 'tf_todays_data'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            return
        service = RacecardsDataScraperService(
            scraper=TFRacecardsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.todays_data.links_view,
            table_name=self.config.db.raw.todays_data.data_table,
            login=True,
            log_object=LogObject(
                job_name="timeform",
                pipeline_stage="ingest_todays_data",
                storage_client=self.storage_client,
            ),
        )
        service.run_racecards_scraper()

    def ingest_results_links(self):
        job_name = 'tf_results_links'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            return
        service = ResultLinksScraperService(
            scraper=TFResultsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                )
            ),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.links_view,
            table_name=self.config.db.raw.results_data.links_table,
            log_object=LogObject(
                job_name="timeform",
                pipeline_stage="ingest_results_links",
                storage_client=self.storage_client,
            ),
        )
        service.run_results_links_scraper()

    def ingest_results_data(self):
        job_name = 'tf_results_data'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            return
        service = ResultsDataScraperService(
            scraper=TFResultsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.data_view,
            table_name=self.config.db.raw.results_data.data_table,
            upsert_procedure=RawSQLGenerator.get_results_data_upsert_sql(),
            login=True,
            log_object=LogObject(
                job_name="timeform",
                pipeline_stage="ingest_results_data",
                storage_client=self.storage_client,
            ),
        )
        service.run_results_scraper()

    def ingest_results_data_world(self):
        job_name = 'tf_results_data_world'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            return
        service = ResultsDataScraperService(
            scraper=TFResultsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            table_name=self.config.db.raw.results_data.data_world_table,
            view_name=self.config.db.raw.results_data.data_world_view,
            upsert_procedure=RawSQLGenerator.get_results_data_world_upsert_sql(),
            login=True,
            log_object=LogObject(
                job_name="timeform",
                pipeline_stage="ingest_results_data_world",
                storage_client=self.storage_client,
            ),
        )
        service.run_results_scraper()
