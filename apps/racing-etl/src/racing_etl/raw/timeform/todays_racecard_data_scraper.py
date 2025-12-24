import hashlib
import re
from datetime import datetime

import pandas as pd
from playwright.sync_api import Page

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper


class TFRacecardsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus) -> None:
        self.pipeline_status = pipeline_status

    def scrape_data(self, page: Page, url: str) -> pd.DataFrame:
        race_data = self._get_data_from_url(url)
        age_range = self._get_optional_element_text(
            page, "span.rp-header-text[title='Horse age range']"
        )
        bha_rating_range = self._get_optional_element_text(
            page, "span.rp-header-text.pr3[title='BHA rating range']"
        )
        prize_money = self._get_optional_element_text(
            page, "span.rp-header-text.pr3[title='Prize money to winner']"
        )
        horse_data = self._get_horse_data(page)
        return horse_data.assign(
            **race_data,
            age_range=age_range,
            hcap_range=bha_rating_range,
            prize=prize_money,
            unique_id=lambda x: x.apply(
                lambda y: hashlib.sha512(f"{y['horse_id']}{url}".encode()).hexdigest(),
                axis=1,
            ),
            finishing_position=None,
            fractional_price=None,
            main_race_comment=None,
            draw=None,
            tf_rating=None,
            tf_speed_figure=None,
            betfair_win_sp=None,
            going=None,
            in_play_prices=None,
            debug_link=url,
            equipment=None,
            official_rating=None,
            race_id=None,
            betfair_place_sp=None,
            distance=None,
            horse_name_link=None,
            race_type=None,
            tf_comment=None,
            horse_age=None,
            race_time_debug=None,
            created_at=datetime.now(),
        )

    def _format_entity(self, entity: str) -> str:
        return entity.replace("-", " ").title().strip()

    def _get_optional_element_text(self, page: Page, css_selector: str) -> str | None:
        try:
            locator = page.locator(css_selector)
            if locator.count() > 0:
                return locator.first.text_content().strip()
            return None
        except Exception:
            return None

    def _get_data_from_url(self, url: str) -> dict:
        if url.endswith("/"):
            url = url[:-1]
        *_, course, race_date, race_time, course_id, race, _ = url.split("/")
        course = course.replace("-", " ").title().strip()
        race_timestamp = datetime.strptime(f"{race_date} {race_time}", "%Y-%m-%d %H%M")
        return {
            "course_id": course_id,
            "course": course,
            "race_date": datetime.strptime(race_date, "%Y-%m-%d"),
            "race_time": race_timestamp,
            "race": race,
        }

    def _get_horse_data(self, page: Page) -> pd.DataFrame:
        page.wait_for_selector("tbody.rp-horse-row", timeout=10000)

        horse_entries = page.locator("tbody.rp-horse-row").all()
        horse_data = []
        trainer_pattern = (
            r"https://www.timeform.com/horse-racing/trainer/([a-zA-Z-]+)/form/([0-9]+)"
        )
        jockey_pattern = (
            r"https://www.timeform.com/horse-racing/jockey/([a-zA-Z-]+)/form/([0-9]+)"
        )
        horse_pattern = r"https://www.timeform.com/horse-racing/horse/form/([a-zA-Z-]+)/([0-9]+)/([a-zA-Z-]+)/([0-9]+)"

        for entry in horse_entries:
            links = entry.locator("a").all()
            for link in links:
                href = link.get_attribute("href")
                if href.endswith("/sire"):
                    *_, sire_name, sire_id, _ = href.split("/")
                if href.endswith("/dam"):
                    *_, dam_name, dam_id, _ = href.split("/")
                if re.search(trainer_pattern, href):
                    *_, trainer_name, trainer_id = re.search(
                        trainer_pattern, href
                    ).groups()
                    continue
                if re.search(jockey_pattern, href):
                    *_, jockey_name, jockey_id = re.search(
                        jockey_pattern, href
                    ).groups()
                    continue
                if re.search(horse_pattern, href):
                    *_, horse_name, horse_id, _, _ = re.search(
                        horse_pattern, href
                    ).groups()
                    continue
            horse_name = self._format_entity(horse_name)
            sire_name = self._format_entity(sire_name)
            dam_name = self._format_entity(dam_name)
            trainer_name = self._format_entity(trainer_name)
            jockey_name = self._format_entity(jockey_name)

            horse_data.append(
                {
                    "horse_name": horse_name,
                    "horse_id": horse_id,
                    "sire_name": sire_name,
                    "sire_id": sire_id,
                    "dam_name": dam_name,
                    "dam_id": dam_id,
                    "trainer_name": trainer_name,
                    "trainer_id": trainer_id,
                    "jockey_name": jockey_name,
                    "jockey_id": jockey_id,
                }
            )

        data = pd.DataFrame(horse_data)

        self.pipeline_status.add_info(f"Scraped horse data: {data.shape[0]} entries")

        return data
