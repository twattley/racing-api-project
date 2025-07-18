import hashlib
import re
import time
from datetime import datetime

import numpy as np
import pandas as pd
import pytz
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper


class RPResultsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus) -> None:
        self.pipeline_status = pipeline_status
        self.pedigree_settings_button_toggled = False

    def scrape_data(self, driver: webdriver.Chrome, url: str) -> pd.DataFrame:
        self._wait_for_page_load(driver)

        self._toggle_button(driver)

        created_at = datetime.now(pytz.timezone("Europe/London")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        *_, course_id, course, race_date, race_id = url.split("/")
        surface, country, course_name = self._get_course_country_data(driver)
        race_time = self._return_element_text_from_css(
            driver,
            "span.rp-raceTimeCourseName__time[data-test-selector='text-raceTime']",
        )
        race_title = self._return_element_text_from_css(
            driver, "h2.rp-raceTimeCourseName__title"
        )
        conditions = self._get_optional_element_text(
            driver, "span.rp-raceTimeCourseName_ratingBandAndAgesAllowed"
        )
        race_class = self._get_optional_element_text(
            driver, "span.rp-raceTimeCourseName_class"
        )
        distance = self._return_element_text_from_css(
            driver, "span.rp-raceTimeCourseName_distance"
        )
        distance_full = self._get_optional_element_text(
            driver, "span.rp-raceTimeCourseName_distanceFull"
        )
        going = self._return_element_text_from_css(
            driver, "span.rp-raceTimeCourseName_condition"
        )
        winning_time = self._get_raw_winning_time(driver)
        number_of_runners = self._get_number_of_runners(driver)
        try:
            total_prize_money, first_place_prize_money, currency = (
                self._get_prize_money(driver)
            )
        except Exception:
            total_prize_money, first_place_prize_money, currency = (
                np.nan,
                np.nan,
                np.nan,
            )

        performance_data, order = self._get_performance_data(driver)
        performance_data = self._get_comment_data(driver, order, performance_data)
        performance_data = self._get_horse_type_data(driver, order, performance_data)
        performance_data = self._get_pedigree_data(driver, order, performance_data)
        race_timestamp = self._create_race_time(race_date, race_time, country)
        performance_data = pd.DataFrame(performance_data).assign(
            race_date=datetime.strptime(race_date, "%Y-%m-%d"),
            race_title=race_title,
            race_time_debug=race_time,
            race_time=race_timestamp,
            conditions=conditions,
            race_class=race_class,
            distance=distance,
            distance_full=distance_full,
            going=going,
            winning_time=winning_time,
            number_of_runners=number_of_runners,
            total_prize_money=total_prize_money,
            first_place_prize_money=first_place_prize_money,
            currency=currency,
            course_id=course_id,
            course_name=course_name,
            course=course,
            debug_link=url,
            race_id=race_id,
            country=country,
            surface=surface,
            created_at=created_at,
            unique_id=lambda x: x.apply(
                lambda y: hashlib.sha512(
                    f"{y['horse_id']}{y['debug_link']}".encode()
                ).hexdigest(),
                axis=1,
            ),
            meeting_id=lambda x: x.apply(
                lambda y: hashlib.sha512(
                    f"{y['course_id']}{y['race_date']}".encode()
                ).hexdigest(),
                axis=1,
            ),
            rp_comment=None,
        )

        performance_data = performance_data.pipe(self._get_adj_total_distance_beaten)

        performance_data = performance_data.apply(
            lambda x: x.str.strip() if x.dtype == "object" else x
        )

        performance_data = performance_data.dropna(subset=["race_time"])
        if performance_data.empty:
            self.pipeline_status.add_error(
                f"No data for {url} failure to scrape timestamp"
            )
        self.pipeline_status.add_info(
            f"Scraped {len(performance_data)} rows for {url}"
        )
        return performance_data[
            [
                "race_time",
                "race_date",
                "course_name",
                "race_class",
                "horse_name",
                "horse_type",
                "horse_age",
                "headgear",
                "conditions",
                "horse_price",
                "race_title",
                "distance",
                "distance_full",
                "going",
                "number_of_runners",
                "total_prize_money",
                "first_place_prize_money",
                "winning_time",
                "official_rating",
                "horse_weight",
                "draw",
                "country",
                "surface",
                "finishing_position",
                "total_distance_beaten",
                "ts_value",
                "rpr_value",
                "extra_weight",
                "comment",
                "race_time_debug",
                "currency",
                "course",
                "jockey_name",
                "jockey_claim",
                "trainer_name",
                "sire_name",
                "dam_name",
                "dams_sire",
                "owner_name",
                "horse_id",
                "trainer_id",
                "jockey_id",
                "sire_id",
                "dam_id",
                "dams_sire_id",
                "owner_id",
                "race_id",
                "course_id",
                "meeting_id",
                "unique_id",
                "debug_link",
                "created_at",
                "adj_total_distance_beaten",
                "rp_comment",
            ]
        ]

    def _toggle_button(self, driver):
        if self.pedigree_settings_button_toggled:
            return
        try:
            close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        "button.ab-close-button[aria-label='Close Message']",
                    )
                )
            )
            close_btn.click()
        except Exception:
            pass

        pedigree_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-test-selector="button-pedigree"]')
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", pedigree_button
        )
        time.sleep(3)
        pedigree_button.click()
        self.pedigree_settings_button_toggled = True

    def _wait_for_page_load(self, driver: webdriver.Chrome) -> None:
        """
        Logs which elements were not found on the page.
        """
        # Elements that just need to be present
        presence_elements = [
            (".rp-raceInfo", "Race Info"),
            ("div[data-test-selector='text-prizeMoney']", "Prize Money"),
            (
                "tr.rp-horseTable__commentRow[data-test-selector='text-comments']",
                "Comments",
            ),
            (
                "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']",
                "Pedigree Info",
            ),
            ("a.rp-raceTimeCourseName__name", "Course Name"),
            (
                "span.rp-raceTimeCourseName__time[data-test-selector='text-raceTime']",
                "Race Time",
            ),
            ("h2.rp-raceTimeCourseName__title", "Race Title"),
            ("span.rp-raceTimeCourseName_distance", "Distance"),
            ("span.rp-raceTimeCourseName_condition", "Going"),
            ("tr.rp-horseTable__pedigreeRow td", "Pedigree Data"),
        ]

        # Elements that need to be clickable
        clickable_elements = [
            ("[data-test-selector='button-pedigree']", "Pedigree Button"),
        ]

        missing_elements = []

        # Check presence elements
        for selector, name in presence_elements:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                self.pipeline_status.add_error(f"Missing element: {name}")
                missing_elements.append(name)

        # Check clickable elements
        for selector, name in clickable_elements:
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                self.pipeline_status.add_error(f"Element not clickable: {name}")
                missing_elements.append(name)

        if missing_elements:
            raise ValueError(f"Missing elements: {', '.join(missing_elements)}")

    def _convert_to_24_hour(self, time_str: str) -> str:
        """
        Converts a time string from 12-hour format to 24-hour format.
        """
        hours, minutes = map(int, time_str.split(":"))
        if hours < 10:
            hours += 12
        return f"{hours:02d}:{minutes:02d}"

    def _create_race_time(
        self, race_date: str, race_time: str, country: str
    ) -> datetime:
        if country in {"IRE", "UK", "FR", "UAE"}:
            race_time = self._convert_to_24_hour(race_time)
        return datetime.strptime(f"{race_date} {race_time}", "%Y-%m-%d %H:%M")

    def _get_entity_data_from_link(self, entity_link: str) -> tuple[str, str]:
        entity_id, entity_name = entity_link.split("/")[-2:]
        entity_name = " ".join(i.title() for i in entity_name.split("-"))
        return entity_id, entity_name

    def _return_element_text_from_css(
        self, driver: webdriver.Chrome, element_id: str
    ) -> str:
        return driver.find_element(By.CSS_SELECTOR, element_id).text.strip()

    def _get_optional_element_text(self, driver: webdriver.Chrome, css_selector: str):
        try:
            return driver.find_element(By.CSS_SELECTOR, css_selector).text.strip()
        except Exception:
            return None

    def _get_raw_winning_time(self, driver: webdriver.Chrome):
        race_info = " ".join(
            element.text.strip()
            for element in driver.find_elements(By.CSS_SELECTOR, ".rp-raceInfo")
        ).splitlines()[0]
        match = re.search(r"winning time: (.*?) total sp:", race_info, re.IGNORECASE)

        return match[1] if match else np.nan

    def _get_number_of_runners(self, driver: webdriver.Chrome) -> str:
        race_info = " ".join(
            element.text.strip()
            for element in driver.find_elements(By.CSS_SELECTOR, ".rp-raceInfo")
        ).splitlines()[0]
        match = re.search(r"(.*?) winning time:", race_info, re.IGNORECASE)
        if match:
            return match[1].lower().split("ran")[0].strip()

    def _get_prize_money(self, driver: webdriver.Chrome) -> tuple[int, int, str]:
        prize_money_container = driver.find_element(
            By.CSS_SELECTOR, "div[data-test-selector='text-prizeMoney']"
        )
        prize_money_text = prize_money_container.text

        places_and_money = re.split(
            r"\s*(?:1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th|13th|14th|15th)\s*",
            prize_money_text,
        )
        places_and_money = list(filter(None, places_and_money))
        currency_mapping = {"€": "EURO", "£": "POUNDS"}

        # Split at the decimal point and keep only the part before it, then remove commas and convert to int
        numbers = [
            int(p.split(".")[0].replace(",", "").replace("€", "").replace("£", ""))
            for p in places_and_money
        ]

        total = sum(numbers)
        rounded_total_in_thousands = round(total, -3) // 1000
        first_place_number = numbers[
            0
        ]  # Already converted to int, no need to process again
        first_place_rounded_in_thousands = round(first_place_number, -3) // 1000
        currency_symbol = places_and_money[0][0]
        currency_name = currency_mapping.get(currency_symbol, currency_symbol)
        return (
            rounded_total_in_thousands,
            first_place_rounded_in_thousands,
            currency_name,
        )

    def _get_performance_data(
        self,
        driver: webdriver.Chrome,
    ) -> tuple[list[dict[str, str]], list[tuple[int, str]]]:
        horse_data = []

        order = []

        rows = driver.find_elements(
            By.CSS_SELECTOR, "tr.rp-horseTable__mainRow[data-test-selector='table-row']"
        )
        for index, row in enumerate(rows):
            horse_position = row.find_element(
                By.CSS_SELECTOR,
                "span.rp-horseTable__pos__number[data-test-selector='text-horsePosition']",
            ).text.strip()

            if "(" in horse_position:
                draw = horse_position.split("(")[1].replace(")", "").strip()
                horse_position = horse_position.split("(")[0].strip()
            else:
                draw = np.nan

            try:
                jockey_element = row.find_element(
                    By.CSS_SELECTOR, "a[href*='/profile/jockey']"
                )
                jockey_link = jockey_element.get_attribute("href")
                jockey_id, jockey_name = self._get_entity_data_from_link(jockey_link)
            except Exception:
                jockey_id, jockey_name = np.nan, np.nan

            try:
                owner_element = row.find_element(
                    By.CSS_SELECTOR, "a[href*='/profile/owner']"
                )
                owner_link = owner_element.get_attribute("href")
                owner_id, owner_name = self._get_entity_data_from_link(owner_link)
            except Exception:
                owner_id, owner_name = np.nan, np.nan

            sup_elements = jockey_element.find_elements(
                By.XPATH, "./following-sibling::sup"
            )
            if sup_elements:
                jockey_claim = sup_elements[0].get_attribute("textContent").strip()
            else:
                jockey_claim = np.nan

            try:
                trainer_element = row.find_element(
                    By.CSS_SELECTOR, "a[href*='/profile/trainer']"
                )
                trainer_link = trainer_element.get_attribute("href")
                trainer_id, trainer_name = self._get_entity_data_from_link(trainer_link)
            except Exception:
                trainer_id, trainer_name = np.nan, np.nan

            horse_element = row.find_element(
                By.CSS_SELECTOR, "a[href*='/profile/horse']"
            )
            horse_link = horse_element.get_attribute("href")
            horse_id, horse_name = self._get_entity_data_from_link(horse_link)

            weight_st_element = row.find_element(
                By.CSS_SELECTOR, "span[data-test-selector='horse-weight-st']"
            )
            weight_lb_element = row.find_element(
                By.CSS_SELECTOR, "span[data-test-selector='horse-weight-lb']"
            )
            horse_weight = f"{weight_st_element.text}-{weight_lb_element.text}"

            horse_age = row.find_element(
                By.CSS_SELECTOR, "td.rp-horseTable__spanNarrow[data-ending='yo']"
            ).text.strip()

            official_rating = row.find_element(
                By.CSS_SELECTOR, "td.rp-horseTable__spanNarrow[data-ending='OR']"
            ).text.strip()
            ts_value = row.find_element(
                By.CSS_SELECTOR, "td.rp-horseTable__spanNarrow[data-ending='TS']"
            ).text.strip()
            rpr_value = row.find_element(
                By.CSS_SELECTOR, "td.rp-horseTable__spanNarrow[data-ending='RPR']"
            ).text.strip()

            horse_price = row.find_element(
                By.CSS_SELECTOR, "span.rp-horseTable__horse__price"
            ).text.strip()

            distnce_beaten_elements = row.find_elements(
                By.CSS_SELECTOR, "span.rp-horseTable__pos__length > span"
            )
            if len(distnce_beaten_elements) == 1:
                total_distance_beaten = distnce_beaten_elements[0].text.strip()
            elif len(distnce_beaten_elements) == 2:
                total_distance_beaten = distnce_beaten_elements[1].text.strip()
            else:
                total_distance_beaten = np.nan

            extra_weights_elements = row.find_elements(
                By.CSS_SELECTOR,
                "span.rp-horseTable__extraData img[data-test-selector='img-extraWeights']",
            )
            if extra_weights_elements:
                extra_weight = (
                    extra_weights_elements[0]
                    .find_element(By.XPATH, "following-sibling::span")
                    .text.strip()
                )
            else:
                extra_weight = np.nan

            headgear_elements = row.find_elements(
                By.CSS_SELECTOR, "span.rp-horseTable__headGear"
            )
            if headgear_elements:
                headgear = headgear_elements[0].text.strip().replace("\n", "")
            else:
                headgear = np.nan

            horse_data.append(
                {
                    "horse_id": horse_id,
                    "horse_name": horse_name,
                    "horse_age": horse_age,
                    "jockey_id": jockey_id,
                    "jockey_name": jockey_name,
                    "jockey_claim": jockey_claim,
                    "trainer_id": trainer_id,
                    "trainer_name": trainer_name,
                    "owner_id": owner_id,
                    "owner_name": owner_name,
                    "horse_weight": horse_weight,
                    "official_rating": official_rating,
                    "finishing_position": horse_position,
                    "total_distance_beaten": total_distance_beaten,
                    "draw": draw,
                    "ts_value": ts_value,
                    "rpr_value": rpr_value,
                    "horse_price": horse_price,
                    "extra_weight": extra_weight,
                    "headgear": headgear,
                }
            )

            order.append((index, horse_name))

        return horse_data, order

    def _get_comment_data(
        self,
        driver: webdriver.Chrome,
        order: list[tuple[int, str]],
        horse_data: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        sorted_horses = sorted(order, key=lambda x: x[0])
        sorted_horse_data = sorted(
            horse_data,
            key=lambda x: next(
                i for i, name in enumerate(sorted_horses) if name[1] == x["horse_name"]
            ),
        )
        comment_rows = driver.find_elements(
            By.CSS_SELECTOR,
            "tr.rp-horseTable__commentRow[data-test-selector='text-comments']",
        )

        if len(sorted_horse_data) != len(comment_rows):
            self.pipeline_status.add_error(
                "Error: The number of horses does not match the number of comment rows."
            )
            return horse_data

        for horse_data, comment_row in zip(sorted_horse_data, comment_rows):
            comment_text = comment_row.find_element(By.TAG_NAME, "td").text.strip()
            horse_data["comment"] = comment_text

        return sorted_horse_data

    def _get_horse_type_data(
        self,
        driver: webdriver.Chrome,
        order: list[tuple[int, str]],
        horse_data: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        sorted_horses = sorted(order, key=lambda x: x[0])
        sorted_horse_data = sorted(
            horse_data,
            key=lambda x: next(
                i for i, name in enumerate(sorted_horses) if name[1] == x["horse_name"]
            ),
        )
        horse_type_rows = driver.find_elements(
            By.CSS_SELECTOR,
            "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']",
        )

        if len(sorted_horse_data) != len(horse_type_rows):
            self.pipeline_status.add_error(
                "Error: The number of horses does not match the number of horse type rows."
            )
            return horse_data

        for horse_data, horse_type_row in zip(sorted_horse_data, horse_type_rows):
            horse_type_raw_text = (
                horse_type_row.find_element(By.TAG_NAME, "td")
                .get_attribute("textContent")
                .strip()
            )
            horse_type_text = horse_type_raw_text.splitlines()[0].strip()
            horse_data["horse_type"] = horse_type_text

        return sorted_horse_data

    def _get_pedigree_data(
        self,
        driver: webdriver.Chrome,
        order: list[tuple[int, str]],
        horse_data: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        sorted_horses = sorted(order, key=lambda x: x[0])
        sorted_horse_data = sorted(
            horse_data,
            key=lambda x: next(
                i for i, name in enumerate(sorted_horses) if name[1] == x["horse_name"]
            ),
        )
        pedigree_rows = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (
                    By.CSS_SELECTOR,
                    "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']",
                )
            )
        )

        if len(sorted_horse_data) != len(pedigree_rows):
            self.pipeline_status.add_error(
                "Number of horses does not match the number of pedigree rows."
            )
            return horse_data

        pedigrees = []
        for row in pedigree_rows:
            pedigree = {}
            profile_links = row.find_elements(By.CSS_SELECTOR, "td > a.ui-profileLink")
            pedigree_hrefs = [link.get_attribute("href") for link in profile_links]
            for i, v in enumerate(pedigree_hrefs):
                if i == 0:
                    pedigree["sire_id"], pedigree["sire"] = (
                        self._get_entity_data_from_link(v)
                    )
                elif i == 1:
                    pedigree["dam_id"], pedigree["dam"] = (
                        self._get_entity_data_from_link(v)
                    )
                elif i == 2:
                    (
                        pedigree["dams_sire_id"],
                        pedigree["dams_sire"],
                    ) = self._get_entity_data_from_link(v)
                else:
                    self.pipeline_status.add_error(
                        f"Error: Unknown pedigree link index: {i}"
                    )
            pedigrees.append(pedigree)

        for horse_data, pedigrees in zip(sorted_horse_data, pedigrees):
            horse_data["sire_name"] = pedigrees["sire"]
            horse_data["sire_id"] = pedigrees["sire_id"]
            if "dam" in pedigrees.keys() and "dam_id" in pedigrees.keys():
                horse_data["dam_name"] = pedigrees["dam"]
                horse_data["dam_id"] = pedigrees["dam_id"]
            else:
                horse_data["dam_name"] = np.nan
                horse_data["dam_id"] = np.nan
            if "dams_sire" in pedigrees.keys() and "dams_sire_id" in pedigrees.keys():
                horse_data["dams_sire"] = pedigrees["dams_sire"]
                horse_data["dams_sire_id"] = pedigrees["dams_sire_id"]
            else:
                horse_data["dams_sire"] = np.nan
                horse_data["dams_sire_id"] = np.nan

        return sorted_horse_data

    def _get_course_country_data(self, driver: webdriver.Chrome):
        course_name = self._return_element_text_from_css(
            driver, "a.rp-raceTimeCourseName__name"
        )
        matches = re.findall(r"\((.*?)\)", course_name)
        if course_name == "Newmarket (July)" and matches == ["July"]:
            return "Turf", "UK", "Newmarket (July)"
        if len(matches) == 2:
            surface, country = matches
            return surface, country, course_name
        elif len(matches) == 1 and matches[0] == "AW":
            return "AW", "UK", course_name
        elif len(matches) == 1:
            return "Turf", matches[0], course_name
        else:
            return "Turf", "UK", course_name

    def _convert_distance_to_float(self, distance_str):
        text_code_to_numeric = {
            "dht": 0,
            "nse": 0.01,
            "shd": 0.1,
            "sht-hd": 0.1,
            "hd": 0.2,
            "sht-nk": 0.3,
            "snk": 0.3,
            "nk": 0.5,
            "dist": 999,
        }
        if pd.isna(distance_str) or not distance_str:
            return 0.0
        clean_str = distance_str.strip("[]")

        if clean_str in text_code_to_numeric:
            return text_code_to_numeric[clean_str]

        if not clean_str:
            return 0.0

        match = re.match(r"(\d+)?(?:\s*)?([½¼¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞])?", clean_str)
        whole_number, fraction = match[1], match[2]

        whole_number_part = float(whole_number) if whole_number else 0.0

        fraction_to_decimal = {
            "½": 0.5,
            "⅓": 0.33,
            "⅔": 0.66,
            "¼": 0.25,
            "¾": 0.75,
            "⅕": 0.2,
            "⅖": 0.4,
            "⅗": 0.6,
            "⅘": 0.8,
            "⅙": 0.167,
            "⅚": 0.833,
            "⅛": 0.125,
            "⅜": 0.375,
            "⅝": 0.625,
            "⅞": 0.875,
        }
        fraction_part = fraction_to_decimal.get(fraction, 0.0)

        return whole_number_part + fraction_part

    def _get_adj_total_distance_beaten(self, df):
        # fmt: off
        if len(df) == 1 and df["finishing_position"].iloc[0] == "1":
            df["adj_total_distance_beaten"] = "WO"
            return df

        if df["total_distance_beaten"].unique().tolist() == [""]:
            df["adj_total_distance_beaten"] = "FOG"
            return df

        if len(df) == 2 and df["finishing_position"].tolist() == ["1", "1"]:
            df["adj_total_distance_beaten"] = "0"
            return df

        if len(df) == 2 and len(df[df["finishing_position"] == "1"]) == 1:
            df["adj_total_distance_beaten"] = np.select(
                [df["finishing_position"] == "1"],
                ["0"],
                df["finishing_position"].astype(str),
            )
            return df

        df = df.assign(
            float_total_distance_beaten=df["total_distance_beaten"].apply(
                self._convert_distance_to_float
            ),
        )
        df = df.assign(
            float_total_distance_beaten=df["float_total_distance_beaten"].round(2)
        )

        second_place = "2"

        if len(df[df["finishing_position"] == "1"]) > 1:
            finishing_positions = df["finishing_position"].unique()
            numeric_finishing_positions = pd.to_numeric(
                finishing_positions, errors="coerce"
            )
            second_place = str(
                numeric_finishing_positions[numeric_finishing_positions > 1].min()
            ).replace(".0", "")

        dsq_df = df[
            (pd.to_numeric(df["finishing_position"], errors="coerce") > 1)
            & (df["total_distance_beaten"] == "")
        ]
        if not dsq_df.empty:
            winning_distance = df[df["finishing_position"] == "1"][
                "float_total_distance_beaten"
            ].iloc[0]
            df["float_total_distance_beaten"] = (
                df["float_total_distance_beaten"] - winning_distance
            )

        df = df.assign(
            adj_total_distance_beaten=np.select(
                [
                    df["finishing_position"].str.contains(r"[A-Za-z]", na=False),
                    (df["finishing_position"] == "0") & (df["total_distance_beaten"] == ""),
                    (df["finishing_position"] != "1") & (df["total_distance_beaten"] == ""),
                    (df["finishing_position"] == "1"),
                ],
                [
                    df["finishing_position"],
                    "UND",
                    "(DSQ)",
                    -df[df["finishing_position"] == second_place]["float_total_distance_beaten"].iloc[0],
                ],
                df["float_total_distance_beaten"],
            )
        ).drop(columns=["float_total_distance_beaten"])
        df = df.assign(
            adj_total_distance_beaten=np.where(
                df["adj_total_distance_beaten"] == "(DSQ)",
                "(DSQ) " + df["finishing_position"],
                df["adj_total_distance_beaten"],
            )
        )
        df["adj_total_distance_beaten"] = df["adj_total_distance_beaten"].astype(str)
        return df

    # fmt: on
