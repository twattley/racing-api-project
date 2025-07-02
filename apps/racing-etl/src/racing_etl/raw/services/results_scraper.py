import random
import time
from typing import Any, Hashable

import pandas as pd
from api_helpers.helpers.logging_config import E, I
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...raw.interfaces.data_scraper_interface import IDataScraper
from ...raw.interfaces.webriver_interface import IWebDriver

from ...data_types.log_object import LogObject


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
        log_object: LogObject,
        login: bool = False,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.view_name = view_name
        self.upsert_procedure = upsert_procedure
        self.log_object = log_object
        self.login = login

    def _get_missing_links(self) -> list[dict[Hashable, Any]]:
        links: pd.DataFrame = self.storage_client.fetch_data(
            f"SELECT link_url FROM {self.schema}.{self.view_name}"
        )

        return links.to_dict(orient="records")

    def process_links(self, links: list[dict[Hashable, Any]]) -> pd.DataFrame:
        driver = self.driver.create_session(self.login)
        dataframes_list = []

        dummy_movement = True
        rp_processor = True if "racingpost.com" in links[0]["link_url"] else False



        for index, link in enumerate(links):
            I(f"Processing link {index} of {len(links)}")
            try:
                I(f"Scraping link: {link['link_url']}")
                if dummy_movement and rp_processor:
                    I(
                        "Dummy movement enabled. Navigating to Racing Post homepage and back to the link."
                    )
                    driver.get(link["link_url"])
                    time.sleep(5)
                    driver.get("https://www.racingpost.com/")
                    time.sleep(5)
                    driver.get(link["link_url"])
                    dummy_movement = False
                else:
                    random_num = random.randint(1, 20)
                    I("Dummy movement disabled. Navigating directly to the link.")
                    if random_num == 5:
                        I(
                            "Randomly selected to perform dummy movement. Navigating to Racing Post homepage and back to the link."
                        )
                        driver.get("https://www.racingpost.com/")
                        time.sleep(5)
                    driver.get(link["link_url"])

                data = self.scraper.scrape_data(driver, link["link_url"])
                I(f"Scraped {len(data)} rows")
                dataframes_list.append(data)
            except Exception as e:
                E(
                    f"Encountered an error: {e}. Attempting to continue with the next link."
                )
                self.log_object.add_error(
                    f"Error scraping link {link['link_url']}: {str(e)}"
                )
                continue

        if not dataframes_list:
            I("No data scraped. Ending the script.")
            return pd.DataFrame()

        combined_data = pd.concat(dataframes_list)

        return combined_data

    def _stores_results_data(self, data: pd.DataFrame) -> None:
        self.storage_client.upsert_data(
            data=data,
            schema=self.schema,
            table_name=self.table_name,
            unique_columns=["unique_id"],
            use_base_table=True,
            upsert_procedure=self.upsert_procedure,
        )

    def run_results_scraper(self):
        links = self._get_missing_links()
        if not links:
            I("No links to scrape. Ending the script.")
            return
        data = self.process_links(links)
        if data.empty:
            I("No data processed. Ending the script.")
            return
        self._stores_results_data(data)
        self.log_object.save_to_database()
