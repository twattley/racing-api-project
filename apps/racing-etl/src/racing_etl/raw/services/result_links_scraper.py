import pandas as pd
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.link_scraper_interface import ILinkScraper
from ...raw.interfaces.webriver_interface import IWebDriver


class ResultLinksScraperService:
    def __init__(
        self,
        scraper: ILinkScraper,
        storage_client: IStorageClient,
        driver: IWebDriver,
        schema: str,
        table_name: str,
        view_name: str,
        pipeline_status: PipelineStatus,
    ):
        self.scraper = scraper
        self.storage_client = storage_client
        self.driver = driver
        self.schema = schema
        self.table_name = table_name
        self.view_name = view_name
        self.pipeline_status = pipeline_status

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
        self.pipeline_status.add_debug(f"Processing {len(dates)} dates: {dates}")
        dataframes_list = []
        for date in dates:
            try:
                data: pd.DataFrame = self.scraper.scrape_links(
                    driver, date["race_date"].strftime("%Y-%m-%d")
                )
                self.pipeline_status.add_info(f"Scraped {len(data)} links for {date}")
                dataframes_list.append(data)
            except Exception as e:
                self.pipeline_status.add_error(
                    f"Error scraping links for date {date['race_date'].strftime('%Y-%m-%d')}: {e}"
                )
                continue

        if not dataframes_list:
            self.pipeline_status.add_info("No data scraped. Ending the script.")
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
            self.pipeline_status.add_info("No dates to process. Ending the script.")
            return
        data = self.process_dates(dates)
        self._store_data(data)
        self.pipeline_status.save_to_database()
