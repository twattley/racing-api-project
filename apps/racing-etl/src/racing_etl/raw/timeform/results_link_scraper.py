import numpy as np
import pandas as pd
from playwright.sync_api import Page

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.course_ref_data_interface import ICourseRefData
from ...raw.interfaces.link_scraper_interface import ILinkScraper


class TFResultsLinkScraper(ILinkScraper):
    def __init__(self, ref_data: ICourseRefData, pipeline_status: PipelineStatus):
        self.ref_data = ref_data
        self.pipeline_status = pipeline_status

    def scrape_links(
        self,
        page: Page,
        date: str,
    ) -> pd.DataFrame:
        page.goto(f"https://www.timeform.com/horse-racing/results/{str(date)}", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        ire_course_names = self.ref_data.get_uk_ire_course_names()
        world_course_names = self.ref_data.get_world_course_names()
        days_results_links = self._get_results_links(page)
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

    def _get_pages_results_links(self, page: Page) -> list[str]:
        elements = page.locator('a.results-title[href*="/horse-racing/result/"]').all()
        return [element.get_attribute("href") for element in elements]

    def _get_results_links(self, page: Page) -> list[str]:
        pages_links = self._get_pages_results_links(page)
        buttons = page.locator("button.w-course-region-tabs-button").all()
        for button in buttons:
            button.wait_for(state="visible", timeout=20000)
            button.click()
            page.wait_for_timeout(5000)
            pages_links.extend(self._get_pages_results_links(page))

        return list(set(pages_links))
