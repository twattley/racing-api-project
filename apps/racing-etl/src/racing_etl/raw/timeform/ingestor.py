from api_helpers.config import Config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import (
    IngestTFResultsData,
    IngestTFResultsDataWorld,
    IngestTFResultsLinks,
    IngestTFTodaysData,
    IngestTFTodaysLinks,
    check_pipeline_completion,
)
from ...raw.browser import PlaywrightBrowser
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


class TFIngestor:
    SOURCE = "tf"
    SCHEMA = f"{SOURCE}_raw"

    def __init__(
        self,
        config: Config,
        storage_client: IStorageClient,
        headless: bool = True,
    ):
        self.config = config
        self.storage_client = storage_client
        self._browser = PlaywrightBrowser(headless=headless)
        self.page = self._browser.create_session(website="timeform")
        self._dismiss_popups()

    def _dismiss_popups(self):
        """Dismiss any promotional popups that may appear."""
        popup_selectors = [
            "text=NO THANKS, CONTINUE BROWSING THE SITE",
            "text=NO THANKS",
            "text=No Thanks",
            "text=CONTINUE BROWSING",
            "button:has-text('×')",
            "[class*='close']",
            "[aria-label='Close']",
        ]

        for selector in popup_selectors:
            try:
                element = self.page.locator(selector).first
                element.wait_for(state="visible", timeout=3000)
                element.click()
                self.page.wait_for_timeout(1000)
                return
            except Exception:
                continue

    @check_pipeline_completion(IngestTFTodaysLinks)
    def ingest_todays_links(self, pipeline_status):
        service = RacecardsLinksScraperService(
            scraper=TFRacecardsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                ),
                pipeline_status=pipeline_status,
            ),
            storage_client=self.storage_client,
            page=self.page,
            schema=self.SCHEMA,
            table_name=self.config.db.raw.todays_data.links_table,
            pipeline_status=pipeline_status,
        )
        service.run_racecard_links_scraper()

    @check_pipeline_completion(IngestTFTodaysData)
    def ingest_todays_data(self, pipeline_status):
        service = RacecardsDataScraperService(
            scraper=TFRacecardsDataScraper(pipeline_status),
            storage_client=self.storage_client,
            page=self.page,
            schema=self.SCHEMA,
            view_name=self.config.db.raw.todays_data.links_view,
            table_name=self.config.db.raw.todays_data.data_table,
            pipeline_status=pipeline_status,
        )
        service.run_racecards_scraper()

    @check_pipeline_completion(IngestTFResultsLinks)
    def ingest_results_links(self, pipeline_status):
        service = ResultLinksScraperService(
            scraper=TFResultsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                ),
                pipeline_status=pipeline_status,
            ),
            storage_client=self.storage_client,
            page=self.page,
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.links_view,
            table_name=self.config.db.raw.results_data.links_table,
            pipeline_status=pipeline_status,
        )
        service.run_results_links_scraper()

    @check_pipeline_completion(IngestTFResultsData)
    def ingest_results_data(self, pipeline_status):
        service = ResultsDataScraperService(
            scraper=TFResultsDataScraper(pipeline_status),
            storage_client=self.storage_client,
            page=self.page,
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.data_view,
            table_name=self.config.db.raw.results_data.data_table,
            upsert_procedure=RawSQLGenerator.get_results_data_upsert_sql(),
            pipeline_status=pipeline_status,
        )
        service.run_results_scraper()

    @check_pipeline_completion(IngestTFResultsDataWorld)
    def ingest_results_data_world(self, pipeline_status):
        service = ResultsDataScraperService(
            scraper=TFResultsDataScraper(pipeline_status),
            storage_client=self.storage_client,
            page=self.page,
            schema=self.SCHEMA,
            table_name=self.config.db.raw.results_data.data_world_table,
            view_name=self.config.db.raw.results_data.data_world_view,
            upsert_procedure=RawSQLGenerator.get_results_data_world_upsert_sql(),
            pipeline_status=pipeline_status,
        )
        service.run_results_scraper()

    def close(self):
        """Close the browser session."""
        self._browser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
