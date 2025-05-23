import time

import numpy as np
import pandas as pd
from api_helpers.helpers.logging_config import I
from selenium import webdriver
from selenium.webdriver.common.by import By

from ...config import Config
from ...raw.helpers.course_ref_data import CourseRefData
from ...raw.interfaces.course_ref_data_interface import ICourseRefData
from ...raw.interfaces.link_scraper_interface import ILinkScraper
from ...raw.services.result_links_scraper import ResultLinksScraperService
from ...raw.webdriver.web_driver import WebDriver
from ...storage.storage_client import get_storage_client


class RPResultsLinkScraper(ILinkScraper):
    def __init__(self, ref_data: ICourseRefData):
        self.ref_data = ref_data

    def scrape_links(
        self,
        driver: webdriver.Chrome,
        date: str,
    ) -> pd.DataFrame:
        driver.get(f"https://www.racingpost.com/results/{date}")
        time.sleep(1)
        ire_course_names = self.ref_data.get_uk_ire_course_names()
        world_course_names = self.ref_data.get_world_course_names()
        days_results_links = self._get_results_links(driver)
        I(f"Found {len(days_results_links)} valid links for date {date}.")
        data = pd.DataFrame(
            {
                "race_date": date,
                "link_url": days_results_links,
            }
        )
        data = data.assign(
            course_id=data["link_url"].str.split("/").str[4],
            course_name=data["link_url"].str.split("/").str[5],
        )
        data = data.assign(
            country_category=np.select(
                [
                    data["course_name"].isin(ire_course_names),
                    data["course_name"].isin(world_course_names),
                ],
                [1, 2],
                default=0,
            ),
        )
        return data

    def _get_results_links(self, driver: webdriver.Chrome) -> list[str]:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='results/']")
        hrefs = [link.get_attribute("href") for link in links]
        return list(
            {
                i
                for i in hrefs
                if "fullReplay" not in i
                and len(i.split("/")) == 8
                and "winning-times" not in i
            }
        )


if __name__ == "__main__":
    config = Config()
    storage_client = get_storage_client("postgres")

    service = ResultLinksScraperService(
        scraper=RPResultsLinkScraper(
            ref_data=CourseRefData(source="rp", storage_client=storage_client)
        ),
        storage_client=storage_client,
        driver=WebDriver(config),
        schema="rp_raw",
        view_name=config.db.raw.results_data.links_view,
        table_name=config.db.raw.results_data.links_table,
    )
    service.run_results_links_scraper()
