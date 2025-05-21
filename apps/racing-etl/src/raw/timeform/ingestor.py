from api_helpers.interfaces.storage_client_interface import IStorageClient

from src.config import Config
from src.raw.services.racecard_links_scraper import RacecardsLinksScraperService
from src.raw.services.racecard_scraper import RacecardsDataScraperService
from src.raw.services.result_links_scraper import ResultLinksScraperService
from src.raw.services.results_scraper import ResultsDataScraperService
from src.raw.timeform.results_data_scraper import TFResultsDataScraper
from src.raw.timeform.results_link_scraper import TFResultsLinkScraper
from src.raw.timeform.todays_racecard_data_scraper import TFRacecardsDataScraper
from src.raw.timeform.todays_racecard_links_scraper import TFRacecardsLinkScraper
from src.raw.webdriver.web_driver import WebDriver
from src.raw.helpers.course_ref_data import CourseRefData
from src.raw.timeform.generate_query import RawSQLGenerator
from src.storage.storage_client import get_storage_client


class TFIngestor:
    SOURCE = "tf"
    SCHEMA = f"{SOURCE}_raw"

    def __init__(
        self,
        config: Config,
        storage_client: IStorageClient,
    ):
        self.config = config
        self.storage_client = storage_client

    def ingest_todays_links(self):
        service = RacecardsLinksScraperService(
            scraper=TFRacecardsLinkScraper(
                ref_data=CourseRefData(
                    source=self.SOURCE, storage_client=self.storage_client
                )
            ),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.todays_data.links_view,
            table_name=self.config.db.raw.todays_data.links_table,
        )
        service.run_racecard_links_scraper()

    def ingest_todays_data(self):
        service = RacecardsDataScraperService(
            scraper=TFRacecardsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.todays_data.links_table,
            table_name=self.config.db.raw.todays_data.data_table,
            login=True,
        )
        service.run_racecards_scraper()

    def ingest_results_links(self):
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
        )
        service.run_results_links_scraper()

    def ingest_results_data(self):
        service = ResultsDataScraperService(
            scraper=TFResultsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            view_name=self.config.db.raw.results_data.data_view,
            table_name=self.config.db.raw.results_data.data_table,
            upsert_procedure=RawSQLGenerator.get_results_data_upsert_sql(),
            login=True,
        )
        service.run_results_scraper()

    def ingest_results_data_world(self):
        service = ResultsDataScraperService(
            scraper=TFResultsDataScraper(),
            storage_client=self.storage_client,
            driver=WebDriver(self.config),
            schema=self.SCHEMA,
            table_name=self.config.db.raw.results_data.data_world_table,
            view_name=self.config.db.raw.results_data.data_world_view,
            upsert_procedure=RawSQLGenerator.get_results_data_world_upsert_sql(),
            login=True,
        )
        service.run_results_scraper()


if __name__ == "__main__":
    storage_client = get_storage_client("postgres")
    ingestor = TFIngestor(
        config=Config(),
        storage_client=storage_client,
    )
    ingestor.ingest_results_data()
