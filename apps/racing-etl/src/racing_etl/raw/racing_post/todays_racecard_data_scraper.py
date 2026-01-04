import hashlib
from datetime import datetime

import pandas as pd
from playwright.sync_api import Page

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper


class RPRacecardsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus) -> None:
        self.pipeline_status = pipeline_status
        self.pedigree_owner_settings_button_toggled = False

    def scrape_data(self, page: Page, url: str) -> pd.DataFrame:
        self._toggle_buttons(page)
        race_data = self._get_data_from_url(url)
        race_time = self._get_race_time(page)
        header_data = self._get_race_details(page)
        horse_data = self._get_horse_data(page)
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

    def _toggle_buttons(self, page: Page):
        try:
            if self.pedigree_owner_settings_button_toggled:
                self.pipeline_status.add_debug("Settings already toggled")
                return
            else:
                self.pipeline_status.add_debug("Toggling settings button")
                settings_button = page.locator(
                    ".RC-cardTabsZone__settingsBtn.js-RC-settingsPopover__openBtn"
                )
                settings_button.wait_for(state="visible", timeout=10000)
                # Use JavaScript click to avoid interception issues
                settings_button.evaluate("el => el.click()")
                page.wait_for_timeout(2000)

                pedigree_switcher = page.locator(
                    "#RC-customizeSettings__switcher_pedigrees"
                )
                owner_switcher = page.locator("#RC-customizeSettings__switcher_owner")
                done_button = page.locator(
                    "[data-test-selector='RC-customizeSettings__popoverBtn']"
                )
                page.wait_for_timeout(2000)

                # Use JavaScript click to bypass label interception
                pedigree_switcher.evaluate("el => el.click()")
                page.wait_for_timeout(2000)
                owner_switcher.evaluate("el => el.click()")
                page.wait_for_timeout(2000)
                done_button.evaluate("el => el.click()")
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

    def _get_race_time(self, page: Page) -> datetime:
        element = page.locator(
            "span.RC-courseHeader__time[data-test-selector='RC-courseHeader__time']"
        )
        time_text = element.text_content().strip()
        hours, minutes = time_text.split(":")
        hours = int(hours)
        if hours < 10:
            hours += 12
        return {
            "race_time": datetime.strptime(
                f"{datetime.now().strftime('%Y-%m-%d')} {hours}:{minutes}",
                "%Y-%m-%d %H:%M",
            )
        }

    def _get_surface(self, page: Page) -> str:
        course_name_element = page.locator(".RC-courseHeader__name")
        course_name_text = course_name_element.text_content().strip()
        return "AW" if "AW" in course_name_text else "Turf"

    def _get_race_details(self, page: Page) -> dict:
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

        # Get all elements with data-test-selector within the header divs
        header_data = {}
        for selector, field_name in header_map.items():
            try:
                element = page.locator(f"[data-test-selector='{selector}']").first
                if element.count() > 0:
                    text = element.text_content().strip()
                    header_data[field_name] = text
            except Exception:
                continue

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
        header_data["surface"] = self._get_surface(page)
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

    def _get_optional_element_text(self, row, css_selector: str) -> str | None:
        try:
            element = row.locator(css_selector).first
            if element.count() > 0:
                return element.text_content().strip()
            return None
        except Exception:
            return None

    def _clean_entity_name(self, entity_name: str) -> str:
        return entity_name.replace("-", " ").title().strip()

    def _get_horse_data(self, page: Page) -> pd.DataFrame:
        page.wait_for_selector(
            ".RC-runnerRow.js-RC-runnerRow.js-PC-runnerRow", timeout=10000
        )
        runner_rows = page.locator(
            ".RC-runnerRow.js-RC-runnerRow.js-PC-runnerRow"
        ).all()

        horse_data = []
        for row in runner_rows:
            horse = row.locator("a.RC-runnerName")
            runner_no = (
                row.locator("[data-test-selector='RC-cardPage-runnerNumber-no']")
                .text_content()
                .strip()
            )

            if "NR" in runner_no:
                self.pipeline_status.add_debug(
                    f"Runner {horse.text_content().strip()} is a non-runner"
                )
                continue
            if "R" in runner_no:
                self.pipeline_status.add_debug(
                    f"Runner {horse.text_content().strip()} is a reserve"
                )
                continue

            color_sex = row.locator("span[data-test-selector='RC-pedigree__color-sex']")
            sire_link_element = row.locator("a[data-test-selector='RC-pedigree__sire']")
            dam_link_element = row.locator("a[data-test-selector='RC-pedigree__dam']")
            jockey_element = row.locator(
                "a[data-test-selector='RC-cardPage-runnerJockey-name']"
            )
            trainer_link_element = row.locator(
                "a[data-test-selector='RC-cardPage-runnerTrainer-name']"
            )
            owner_link_element = row.locator(
                "a[data-test-selector='RC-cardPage-runnerOwner-name']"
            )

            horse_href = horse.get_attribute("href")
            horse_id = horse_href.split("/")[3].strip()
            horse_name = horse.text_content().strip().split("\n")[0].strip()

            sire_href = sire_link_element.get_attribute("href")
            sire_name, sire_id = sire_href.split("/")[-1], sire_href.split("/")[-2]

            dam_href = dam_link_element.get_attribute("href")
            dam_name, dam_id = dam_href.split("/")[-1], dam_href.split("/")[-2]

            owner_href = owner_link_element.get_attribute("href")
            owner_name, owner_id = owner_href.split("/")[-1], owner_href.split("/")[-2]

            jockey_href = jockey_element.first.get_attribute("href")
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
            official_rating_element = row.locator(
                ".RC-runnerOr[data-test-selector='RC-cardPage-runnerOr']"
            )
            official_rating = (
                official_rating_element.text_content().strip()
                if official_rating_element.count() > 0
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
                    "horse_type": color_sex.text_content().strip(),
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

        self.pipeline_status.add_debug(
            f"Scraped {len(data)} RP horses data successfully"
        )
        return data
