import time

import numpy as np
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...raw.interfaces.course_ref_data_interface import ICourseRefData
from ...raw.interfaces.link_scraper_interface import ILinkScraper

from ...data_types.pipeline_status import PipelineStatus


class TFResultsLinkScraper(ILinkScraper):
    def __init__(self, ref_data: ICourseRefData, pipeline_status: PipelineStatus):
        self.ref_data = ref_data
        self.pipeline_status = pipeline_status

    def scrape_links(
        self,
        driver: webdriver.Chrome,
        date: str,
    ) -> pd.DataFrame:
        driver.get(f"https://www.timeform.com/horse-racing/results/{str(date)}")
        time.sleep(5)
        ire_course_names = self.ref_data.get_uk_ire_course_names()
        world_course_names = self.ref_data.get_world_course_names()
        days_results_links = self._get_results_links(driver)
        data = pd.DataFrame(
            {
                "race_date": date,
                "link_url": days_results_links,
            }
        )
        data = data.assign(
            course_id=data["link_url"].str.split("/").str[8],
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
        self.pipeline_status.add_info(
            f"Scraped {len(data)} results links for date {date}"
        )
        return data

    def _get_pages_results_links(self, driver: webdriver.Chrome) -> list[str]:
        elements = driver.find_elements(
            By.CSS_SELECTOR, 'a.results-title[href*="/horse-racing/result/"]'
        )
        return [element.get_attribute("href") for element in elements]

    def _get_results_links(self, driver: webdriver.Chrome) -> list[str]:
        pages_links = self._get_pages_results_links(driver)
        buttons = driver.find_elements(
            By.CSS_SELECTOR, "button.w-course-region-tabs-button"
        )
        for button in buttons:
            WebDriverWait(driver, 20).until(EC.element_to_be_clickable(button))
            button.click()
            time.sleep(10)
            pages_links.extend(self._get_pages_results_links(driver))

        return list(set(pages_links))
