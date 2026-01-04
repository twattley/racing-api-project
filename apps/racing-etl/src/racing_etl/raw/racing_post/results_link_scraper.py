import numpy as np
import pandas as pd
from playwright.sync_api import Page

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.course_ref_data_interface import ICourseRefData
from ...raw.interfaces.link_scraper_interface import ILinkScraper


class RPResultsLinkScraper(ILinkScraper):
    def __init__(self, ref_data: ICourseRefData, pipeline_status: PipelineStatus):
        self.ref_data = ref_data
        self.pipeline_status = pipeline_status

    def scrape_links(
        self,
        page: Page,
        date: str,
    ) -> pd.DataFrame:
        page.goto(
            f"https://www.racingpost.com/results/{date}",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        page.wait_for_selector("a[href*='results/']", timeout=30000)
        page.wait_for_timeout(1000)

        ire_course_names = self.ref_data.get_uk_ire_course_names()
        world_course_names = self.ref_data.get_world_course_names()
        days_results_links = self._get_results_links(page)
        self.pipeline_status.add_info(
            f"Found {len(days_results_links)} valid links for date {date}."
        )
        if len(days_results_links) == 0:
            self.pipeline_status.add_warning(f"***NO RESULTS LINKS FOUND***")
            return pd.DataFrame()
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

    def _get_results_links(self, page: Page) -> list[str]:
        # Get all hrefs in one JavaScript call - no stale element issues
        hrefs = page.eval_on_selector_all(
            "a[href*='results/']", "elements => elements.map(el => el.href)"
        )
        return list(
            {
                i
                for i in hrefs
                if "fullReplay" not in i
                and len(i.split("/")) == 8
                and "winning-times" not in i
            }
        )
