import hashlib
import re
from datetime import datetime

import pandas as pd
from playwright.sync_api import Page, Locator

from racing_etl.data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper


class TFResultsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus):
        self.pipeline_status = pipeline_status

    def scrape_data(self, page: Page, url: str) -> pd.DataFrame:
        race_details_link = TFResultsDataScraper._get_race_details_from_link(url)
        self.pipeline_status.add_debug(
            f"Scraping data for {url} sleeping for 2 seconds"
        )
        page.wait_for_timeout(2000)
        race_details_page = TFResultsDataScraper._get_race_details_from_page(page)
        return TFResultsDataScraper._get_performance_data(
            page, race_details_link, race_details_page, url
        )

    @staticmethod
    def _get_element_text_by_selector(row: Locator, css_selector: str):
        elements = row.locator(css_selector).all()
        for element in elements:
            text = element.text_content()
            if text and text.strip():
                return text.strip()
        return None

    @staticmethod
    def _return_element_from_css_selector(
        row: Locator,
        css_selector: str,
        multiple_elements: bool = False,
    ) -> str | None:
        try:
            locator = row.locator(css_selector)
            if locator.count() > 0:
                return locator.first.text_content()
            return None
        except Exception:
            return None

    @staticmethod
    def _find_element_text_by_xpath(row: Locator, xpath: str) -> str:
        return row.locator(f"xpath={xpath}").text_content()

    @staticmethod
    def _find_element_text_by_selector(
        row: Locator,
        selector: str,
        default: str = "Information not found for this row",
    ) -> str | None:
        locator = row.locator(selector)
        if locator.count() > 0:
            return locator.first.text_content()
        return default

    @staticmethod
    def _find_element_text_by_selector_strip(
        row: Locator,
        selector: str,
        chars_to_strip: str,
        default: str = "Information not found for this row",
    ) -> str | None:
        locator = row.locator(selector)
        if locator.count() > 0:
            text = locator.first.text_content()
            return text.strip(chars_to_strip) if text else default
        return default

    @staticmethod
    def _title_except_brackets(text: str) -> str:
        text = text.title()

        def uppercase_match(match):
            return match.group(0).upper()

        return re.sub(r"\([^)]*\)", uppercase_match, text)

    @staticmethod
    def _get_main_race_comment(page: Page) -> str:
        premium_comment_elements = page.locator(
            "td[title='Premium Race Comment']"
        ).all()
        for premium_comment_element in premium_comment_elements:
            paragraph_elements = premium_comment_element.locator("p").all()
            if paragraph_elements:
                first_paragraph_text = paragraph_elements[0].text_content().strip()
                if "rule 4" in first_paragraph_text.lower():
                    second_paragraph_text = (
                        paragraph_elements[1].text_content().strip()
                        if len(paragraph_elements) > 1
                        else ""
                    )
                    full_comment = f"{first_paragraph_text} {second_paragraph_text}"
                else:
                    full_comment = first_paragraph_text
                return full_comment
        return "No Comment Found"

    @staticmethod
    def _get_race_details_from_link(link: str) -> dict:
        *_, course, race_date, race_time, course_id, race = link.split("/")
        return {
            "course": course,
            "race_date": datetime.strptime(race_date, "%Y-%m-%d"),
            "race_time_debug": race_time,
            "race_time": datetime.strptime(f"{race_date} {race_time}", "%Y-%m-%d %H%M"),
            "course_id": course_id,
            "race": race,
            "race_id": hashlib.sha256(
                f"{course_id}_{race_date}_{race_time}_{race}".encode()
            ).hexdigest(),
        }

    @staticmethod
    def _get_race_details_from_page(page: Page) -> dict:
        titles = [
            # (variable name, title attribute of the span element)
            ("distance", "Distance expressed in miles, furlongs and yards"),
            ("going", "Race going"),
            ("prize", "Prize money to winner"),
            ("hcap_range", "BHA rating range"),
            ("age_range", "Horse age range"),
            ("race_type", "The type of race"),
        ]
        elements = page.locator("span.rp-header-text").all()

        values = {var: None for var, _ in titles}
        for var, tf_title in titles:
            for element in elements:
                if element.get_attribute("title") == tf_title:
                    values[var] = element.text_content()
                    break

        values["main_race_comment"] = TFResultsDataScraper._get_main_race_comment(page)

        return values

    @staticmethod
    def _get_entity_info_from_row(
        row: Locator, selector: str, index: int
    ) -> tuple[str, str]:
        locator = row.locator(selector)
        if locator.count() > 0:
            element = locator.first
            entity_name = element.text_content()
            if "Sire" in selector or "Dam" in selector:
                entity_name = TFResultsDataScraper._title_except_brackets(entity_name)
            entity_id = element.get_attribute("href").split("/")[index]
            return entity_name, entity_id

    @staticmethod
    def _get_entity_names(row: Locator):
        tf_horse_name = tf_horse_id = tf_horse_name_link = ""
        tf_clean_sire_name = tf_sire_name_id = ""
        tf_clean_dam_name = tf_dam_name_id = ""
        tf_clean_trainer_name = tf_trainer_id = ""
        tf_clean_jockey_name = tf_jockey_id = ""

        all_links = row.locator("a").all()
        for link in all_links:
            horse_links = row.locator("a.rp-horse").all()
            all_hrefs = link.get_attribute("href")
            if "horse-form" in all_hrefs:
                tf_horse_id = all_hrefs.split("/")[-1]
                tf_horse_name_link = (
                    all_hrefs.split("/")[-2].replace("-", " ").title().strip()
                )
            for horse_link in horse_links:
                horse_name = horse_link.text_content()
                if horse_name.strip():
                    tf_horse_name = TFResultsDataScraper._title_except_brackets(
                        re.sub(r"^\d+\.\s+", "", horse_name)
                    )
        for link in all_links:
            href = link.get_attribute("href")
            href_parts = href.split("/")
            if href_parts[-1] == "sire":
                tf_sire_name_link, tf_sire_name_id = href_parts[-3], href_parts[-2]
                tf_clean_sire_name = tf_sire_name_link.replace("-", " ").title().strip()
            if href_parts[-1] == "dam":
                tf_dam_name_link, tf_dam_name_id = href_parts[-3], href_parts[-2]
                tf_clean_dam_name = tf_dam_name_link.replace("-", " ").title().strip()
            if href_parts[4] == "trainer":
                tf_trainer_id, tf_trainer_name = href_parts[-1], href_parts[-3]
                tf_clean_trainer_name = (
                    tf_trainer_name.replace("-", " ").title().strip()
                )
            if href_parts[4] == "jockey":
                tf_jockey_id, tf_jockey_name = href_parts[-1], href_parts[-3]
                tf_clean_jockey_name = tf_jockey_name.replace("-", " ").title().strip()

        return (
            tf_horse_name,
            tf_horse_id,
            tf_horse_name_link,
            tf_clean_sire_name,
            tf_clean_dam_name,
            tf_sire_name_id,
            tf_dam_name_id,
            tf_clean_trainer_name,
            tf_trainer_id,
            tf_clean_jockey_name,
            tf_jockey_id,
        )

    @staticmethod
    def _get_performance_data(
        page: Page,
        race_details_link: dict,
        race_details_page: dict,
        link: str,
    ) -> pd.DataFrame:
        table_rows = page.locator(".rp-table-row").all()

        data = []
        for row in table_rows:
            performance_data = {}
            performance_data["tf_rating"] = (
                TFResultsDataScraper._return_element_from_css_selector(
                    row, "div.rp-circle.rp-rating.res-rating"
                )
            )
            performance_data["tf_speed_figure"] = (
                TFResultsDataScraper._return_element_from_css_selector(
                    row, "td.al-center.rp-tfig"
                )
            )
            performance_data["draw"] = (
                TFResultsDataScraper._return_element_from_css_selector(
                    row, "span.rp-draw"
                )
            )
            performance_data["finishing_position"] = (
                TFResultsDataScraper._find_element_text_by_selector(
                    row, 'span.rp-entry-number[title="Finishing Position"]'
                )
            )
            (
                performance_data["horse_name"],
                performance_data["horse_id"],
                performance_data["horse_name_link"],
                performance_data["sire_name"],
                performance_data["dam_name"],
                performance_data["sire_id"],
                performance_data["dam_id"],
                performance_data["trainer_name"],
                performance_data["trainer_id"],
                performance_data["jockey_name"],
                performance_data["jockey_id"],
            ) = TFResultsDataScraper._get_entity_names(row)
            performance_data["horse_age"] = (
                TFResultsDataScraper._find_element_text_by_selector(
                    row,
                    "td.al-center.rp-body-text.rp-ageequip-hide[title='Horse age']",
                    "Horse Age information not found for this row",
                )
            )
            equipment_elements = row.locator(
                "td.al-center.rp-body-text.rp-ageequip-hide > span"
            ).all()
            equipment = [el.text_content() for el in equipment_elements]
            performance_data["equipment"] = equipment[0] if equipment else None
            performance_data["official_rating"] = (
                TFResultsDataScraper._find_element_text_by_selector_strip(
                    row,
                    "td.al-center.rp-body-text.rp-ageequip-hide[title='Official rating given to this horse']",
                    "()",
                    "Official rating information not found for this row",
                )
            )
            performance_data["fractional_price"] = (
                TFResultsDataScraper._find_element_text_by_selector(
                    row, ".price-fractional", "Price information not found for this row"
                )
            )
            performance_data["betfair_win_sp"] = (
                TFResultsDataScraper._find_element_text_by_selector(
                    row,
                    "td.al-center.rp-result-sp.rp-result-bsp-hide[title='Betfair Win SP']",
                    "Betfair Win SP information not found for this row",
                )
            )
            performance_data["betfair_place_sp"] = (
                TFResultsDataScraper._find_element_text_by_selector_strip(
                    row,
                    "td.al-center.rp-result-sp.rp-result-bsp-hide[title='Betfair Place SP']",
                    "()",
                    "Betfair Place SP information not found for this row",
                )
            )
            performance_data["in_play_prices"] = (
                TFResultsDataScraper._find_element_text_by_selector(
                    row,
                    "td.al-center.rp-body-text.rp-ipprices[title='The hi/lo Betfair In-Play prices with a payout of more than GBP100']",
                    "Betfair In-Play prices information not found for this row",
                )
            )
            performance_data["tf_comment"] = (
                TFResultsDataScraper._find_element_text_by_selector(
                    row, "tr.rp-entry-comment.rp-comments.rp-body-text"
                )
            )
            performance_data.update(race_details_link)
            performance_data.update(race_details_page)

            performance_data["debug_link"] = link
            performance_data["created_at"] = datetime.now()

            unique_id = (
                performance_data["horse_id"]
                + performance_data["finishing_position"]
                + performance_data["debug_link"]
            )
            performance_data["unique_id"] = hashlib.sha512(
                unique_id.encode()
            ).hexdigest()

            data.append(performance_data)

        return pd.DataFrame(data)
