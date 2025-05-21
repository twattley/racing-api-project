import pandas as pd
from api_helpers.helpers.logging_config import E, I
from api_helpers.interfaces.storage_client_interface import IStorageClient

from src.raw.interfaces.link_scraper_interface import ILinkScraper
from src.raw.interfaces.webriver_interface import IWebDriver


class ResultLinksScraperService:
    def __init__(
        self,
        scraper: ILinkScraper,
        storage_client: IStorageClient,
        driver: IWebDriver,
        schema: str,
        table_name: str,
        view_name: str,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.view_name = view_name

    def _get_missing_dates(self) -> list[dict]:
        dates: pd.DataFrame = self.storage_client.fetch_data(
            f"""
            SELECT race_date FROM 
            {self.schema}.{self.view_name}
            """
        )
        return dates.to_dict(orient="records")

    def process_dates(self, dates: list[str]) -> pd.DataFrame:
        driver = self.driver.create_session()
        I(f"Processing {len(dates)} dates: {dates}")
        dataframes_list = []
        for date in dates:
            try:
                data: pd.DataFrame = self.scraper.scrape_links(
                    driver, date["race_date"].strftime("%Y-%m-%d")
                )
                I(f"Scraped {len(data)} links for {date}")
                dataframes_list.append(data)
            except Exception as e:
                E(
                    f"Encountered an error: {e}. Attempting to continue with the next link."
                )
                continue

        if not dataframes_list:
            I("No data scraped. Ending the script.")
            return

        return pd.concat(dataframes_list)

    def _store_data(self, data: pd.DataFrame) -> None:
        self.storage_client.store_data(
            data=data,
            schema=self.schema,
            table=self.table_name,
        )

    def run_results_links_scraper(self):
        dates = self._get_missing_dates()
        if not dates:
            I("No dates to process. Ending the script.")
            return
        data = self.process_dates(dates)
        self._store_data(data)
