from datetime import datetime

import pandas as pd
from api_helpers.interfaces.storage_client_interface import IStorageClient
from playwright.sync_api import Page

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.link_scraper_interface import ILinkScraper


class RacecardsLinksScraperService:
    TODAY = datetime.now().strftime("%Y-%m-%d")

    def __init__(
        self,
        scraper: ILinkScraper,
        storage_client: IStorageClient,
        page: Page,
        schema: str,
        table_name: str,
        pipeline_status: PipelineStatus,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.page = page
        self.schema = schema
        self.table_name = table_name
        self.pipeline_status = pipeline_status

    def process_date(self) -> pd.DataFrame:
        try:
            data: pd.DataFrame = self.scraper.scrape_links(self.page, self.TODAY)
            self.pipeline_status.add_info(f"Scraped {len(data)} links for {self.TODAY}")
            return data
        except Exception as e:
            self.pipeline_status.add_error(f"Error scraping links: {str(e)}")
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
        self.pipeline_status.save_to_database()
