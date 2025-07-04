import hashlib
import time
from datetime import datetime

import pandas as pd
from api_helpers.config import Config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ...data_types.pipeline_status import PipelineStatus

from ...raw.interfaces.data_scraper_interface import IDataScraper
from ...raw.webdriver.web_driver import WebDriver


class RPRacecardsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus) -> None:
        self.pipeline_status = pipeline_status
        self.pedigree_owner_settings_button_toggled = False

    def scrape_data(self, driver: webdriver.Chrome, url: str) -> pd.DataFrame:
        self._toggle_buttons(driver)
        race_data = self._get_data_from_url(url)
        race_time = self._get_race_time(driver)
        header_data = self._get_race_details(driver)
        horse_data = self._get_horse_data(driver)
        horse_data = horse_data.assign(
            **race_data,
            **race_time,
            **header_data,
            race_time_debug=None,
            horse_price=None,
            finishing_position=None,
            rpr_value=None,
            debug_link=url,
            total_distance_beaten=None,
            ts_value=None,
            total_prize_money=None,
            currency=None,
            winning_time=None,
            dams_sire_id=None,
            extra_weight=None,
            dams_sire=None,
            comment=None,
            country="UK",
            created_at=datetime.now(),
            adj_total_distance_beaten=None,
        )

        horse_data = horse_data.assign(
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
        ).drop(columns=["distance_yards"])

        self._perform_basic_data_validation(horse_data)

        return horse_data

    def _perform_basic_data_validation(self, data: pd.DataFrame) -> None:
        if not data["horse_weight"].isna().sum() == 0:
            self.pipeline_status.add_error(
                "Horse weight data is missing or contains NaN values"
            )
        if not data["horse_age"].isna().sum() == 0:
            self.pipeline_status.add_error(
                "Horse age data is missing or contains NaN values"
            )
            raise ValueError("Horse age data is missing or contains NaN values")

    def _toggle_buttons(self, driver):
        try:
            if self.pedigree_owner_settings_button_toggled:
                self.pipeline_status.add_debug("Settings already toggled")
                return
            else:
                self.pipeline_status.add_debug("Toggling settings button")
                settings_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            ".RC-cardTabsZone__settingsBtn.js-RC-settingsPopover__openBtn",
                        )
                    )
                )
                driver.execute_script("arguments[0].click();", settings_button)
                time.sleep(2)

                pedigree_switcher = driver.find_element(
                    By.ID, "RC-customizeSettings__switcher_pedigrees"
                )
                owner_switcher = driver.find_element(
                    By.ID, "RC-customizeSettings__switcher_owner"
                )
                done_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "[data-test-selector='RC-customizeSettings__popoverBtn']",
                )
                time.sleep(2)

                driver.execute_script("arguments[0].click();", pedigree_switcher)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", owner_switcher)
                time.sleep(2)
                driver.execute_script("arguments[0].click();", done_button)
                self.pedigree_owner_settings_button_toggled = True
        except Exception as e:
            self.pipeline_status.add_error(f"Error toggling settings button: {str(e)}")

    def _get_data_from_url(self, url: str) -> dict:
        if url.endswith("/"):
            url = url[:-1]
        *_, course_id, course, race_date, race_id = url.split("/")
        course = course.replace("-", " ").title().strip()
        return {
            "course_id": course_id,
            "course_name": course,
            "course": course,
            "race_date": datetime.strptime(race_date, "%Y-%m-%d"),
            "race_id": race_id,
        }

    def _get_race_time(self, driver: webdriver.Chrome) -> datetime:
        element = driver.find_element(
            By.XPATH,
            "//span[@class='RC-courseHeader__time'][@data-test-selector='RC-courseHeader__time']",
        )
        time = element.text.strip()
        hours, minutes = time.split(":")
        hours = int(hours)
        if hours < 10:
            hours += 12
        return {
            "race_time": datetime.strptime(
                f"{datetime.now().strftime('%Y-%m-%d')} {hours}:{minutes}",
                "%Y-%m-%d %H:%M",
            )
        }

    def _get_surface(self, driver: webdriver.Chrome) -> str:
        course_name_element = driver.find_element(
            By.CLASS_NAME, "RC-courseHeader__name"
        )
        course_name_text = course_name_element.text.strip()
        return "AW" if "AW" in course_name_text else "Turf"

    def _get_race_details(self, driver: webdriver.Chrome) -> dict:
        header_map = {
            "RC-header__raceDistanceRound": "distance",
            "RC-header__raceDistance": "distance_full",
            "RC-header__raceInstanceTitle": "race_title",
            "RC-header__raceClass": "race_class",
            "RC-header__rpAges": "conditions",
            "RC-ticker__winner": "first_place_prize_money",
            "RC-headerBox__winner": "first_place_prize_money",
            "RC-headerBox__runners": "number_of_runners",
            "RC-headerBox__going": "going",
        }
        parent_divs = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'RC-cardHeader__courseDetails') or contains(@class, 'RC-cardHeader__keyInfo')]",
        )

        header_data = {}
        for div in parent_divs:
            child_elements = div.find_elements(By.XPATH, ".//*[@data-test-selector]")
            for element in child_elements:
                test_selector = element.get_attribute("data-test-selector")
                text = element.get_attribute("textContent").strip()
                if test_selector in header_map:
                    header_data[header_map[test_selector]] = text

        header_data["going"] = header_data.get("going", "").replace("Going: ", "")
        header_data["distance_yards"] = (
            header_data.get("distance_yards", "")
            .replace("yds", "")
            .replace("(", "")
            .replace(")", "")
        )
        if "places" in header_data:
            header_data.pop("places", None)

        header_data["number_of_runners"] = (
            header_data["number_of_runners"]
            .replace("Runners:", "")
            .replace("\n", "")
            .strip()
            .split(" ")[0]
        )
        header_data["going"] = (
            header_data["going"].replace("Going:", "").replace("\n", "").strip()
        )
        header_data["surface"] = self._get_surface(driver)
        prize_money = (
            header_data["first_place_prize_money"].replace("Winner:\n", "").strip()
        )
        prize_money = (
            round(
                int(prize_money.replace(",", "").replace("€", "").replace("£", "")), -3
            )
            // 1000
        )

        header_data["first_place_prize_money"] = prize_money

        return header_data

    def _get_entity_data_from_link(self, entity_link: str) -> tuple[str, str]:
        entity_id, entity_name = entity_link.split("/")[-2:]
        entity_name = " ".join(i.title() for i in entity_name.split("-"))
        return entity_id, entity_name

    def _get_optional_element_text(
        self, row: webdriver.Chrome, css_selector: str
    ) -> str | None:
        try:
            return row.find_element(By.CSS_SELECTOR, css_selector).text.strip()
        except Exception:
            return None

    def _clean_entity_name(self, entity_name: str) -> str:
        return entity_name.replace("-", " ").title().strip()

    def _get_horse_data(self, driver: webdriver.Chrome) -> pd.DataFrame:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".RC-runnerRow.js-RC-runnerRow.js-PC-runnerRow")
            )
        )
        runner_rows = driver.find_elements(
            By.CSS_SELECTOR, ".RC-runnerRow.js-RC-runnerRow.js-PC-runnerRow"
        )
        horse_data = []
        for row in runner_rows:
            horse = row.find_element(By.CSS_SELECTOR, "a.RC-runnerName")
            runner_no = row.find_element(
                By.CSS_SELECTOR, "[data-test-selector='RC-cardPage-runnerNumber-no']"
            ).text.strip()
            if "NR" in runner_no:
                self.pipeline_status.add_debug(
                    f"Runner {horse.text.strip()} is a non-runner"
                )
                continue
            if "R" in runner_no:
                self.pipeline_status.add_debug(
                    f"Runner {horse.text.strip()} is a reserve"
                )
                continue
            color_sex = row.find_element(
                By.CSS_SELECTOR, "span[data-test-selector='RC-pedigree__color-sex']"
            )
            sire_link_element = row.find_element(
                By.CSS_SELECTOR, "a[data-test-selector='RC-pedigree__sire']"
            )
            dam_link_element = row.find_element(
                By.CSS_SELECTOR, "a[data-test-selector='RC-pedigree__dam']"
            )
            jockey_element = row.find_elements(
                By.CSS_SELECTOR, "a[data-test-selector='RC-cardPage-runnerJockey-name']"
            )
            trainer_link_element = row.find_element(
                By.CSS_SELECTOR,
                "a[data-test-selector='RC-cardPage-runnerTrainer-name']",
            )
            owner_link_element = row.find_element(
                By.CSS_SELECTOR, "a[data-test-selector='RC-cardPage-runnerOwner-name']"
            )
            horse_href = horse.get_attribute("href")
            horse_id = horse_href.split("/")[5].strip()
            horse_name = horse_href.split("/")[6].strip().split("#")[0]
            sire_href = sire_link_element.get_attribute("href")
            sire_name, sire_id = sire_href.split("/")[-1], sire_href.split("/")[-2]
            dam_href = dam_link_element.get_attribute("href")
            dam_name, dam_id = dam_href.split("/")[-1], dam_href.split("/")[-2]
            owner_href = owner_link_element.get_attribute("href")
            owner_name, owner_id = owner_href.split("/")[-1], owner_href.split("/")[-2]
            jockey_href = jockey_element[0].get_attribute("href")
            jockey_name, jockey_id = (
                jockey_href.split("/")[-1],
                jockey_href.split("/")[-2],
            )
            trainer_href = trainer_link_element.get_attribute("href")
            trainer_name, trainer_id = (
                trainer_href.split("/")[-1],
                trainer_href.split("/")[-2],
            )
            headgear = self._get_optional_element_text(row, ".RC-runnerHeadgearCode")
            age = self._get_optional_element_text(row, ".RC-runnerAge")
            weight_carried_st = self._get_optional_element_text(
                row, ".RC-runnerWgt__carried_st"
            )
            weight_carried_lb = self._get_optional_element_text(
                row, ".RC-runnerWgt__carried_lb"
            )
            weight_carried = f"{weight_carried_st}-{weight_carried_lb}"
            jockey_claim = self._get_optional_element_text(
                row,
                "span.RC-runnerInfo__count[data-test-selector='RC-cardPage-runnerJockey-allowance']",
            )
            draw = self._get_optional_element_text(
                row,
                "span.RC-runnerNumber__draw[data-test-selector='RC-cardPage-runnerNumber-draw']",
            )
            official_rating_element = row.find_element(
                By.CSS_SELECTOR,
                ".RC-runnerOr[data-test-selector='RC-cardPage-runnerOr']",
            )
            official_rating = (
                official_rating_element.text.strip()
                if official_rating_element
                else None
            )
            if draw is not None:
                draw = draw.replace("(", "").replace(")", "").strip()
            else:
                draw = None

            horse_data.append(
                {
                    "horse_name": self._clean_entity_name(horse_name),
                    "horse_id": horse_id,
                    "horse_type": color_sex.text.strip(),
                    "sire_name": self._clean_entity_name(sire_name),
                    "sire_id": sire_id,
                    "dam_name": self._clean_entity_name(dam_name),
                    "dam_id": dam_id,
                    "owner_name": self._clean_entity_name(owner_name),
                    "owner_id": owner_id,
                    "jockey_name": self._clean_entity_name(jockey_name),
                    "jockey_id": jockey_id,
                    "trainer_name": self._clean_entity_name(trainer_name),
                    "trainer_id": trainer_id,
                    "headgear": headgear.strip() if headgear else None,
                    "horse_age": age.strip() if age else None,
                    "horse_weight": weight_carried.strip() if weight_carried else None,
                    "jockey_claim": jockey_claim.strip() if jockey_claim else None,
                    "draw": draw,
                    "official_rating": official_rating,
                }
            )
        data = pd.DataFrame(horse_data)

        self.pipeline_status.add_info(
            f"Scraped {len(data)} RP horses data successfully"
        )
        return data
