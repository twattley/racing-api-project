import hashlib
import re
import time
from datetime import datetime

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By

from racing_etl.data_types.pipeline_status import PipelineStatus

from ...raw.interfaces.data_scraper_interface import IDataScraper


class TFResultsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus):
        self.pipeline_status = pipeline_status

    def scrape_data(self, driver: webdriver.Chrome, url: str) -> pd.DataFrame:
        race_details_link = TFResultsDataScraper._get_race_details_from_link(url)
        self.pipeline_status.add_debug(
            f"Scraping data for {url} sleeping for 2 seconds"
        )
        time.sleep(2)
        race_details_page = TFResultsDataScraper._get_race_details_from_page(driver)
        return TFResultsDataScraper._get_performance_data(
            driver, race_details_link, race_details_page, url
        )

    @staticmethod
    def _get_element_text_by_selector(row, css_selector):
        elements = row.find_elements(By.CSS_SELECTOR, css_selector)
        return next(
            (element.text.strip() for element in elements if element.text.strip()),
            None,
        )

    @staticmethod
    def _return_element_from_css_selector(
        table_row: webdriver.Chrome,
        css_selector: str,
        multiple_elements: bool = False,
    ) -> str | None:
        try:
            element = table_row.find_element(By.CSS_SELECTOR, css_selector)
            if multiple_elements:
                element = element[0]
            return element.text
        except Exception:
            return None

    @staticmethod
    def _find_element_text_by_xpath(row: webdriver.Chrome, xpath: str) -> str:
        return row.find_element(By.XPATH, xpath).text

    @staticmethod
    def _find_element_text_by_selector(
        row: webdriver.Chrome,
        selector: str,
        default: str = "Information not found for this row",
    ) -> str | None:
        elements = row.find_elements(By.CSS_SELECTOR, selector)
        return elements[0].text if elements else default

    @staticmethod
    def _find_element_text_by_selector_strip(
        row: webdriver.Chrome,
        selector: str,
        chars_to_strip: str,
        default: str = "Information not found for this row",
    ) -> str | None:
        elements = row.find_elements(By.CSS_SELECTOR, selector)
        return elements[0].text.strip(chars_to_strip) if elements else default

    @staticmethod
    def _title_except_brackets(text: str) -> str:
        text = text.title()

        def uppercase_match(match):
            return match.group(0).upper()

        return re.sub(r"\([^)]*\)", uppercase_match, text)

    @staticmethod
    def _get_main_race_comment(driver: webdriver.Chrome) -> str:
        premium_comment_elements = driver.find_elements(
            By.CSS_SELECTOR, "td[title='Premium Race Comment']"
        )
        for premium_comment_element in premium_comment_elements:
            paragraph_elements = premium_comment_element.find_elements(By.TAG_NAME, "p")
            if paragraph_elements:
                first_paragraph_text = paragraph_elements[0].text.strip()
                if "rule 4" in first_paragraph_text.lower():
                    second_paragraph_text = (
                        paragraph_elements[1].text.strip()
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
    def _get_race_details_from_page(driver: webdriver.Chrome) -> dict:
        titles = [
            # (variable name, title attribute of the span element)
            ("distance", "Distance expressed in miles, furlongs and yards"),
            ("going", "Race going"),
            ("prize", "Prize money to winner"),
            ("hcap_range", "BHA rating range"),
            ("age_range", "Horse age range"),
            ("race_type", "The type of race"),
        ]
        elements = driver.find_elements(By.CSS_SELECTOR, "span.rp-header-text")

        values = {var: None for var, _ in titles}
        for var, tf_title in titles:
            for element in elements:
                if element.get_attribute("title") == tf_title:
                    values[var] = element.text
                    break

        values["main_race_comment"] = TFResultsDataScraper._get_main_race_comment(
            driver
        )

        return values

    @staticmethod
    def _get_entity_info_from_row(
        row: webdriver.Chrome, selector: str, index: int
    ) -> tuple[str, str]:
        elements = row.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            element = elements[0]
            entity_name = element.text
            if "Sire" in selector or "Dam" in selector:
                entity_name = TFResultsDataScraper._title_except_brackets(entity_name)
            entity_id = element.get_attribute("href").split("/")[index]
            return entity_name, entity_id

    @staticmethod
    def _get_entity_names(row: webdriver.Chrome):
        tf_horse_name = tf_horse_id = tf_horse_name_link = ""
        tf_clean_sire_name = tf_sire_name_id = ""
        tf_clean_dam_name = tf_dam_name_id = ""
        tf_clean_trainer_name = tf_trainer_id = ""
        tf_clean_jockey_name = tf_jockey_id = ""

        all_links = row.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            horse_links = row.find_elements(By.CSS_SELECTOR, "a.rp-horse")
            all_hrefs = link.get_attribute("href")
            if "horse-form" in all_hrefs:
                tf_horse_id = all_hrefs.split("/")[-1]
                tf_horse_name_link = (
                    all_hrefs.split("/")[-2].replace("-", " ").title().strip()
                )
            for horse_link in horse_links:
                horse_name = horse_link.text
                if horse_name.strip():
                    tf_horse_name = TFResultsDataScraper._title_except_brackets(
                        re.sub(r"^\d+\.\s+", "", horse_link.text)
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
        driver: webdriver.Chrome,
        race_details_link: dict,
        race_details_page: dict,
        link: str,
    ) -> pd.DataFrame:
        table_rows = driver.find_elements(By.CLASS_NAME, "rp-table-row")

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
            equipment = [
                element.text
                for element in row.find_elements(
                    By.CSS_SELECTOR, "td.al-center.rp-body-text.rp-ageequip-hide > span"
                )
            ]
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
