from datetime import datetime

import pandas as pd
from api_helpers.helpers.logging_config import E, I
from api_helpers.interfaces.storage_client_interface import IStorageClient

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
        view_name: str,
        login: bool = False,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.view_name = view_name
        self.login = login

    TODAY = datetime.now().strftime("%Y-%m-%d")

    def _get_missing_links(self) -> list[str]:
        links: pd.DataFrame = self.storage_client.fetch_data(
            f"SELECT link_url FROM {self.schema}.{self.view_name}"
        )
        # links = pd.DataFrame(
        #     {
        #         "link_url": [
        #             "https://www.racingpost.com/racecards/38/newmarket/2025-05-18/892819",
        #         ]
        #     }
        # )
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


if __name__ == "__main__":
    from api_helpers.clients import get_postgres_client
    from api_helpers.interfaces.storage_client_interface import IStorageClient

    from ...config import Config
    from ...raw.racing_post.todays_racecard_data_scraper import RPRacecardsDataScraper
    from ...raw.services.racecard_scraper import RacecardsDataScraperService
    from ...raw.webdriver.web_driver import WebDriver

    storage_client = get_postgres_client()
    config = Config()
    driver = WebDriver(config)
    service = RacecardsDataScraperService(
        scraper=RPRacecardsDataScraper(),
        storage_client=storage_client,
        driver=WebDriver(config, headless_mode=False),
        schema="rp_raw",
        view_name=config.db.raw.todays_data.links_table,
        table_name=config.db.raw.todays_data.data_table,
    )
    service.run_racecards_scraper()
