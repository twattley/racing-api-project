from datetime import datetime

import pandas as pd
from api_helpers.helpers.logging_config import E, I
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper
from ...raw.interfaces.webriver_interface import IWebDriver


class RacecardsDataScraperService:
    def __init__(
        self,
        scraper: IDataScraper,
        storage_client: IStorageClient,
        driver: IWebDriver,
        schema: str,
        table_name: str,
        log_object: PipelineStatus,
        view_name: str,
        login: bool = False,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.log_object = log_object
        self.view_name = view_name
        self.login = login

    TODAY = datetime.now().strftime("%Y-%m-%d")

    def _get_missing_links(self) -> list[str]:
        links: pd.DataFrame = self.storage_client.fetch_data(
            f"SELECT link_url FROM {self.schema}.{self.view_name}"
        )
        return links.to_dict(orient="records")

    def process_links(self, links: list[str]) -> pd.DataFrame:
        driver = self.driver.create_session(self.login)
        dataframes_list = []
        for link in links:
            try:
                I(f"Scraping link: {link['link_url']}")
                driver.get(link["link_url"])
                data = self.scraper.scrape_data(driver, link["link_url"])
                I(f"Scraped {len(data)} rows")
                dataframes_list.append(data)
            except Exception as e:
                E(
                    "RACECARDS SCRAPER ERROR:"
                    f"Encountered an error: {e}. Attempting to continue with the next link."
                    f"Link: {link['link_url']}"
                )
                self.log_object.add_error(
                    f"Error scraping link {link['link_url']}: {str(e)}"
                )
                continue

        if not dataframes_list:
            I("No data scraped. Ending the script.")
            return

        combined_data = pd.concat(dataframes_list)

        return combined_data

    def _stores_results_data(self, data: pd.DataFrame) -> None:
        self.storage_client.store_data(
            data=data,
            schema=self.schema,
            table=self.table_name,
            truncate=True,
        )

    def _check_already_processed(self) -> bool:
        return not self.storage_client.fetch_data(
            f"""
            SELECT * 
            FROM {self.schema}.todays_data 
            WHERE race_date = '{self.TODAY}'
            """
        ).empty

    def run_racecards_scraper(self):
        source_map = {
            "rp_raw": "Racing Post",
            "tf_raw": "Timeform",
        }
        if self._check_already_processed():
            I(f"Already processed today's {source_map[self.schema]} racecard data")
            return
        links = self._get_missing_links()
        if not links:
            I("No links to scrape. Ending the script.")
            return
        data = self.process_links(links)
        self._stores_results_data(data)
        self.log_object.save_to_database()
