import re
import time

import pandas as pd
from api_helpers.helpers.logging_config import I
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...raw.interfaces.course_ref_data_interface import ICourseRefData
from ...raw.interfaces.link_scraper_interface import ILinkScraper


class TFRacecardsLinkScraper(ILinkScraper):
    BASE_URL = "https://www.timeform.com/horse-racing/racecards"

    def __init__(self, ref_data: ICourseRefData):
        self.ref_data = ref_data

    def scrape_links(self, driver: webdriver.Chrome, date: str) -> pd.DataFrame:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                I(f"Scraping Timeform links for {date} (Attempt {attempt + 1})")
                driver.get(self.BASE_URL)
                time.sleep(15)
                race_types = self._get_race_types(driver)
                self._click_for_racecards(driver, date)
                links = self._get_racecard_links(driver, date)
                data = pd.DataFrame(
                    {
                        "link_url": links,
                        "race_date": [date] * len(links),
                    }
                )
                data["race_type"] = data["link_url"].map(race_types)
                return data
            except Exception as e:
                I(f"An error occurred on attempt {attempt + 1}: {str(e)}")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(5)  # Wait a bit longer before retrying the entire process

        raise ValueError(f"Failed to scrape links after {max_attempts} attempts")

    def _get_race_types(self, driver: webdriver.Chrome):
        race_links = driver.find_elements(
            By.CSS_SELECTOR, "a[href*='/horse-racing/racecards/']"
        )

        race_texts = [link.get_attribute("outerHTML") for link in race_links]
        hrefs = [link.get_attribute("href") for link in race_links]

        race_types = {}
        for text, href in zip(race_texts, hrefs):
            if "Hurdle" in text:
                race_types[href] = "Hurdle"
            elif "Chase" in text:
                race_types[href] = "Chase"
            elif "Flat" in text:
                race_types[href] = "Flat"
            elif "Bumper" in text:
                race_types[href] = "Bumper"
            else:
                continue

        return race_types

    def _click_for_racecards(self, driver: webdriver.Chrome, date: str):
        button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    f"button.w-racecard-grid-nav-button[data-meeting-date='{date}']",
                )
            )
        )
        driver.execute_script("arguments[0].click();", button)
        I(f"Clicked on button for date: {date}")
        time.sleep(10)

    def _get_racecard_links(self, driver: webdriver.Chrome, date: str) -> list[str]:
        uk_ire_course_ids = self.ref_data.get_uk_ire_course_ids()
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Wait for the links to be present
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a"))
                )

                hrefs = []
                elements = driver.find_elements(By.XPATH, "//a")
                for element in elements:
                    try:
                        href = element.get_attribute("href")
                        if href:
                            hrefs.append(href)
                    except StaleElementReferenceException:
                        continue  # Skip this element if it's stale

                trimmed_hrefs = [
                    href[:-1] if href.endswith("/") else href for href in hrefs
                ]

                patterns = [
                    rf"{self.BASE_URL}/{course_name}/{date}/([01]\d|2[0-3])[0-5]\d\/{course_id}/(10|[1-9])/(.*)"
                    for course_id, course_name in uk_ire_course_ids.items()
                ]

                if not patterns:
                    raise ValueError(f"No patterns found on date: {date}")

                I(f"Found {len(hrefs)} links for {date}")

                filtered_urls = {
                    url
                    for url in trimmed_hrefs
                    for pattern in patterns
                    if re.search(pattern, url)
                }

                if filtered_urls:
                    return sorted(filtered_urls)
                else:
                    I(f"No matching URLs found on attempt {attempt + 1}. Retrying...")
                    time.sleep(2)  # Wait a bit before retrying
            except Exception as e:
                I(f"An error occurred on attempt {attempt + 1}: {str(e)}")
                if attempt == max_attempts - 1:
                    raise
                time.sleep(2)  # Wait a bit before retrying

        raise ValueError(f"Failed to get racecard links after {max_attempts} attempts")
