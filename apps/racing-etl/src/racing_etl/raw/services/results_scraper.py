import random
import time
from typing import Any, Hashable

import pandas as pd
from api_helpers.interfaces.storage_client_interface import IStorageClient
from selenium.webdriver.common.by import By

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper
from ...raw.interfaces.webriver_interface import IWebDriver


class ResultsDataScraperService:
    def __init__(
        self,
        scraper: IDataScraper,
        storage_client: IStorageClient,
        driver: IWebDriver,
        schema: str,
        table_name: str,
        view_name: str,
        upsert_procedure: str,
        pipeline_status: PipelineStatus,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.view_name = view_name
        self.upsert_procedure = upsert_procedure
        self.pipeline_status = pipeline_status
        self.source = None

    def _get_missing_links(self) -> list[dict[Hashable, Any]]:
        links: pd.DataFrame = self.storage_client.fetch_data(
            f"SELECT link_url FROM {self.schema}.{self.view_name}"
        )

        return links.to_dict(orient="records")

    def process_links(self, links: list[dict[Hashable, Any]]) -> pd.DataFrame:
        dataframes_list = []

        dummy_movement = True
        self.source = (
            "Racing Post" if "racingpost.com" in links[0]["link_url"] else "Timeform"
        )

        for index, link in enumerate(links):
            self.pipeline_status.add_debug(f"Processing link {index} of {len(links)}")
            try:
                self.pipeline_status.add_debug(f"Scraping link: {link['link_url']}")
                try:
                    button = self.driver.find_element(By.ID, "truste-consent-required")
                    button.click()
                except Exception as e:
                    self.pipeline_status.add_debug(
                        f"Consent button not found or click failed: {str(e)}"
                    )
                if dummy_movement and self.source == "Racing Post":
                    self.pipeline_status.add_debug(
                        "Dummy movement enabled. Navigating to Racing Post homepage and back to the link."
                    )
                    self.driver.get(link["link_url"])
                    time.sleep(5)
                    self.driver.get("https://www.racingpost.com/")
                    time.sleep(5)
                    self.driver.get(link["link_url"])
                    dummy_movement = False
                else:
                    random_num = random.randint(1, 20)
                    self.pipeline_status.add_debug(
                        "Dummy movement disabled. Navigating directly to the link."
                    )
                    if random_num == 5:
                        self.pipeline_status.add_debug(
                            "Randomly selected to perform dummy movement. Navigating to Racing Post homepage and back to the link."
                        )
                        self.driver.get("https://www.racingpost.com/")
                        time.sleep(5)
                    self.driver.get(link["link_url"])

                data = self.scraper.scrape_data(self.driver, link["link_url"])
                self.pipeline_status.add_debug(f"Scraped {len(data)} rows")
                dataframes_list.append(data)
            except Exception as e:
                self.pipeline_status.add_error(
                    f"Error scraping link {link['link_url']}: {str(e)}"
                )
                continue

        if not dataframes_list:
            self.pipeline_status.add_warning("No data scraped. Ending the script.")
            return pd.DataFrame()

        combined_data = pd.concat(dataframes_list)

        self.pipeline_status.add_info(
            f"Total rows scraped for {self.source}: {len(combined_data)}"
        )

        return combined_data

    def _stores_results_data(self, data: pd.DataFrame) -> None:
        try:
            self.storage_client.upsert_data(
                data=data,
                schema=self.schema,
                table_name=self.table_name,
                unique_columns=["unique_id"],
                use_base_table=True,
                upsert_procedure=self.upsert_procedure,
            )
        except Exception as e:
            self.pipeline_status.add_error(
                f"Error upserting data to {self.schema}.{self.table_name}: {str(e)}"
            )
            return

    def run_results_scraper(self):
        links = self._get_missing_links()
        if not links:
            return
        data = self.process_links(links)
        if data.empty:
            return
        self._stores_results_data(data)
        self.pipeline_status.save_to_database()
