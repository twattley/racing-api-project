from datetime import datetime

import pandas as pd
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
        pipeline_status: PipelineStatus,
        view_name: str,
        login: bool = False,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.pipeline_status = pipeline_status
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
                self.pipeline_status.add_debug(f"Scraping link: {link['link_url']}")
                driver.get(link["link_url"])
                data = self.scraper.scrape_data(driver, link["link_url"])
                self.pipeline_status.add_debug(f"Scraped {len(data)} rows")
                dataframes_list.append(data)
            except Exception as e:
                self.pipeline_status.add_error(
                    f"Error scraping link {link['link_url']}: {str(e)}"
                )
                continue

        if not dataframes_list:
            self.pipeline_status.add_warning("No data scraped. Ending the script.")
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
            self.pipeline_status.add_info(
                f"Already processed today's {source_map[self.schema]} racecard data"
            )
            return
        links = self._get_missing_links()
        if not links:
            self.pipeline_status.add_info("No links to scrape. Ending the script.")
            return
        data = self.process_links(links)
        self._stores_results_data(data)
        self.pipeline_status.save_to_database()
