from datetime import datetime

import pandas as pd
from api_helpers.helpers.logging_config import E, I
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.link_scraper_interface import ILinkScraper
from ...raw.interfaces.webriver_interface import IWebDriver


class RacecardsLinksScraperService:
    TODAY = datetime.now().strftime("%Y-%m-%d")

    def __init__(
        self,
        scraper: ILinkScraper,
        storage_client: IStorageClient,
        driver: IWebDriver,
        schema: str,
        table_name: str,
        log_object: PipelineStatus,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.log_object = log_object

    def process_date(self) -> pd.DataFrame:
        try:
            driver = self.driver.create_session()
            data: pd.DataFrame = self.scraper.scrape_links(driver, self.TODAY)
            I(f"Scraped {len(data)} links for {self.TODAY}")
            return data
        except Exception as e:
            self.log_object.add_error(f"Error scraping links: {str(e)}")
            E(f"Error scraping links: {str(e)}")
            raise e

    def _store_racecard_data(self, data: pd.DataFrame) -> None:
        self.storage_client.store_data(
            data=data,
            schema=self.schema,
            table=self.table_name,
            truncate=True,
        )

    def run_racecard_links_scraper(self):
        data = self.process_date()
        self._store_racecard_data(data)
