from datetime import datetime

from api_helpers.config import Config
from api_helpers.helpers.logging_config import I
from api_helpers.interfaces.storage_client_interface import IStorageClient

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
from ...raw.webdriver.web_driver import WebDriver
from ...data_types.log_object import LogObject


class RPIngestor:
    SOURCE = "rp"
    SCHEMA = f"{SOURCE}_raw"
    PIPELINE_STAGE = "ingest"

    def __init__(
        self, config: Config, storage_client: IStorageClient, chat_model: ChatModels
    ):
        self.config = config
        self.storage_client = storage_client
        self.chat_model = chat_model

    def ingest_todays_links(self):
        job_name = 'rp_todays_links'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        service = RacecardsLinksScraperService(
            scraper=RPRacecardsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                )
            ),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            table_name=self.config.db.raw.todays_data.links_table,
            log_object=LogObject(
                job_name=job_name,
                pipeline_stage=self.PIPELINE_STAGE,
                storage_client=self.storage_client,
            ),
        )
        service.run_racecard_links_scraper()

    def ingest_todays_data(self):
        job_name = 'rp_todays_data'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        service = RacecardsDataScraperService(
            scraper=RPRacecardsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.todays_data.links_view,
            table_name=self.config.db.raw.todays_data.data_table,
            log_object=LogObject(
                job_name=job_name,
                pipeline_stage=self.PIPELINE_STAGE,
                storage_client=self.storage_client,
            ),
        )
        service.run_racecards_scraper()

    def ingest_results_links(self):
        job_name = 'rp_results_links'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        service = ResultLinksScraperService(
            scraper=RPResultsLinkScraper(
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
                job_name=job_name,
                pipeline_stage=self.PIPELINE_STAGE,
                storage_client=self.storage_client,
            ),
        )
        service.run_results_links_scraper()

    def ingest_results_data(self):
        job_name = 'rp_results_data'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        service = ResultsDataScraperService(
            scraper=RPResultsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.data_view,
            table_name=self.config.db.raw.results_data.data_table,
            upsert_procedure=RawSQLGenerator.get_results_data_upsert_sql(),
            log_object=LogObject(
                job_name=job_name,
                pipeline_stage=self.PIPELINE_STAGE,
                storage_client=self.storage_client,
            ),
        )
        service.run_results_scraper()

    def ingest_results_data_world(self):
        job_name = 'rp_results_data_world'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        service = ResultsDataScraperService(
            scraper=RPResultsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            table_name=self.config.db.raw.results_data.data_world_table,
            view_name=self.config.db.raw.results_data.data_world_view,
            upsert_procedure=RawSQLGenerator.get_results_data_world_upsert_sql(),
            log_object=LogObject(
                job_name=job_name,
                pipeline_stage=self.PIPELINE_STAGE,
                storage_client=self.storage_client,
            ),
        )
        service.run_results_scraper()

    def ingest_results_comments(self):
        job_name = 'rp_results_comments'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        scraper = RPCommentDataScraper(
            chat_model=self.chat_model,
            storage_client=self.storage_client,
            table_name="results_data",
            log_object=LogObject(
                job_name=job_name,
                pipeline_stage=self.PIPELINE_STAGE,
                storage_client=self.storage_client,
            ),
        )
        scraper.scrape_data()

    def ingest_results_comments_world(self):
        job_name = 'rp_results_comments_world'

        stage_completed = self.storage_client.check_pipeline_completion(
            job_name=job_name,
            pipeline_stage=self.PIPELINE_STAGE,
        )
        if stage_completed:
            I(f"Stage {self.PIPELINE_STAGE} for job {job_name} already completed. Skipping.")
            return
        day_of_week = datetime.now().day
        if day_of_week == 0:
            scraper = RPCommentDataScraper(
                chat_model=self.chat_model,
                storage_client=self.storage_client,
                table_name="results_data_world",
                log_object=LogObject(
                    job_name=job_name,
                    pipeline_stage=self.PIPELINE_STAGE,
                    storage_client=self.storage_client,
                ),
            )
            scraper.scrape_data()
        else:
            I("Not Monday. Skipping the ingestion of results comments for world data.")
