import re

import pandas as pd
from playwright.sync_api import Page

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.course_ref_data_interface import ICourseRefData
from ...raw.interfaces.link_scraper_interface import ILinkScraper


class TFRacecardsLinkScraper(ILinkScraper):
    BASE_URL = "https://www.timeform.com/horse-racing/racecards"

    def __init__(self, ref_data: ICourseRefData, pipeline_status: PipelineStatus):
        self.pipeline_status = pipeline_status
        self.ref_data = ref_data

    def scrape_links(self, page: Page, date: str) -> pd.DataFrame:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.pipeline_status.add_info(
                    f"Scraping Timeform links for {date} (Attempt {attempt + 1})"
                )
                page.goto(self.BASE_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                race_types = self._get_race_types(page)
                self._click_for_racecards(page, date)
                links = self._get_racecard_links(page, date)
                data = pd.DataFrame(
                    {
                        "link_url": links,
                        "race_date": [date] * len(links),
                    }
                )
                data["race_type"] = data["link_url"].map(race_types)
                return data
            except Exception as e:
                self.pipeline_status.add_error(
                    f"An error occurred on attempt {attempt + 1}: {str(e)}"
                )
                if attempt == max_attempts - 1:
                    raise
                page.wait_for_timeout(5000)

        raise ValueError(f"Failed to scrape links after {max_attempts} attempts")

    def _get_race_types(self, page: Page):
        race_links = page.locator("a[href*='/horse-racing/racecards/']").all()

        race_types = {}
        for link in race_links:
            text = link.evaluate("el => el.outerHTML")
            href = link.get_attribute("href")
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

    def _click_for_racecards(self, page: Page, date: str):
        button = page.locator(f"button.w-racecard-grid-nav-button[data-meeting-date='{date}']")
        button.wait_for(state="visible", timeout=10000)
        button.click()
        page.wait_for_timeout(5000)

    def _get_racecard_links(self, page: Page, date: str) -> list[str]:
        uk_ire_course_ids = self.ref_data.get_uk_ire_course_ids()
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Wait for links to be present
                page.wait_for_selector("a", timeout=10000)

                # Get all hrefs in one JavaScript call - no stale element issues!
                hrefs = page.eval_on_selector_all(
                    "a[href]", "elements => elements.map(el => el.href)"
                )

                trimmed_hrefs = [
                    href[:-1] if href.endswith("/") else href for href in hrefs if href
                ]

                patterns = [
                    rf"{self.BASE_URL}/{course_name}/{date}/([01]\d|2[0-3])[0-5]\d\/{course_id}/(10|[1-9])/(.*)"
                    for course_id, course_name in uk_ire_course_ids.items()
                ]

                if not patterns:
                    raise ValueError(f"No patterns found on date: {date}")

                self.pipeline_status.add_info(f"Found {len(hrefs)} links for {date}")

                filtered_urls = {
                    url
                    for url in trimmed_hrefs
                    for pattern in patterns
                    if re.search(pattern, url)
                }

                if filtered_urls:
                    return sorted(filtered_urls)
                else:
                    self.pipeline_status.add_debug(
                        f"No matching URLs found on attempt {attempt + 1}. Retrying..."
                    )
                    page.wait_for_timeout(2000)
            except Exception as e:
                self.pipeline_status.add_error(
                    f"An error occurred on attempt {attempt + 1}: {str(e)}"
                )
                if attempt == max_attempts - 1:
                    raise
                page.wait_for_timeout(2000)

        raise ValueError(f"Failed to get racecard links after {max_attempts} attempts")
