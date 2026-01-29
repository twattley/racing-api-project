import hashlib
import re
from datetime import datetime

import numpy as np
import pandas as pd
import pytz
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from ...data_types.pipeline_status import PipelineStatus
from ...raw.interfaces.data_scraper_interface import IDataScraper


class RPResultsDataScraper(IDataScraper):
    def __init__(self, pipeline_status: PipelineStatus) -> None:
        self.pipeline_status = pipeline_status
        self.pedigree_settings_button_toggled = False

    def scrape_data(self, page: Page, url: str) -> pd.DataFrame:
        self._wait_for_page_load(page, url)

        self._toggle_button(page)

        created_at = datetime.now(pytz.timezone("Europe/London")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        *_, course_id, course, race_date, race_id = url.split("/")
        surface, country, course_name = self._get_course_country_data(page)
        race_time = self._return_element_text_from_css(
            page,
            "span.rp-raceTimeCourseName__time[data-test-selector='text-raceTime']",
        )
        race_title = self._return_element_text_from_css(
            page, "h2.rp-raceTimeCourseName__title"
        )
        conditions = self._get_optional_element_text(
            page, "span.rp-raceTimeCourseName_ratingBandAndAgesAllowed"
        )
        race_class = self._get_optional_element_text(
            page, "span.rp-raceTimeCourseName_class"
        )
        distance = self._return_element_text_from_css(
            page, "span.rp-raceTimeCourseName_distance"
        )
        distance_full = self._get_optional_element_text(
            page, "span.rp-raceTimeCourseName_distanceFull"
        )
        going = self._return_element_text_from_css(
            page, "span.rp-raceTimeCourseName_condition"
        )
        winning_time = self._get_raw_winning_time(page)
        number_of_runners = self._get_number_of_runners(page)
        try:
            total_prize_money, first_place_prize_money, currency = (
                self._get_prize_money(page)
            )
        except Exception:
            total_prize_money, first_place_prize_money, currency = (
                np.nan,
                np.nan,
                np.nan,
            )

        performance_data, order = self._get_performance_data(page)
        performance_data = self._get_comment_data(page, order, performance_data)
        performance_data = self._get_horse_type_data(page, order, performance_data)
        performance_data = self._get_pedigree_data(page, order, performance_data)
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
            rp_comment="no comment available",
        )

        # Get RP analysis comments and merge with horse data
        rp_comments = self._get_rp_analysis_comments(page, url)

        for horse_id, comment in rp_comments.items():
            performance_data.loc[
                performance_data["horse_id"] == horse_id, "rp_comment"
            ] = comment.strip()

        performance_data = performance_data.pipe(self._get_adj_total_distance_beaten)

        performance_data = performance_data.apply(
            lambda x: x.str.strip() if x.dtype == "object" else x
        )

        performance_data = performance_data.dropna(subset=["race_time"])
        if performance_data.empty:
            self.pipeline_status.add_error(
                f"No data for {url} failure to scrape timestamp"
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

    def _toggle_button(self, page: Page):
        if self.pedigree_settings_button_toggled:
            self.pipeline_status.add_debug("Pedigree button already toggled, skipping")
            return

        self.pipeline_status.add_debug("Starting _toggle_button")

        try:
            # Try to close any popup
            close_btn = page.locator(
                "button.ab-close-button[aria-label='Close Message']"
            )
            if close_btn.count() > 0 and close_btn.is_visible(timeout=5000):
                close_btn.click()
                self.pipeline_status.add_debug("Closed popup")
        except Exception:
            pass

        self.pipeline_status.add_debug("Looking for pedigree button")
        # Use .first because there can be multiple pedigree buttons on the page
        pedigree_button = page.locator('[data-test-selector="button-pedigree"]').first
        pedigree_button.wait_for(state="visible", timeout=10000)
        self.pipeline_status.add_debug("Pedigree button visible")
        pedigree_button.scroll_into_view_if_needed()
        self.pipeline_status.add_debug("Scrolled to pedigree button")
        page.wait_for_timeout(3000)
        pedigree_button.click()
        self.pipeline_status.add_debug("Clicked pedigree button")
        self.pedigree_settings_button_toggled = True

        # Wait for pedigree elements to appear after clicking
        self.pipeline_status.add_debug("Waiting for pedigree elements to appear")
        try:
            page.wait_for_selector(
                "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']",
                timeout=10000,
            )
            self.pipeline_status.add_debug("Found pedigree rows")
            page.wait_for_selector("tr.rp-horseTable__pedigreeRow td", timeout=10000)
            self.pipeline_status.add_debug("Found pedigree data cells")
        except PlaywrightTimeoutError:
            self.pipeline_status.add_error(
                "Pedigree elements did not appear after toggle"
            )
            raise ValueError(
                "Pedigree elements did not appear after clicking toggle button"
            )

    def _wait_for_page_load(self, page: Page, url: str) -> None:
        """
        Wait for basic page elements that should be present on load.
        Note: Pedigree elements are NOT checked here - they only appear after
        clicking the toggle button in _toggle_button().
        """
        self.pipeline_status.add_debug("Starting _wait_for_page_load")

        # Elements that just need to be present (NOT pedigree - that comes after toggle)
        presence_elements = [
            (".rp-raceInfo", "Race Info"),
            ("div[data-test-selector='text-prizeMoney']", "Prize Money"),
            (
                "tr.rp-horseTable__commentRow[data-test-selector='text-comments']",
                "Comments",
            ),
            ("a.rp-raceTimeCourseName__name", "Course Name"),
            (
                "span.rp-raceTimeCourseName__time[data-test-selector='text-raceTime']",
                "Race Time",
            ),
            ("h2.rp-raceTimeCourseName__title", "Race Title"),
            ("span.rp-raceTimeCourseName_distance", "Distance"),
            ("span.rp-raceTimeCourseName_condition", "Going"),
        ]

        # Elements that need to be clickable
        clickable_elements = [
            ("[data-test-selector='button-pedigree']", "Pedigree Button"),
        ]

        missing_elements = []

        # Check presence elements
        for selector, name in presence_elements:
            try:
                self.pipeline_status.add_debug(f"Waiting for element: {name}")
                page.wait_for_selector(selector, timeout=10000)
                self.pipeline_status.add_debug(f"Found element: {name}")
            except PlaywrightTimeoutError:
                self.pipeline_status.add_error(f"Missing element: {name} - URL - {url}")
                missing_elements.append(name)

        # Check clickable elements - use .first to handle duplicates
        for selector, name in clickable_elements:
            try:
                self.pipeline_status.add_debug(f"Waiting for clickable: {name}")
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=10000)
                self.pipeline_status.add_debug(f"Found clickable: {name}")
            except PlaywrightTimeoutError:
                self.pipeline_status.add_error(f"Element not clickable: {name}")
                missing_elements.append(name)

        if missing_elements:
            self.pipeline_status.add_error(
                f"Element Missing elements: {', '.join(missing_elements)}, URL - {url}"
            )
            self.pipeline_status.add_info(
                f"[ERROR] Missing elements: {', '.join(missing_elements)}, URL - {url}"
            )

        self.pipeline_status.add_debug("_wait_for_page_load completed successfully")

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

    def _get_rp_analysis_comments(self, page: Page, results_url: str) -> dict[str, str]:
        """
        Scrape RP analysis comments from the /analysis page.

        Returns a dict mapping horse_id -> comment text.
        """
        analysis_url = f"{results_url}/analysis"

        try:
            self.pipeline_status.add_debug(
                f"Navigating to analysis page: {analysis_url}"
            )
            # Navigate to analysis page - use domcontentloaded as networkidle can hang
            # on pages with continuous analytics/ad requests
            page.goto(analysis_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for the analysis container to be present (this is the key wait)
            try:
                page.wait_for_selector(
                    "div.rp-analysis[data-test-selector='block-analysis']",
                    timeout=15000,
                )
            except PlaywrightTimeoutError:
                self.pipeline_status.add_debug(
                    f"No analysis block found for {analysis_url}"
                )
                return {}

            # Find the analysis copy container
            analysis_container = page.locator("div.rp-analysis__copy")
            if analysis_container.count() == 0:
                self.pipeline_status.add_debug(
                    f"No analysis copy container found for {analysis_url}"
                )
                return {}

            # Get all comment blocks
            comment_blocks = page.locator("p.rp-analysis__copy__block").all()
            self.pipeline_status.add_debug(
                f"Found {len(comment_blocks)} comment blocks"
            )

            horse_comments = {}

            for idx, block in enumerate(comment_blocks):
                # Look for horse link in this block
                horse_link = block.locator("a[href*='/profile/horse/']")

                if horse_link.count() > 0:
                    href = horse_link.first.get_attribute("href")
                    self.pipeline_status.add_debug(
                        f"Block {idx}: Found horse link: {href}"
                    )
                    if href:
                        # Extract horse_id from link like /profile/horse/6229186/westcombe
                        parts = href.split("/")
                        horse_idx = parts.index("horse") if "horse" in parts else -1
                        if horse_idx >= 0 and horse_idx + 1 < len(parts):
                            horse_id = parts[horse_idx + 1]

                            # Get the full text of the block and clean it
                            comment_text = block.text_content().strip()

                            # Remove the horse name at the start (it's in bold/strong)
                            # Use .first because a block can mention multiple horses
                            horse_name_locator = block.locator(
                                "span.rp-analysis__copy__strong"
                            )
                            if horse_name_locator.count() > 0:
                                horse_name = (
                                    horse_name_locator.first.text_content().strip()
                                )
                                # Remove horse name from start of comment
                                if comment_text.startswith(horse_name):
                                    comment_text = comment_text[
                                        len(horse_name) :
                                    ].strip()
                                    # Remove leading comma if present
                                    if comment_text.startswith(","):
                                        comment_text = comment_text[1:].strip()

                            horse_comments[horse_id] = comment_text
                            self.pipeline_status.add_debug(
                                f"Extracted comment for horse {horse_id}: {comment_text[:50]}..."
                            )
                            print(
                                f"Extracted comment for horse {horse_id}: {comment_text[:50]}..."
                            )
                else:
                    block_text = block.text_content().strip()[:50]
                    self.pipeline_status.add_debug(
                        f"Block {idx}: No horse link, text: {block_text}"
                    )

            self.pipeline_status.add_debug(
                f"Found {len(horse_comments)} RP analysis comments"
            )

            return horse_comments

        except Exception as e:
            self.pipeline_status.add_warning(
                f"Failed to get RP analysis comments from {analysis_url}: {e}"
            )
            return {}

    def _return_element_text_from_css(self, page: Page, selector: str) -> str:
        return page.locator(selector).text_content().strip()

    def _get_optional_element_text(self, page: Page, css_selector: str):
        try:
            locator = page.locator(css_selector)
            if locator.count() > 0:
                return locator.first.text_content().strip()
            return None
        except Exception:
            return None

    def _get_raw_winning_time(self, page: Page):
        try:
            # Find the li element containing "Winning time:" and extract the value
            li_elements = page.locator(".rp-raceInfo li").all()
            for li in li_elements:
                text = li.text_content()
                if "winning time:" in text.lower():
                    # Extract the text between "Winning time:" and "Total SP:"
                    parts = text.lower().split("winning time:")
                    if len(parts) > 1:
                        after_winning = parts[1]
                        # Get everything before "total sp:" if it exists
                        if "total sp:" in after_winning:
                            winning_time = after_winning.split("total sp:")[0].strip()
                        else:
                            winning_time = after_winning.strip()
                        # Collapse multiple spaces into single space
                        return " ".join(winning_time.split())
            return np.nan
        except Exception:
            return np.nan

    def _get_number_of_runners(self, page: Page) -> str:
        try:
            # Target the span with black styling that contains "X ran"
            runners_span = page.locator(
                "span.rp-raceInfo__value.rp-raceInfo__value_black"
            )
            if runners_span.count() > 0:
                text = runners_span.first.text_content().strip()
                # Extract just the number from "10 ran"
                if "ran" in text.lower():
                    return text.lower().split("ran")[0].strip()
            return np.nan
        except Exception:
            return np.nan

    def _get_prize_money(self, page: Page) -> tuple[int, int, str]:
        prize_money_container = page.locator(
            "div[data-test-selector='text-prizeMoney']"
        )
        prize_money_text = prize_money_container.text_content()

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
        page: Page,
    ) -> tuple[list[dict[str, str]], list[tuple[int, str]]]:
        horse_data = []

        order = []

        rows = page.locator(
            "tr.rp-horseTable__mainRow[data-test-selector='table-row']"
        ).all()

        for index, row in enumerate(rows):
            horse_position = (
                row.locator(
                    "span.rp-horseTable__pos__number[data-test-selector='text-horsePosition']"
                )
                .text_content()
                .strip()
            )

            if "(" in horse_position:
                draw = horse_position.split("(")[1].replace(")", "").strip()
                horse_position = horse_position.split("(")[0].strip()
            else:
                draw = np.nan

            try:
                jockey_element = row.locator("a[href*='/profile/jockey']")
                jockey_link = jockey_element.first.get_attribute("href")
                jockey_id, jockey_name = self._get_entity_data_from_link(jockey_link)
            except Exception:
                jockey_id, jockey_name = np.nan, np.nan

            try:
                owner_element = row.locator("a[href*='/profile/owner']")
                owner_link = owner_element.first.get_attribute("href")
                owner_id, owner_name = self._get_entity_data_from_link(owner_link)
            except Exception:
                owner_id, owner_name = np.nan, np.nan

            # Get jockey claim from sibling sup element
            try:
                sup_elements = row.locator("a[href*='/profile/jockey'] + sup").all()
                if sup_elements:
                    jockey_claim = sup_elements[0].text_content().strip()
                else:
                    jockey_claim = np.nan
            except Exception:
                jockey_claim = np.nan

            try:
                trainer_element = row.locator("a[href*='/profile/trainer']")
                trainer_link = trainer_element.first.get_attribute("href")
                trainer_id, trainer_name = self._get_entity_data_from_link(trainer_link)
            except Exception:
                trainer_id, trainer_name = np.nan, np.nan

            horse_element = row.locator("a[href*='/profile/horse']")
            horse_link = horse_element.first.get_attribute("href")
            horse_id, horse_name = self._get_entity_data_from_link(horse_link)

            weight_st_element = row.locator(
                "span[data-test-selector='horse-weight-st']"
            )
            weight_lb_element = row.locator(
                "span[data-test-selector='horse-weight-lb']"
            )
            horse_weight = (
                f"{weight_st_element.text_content()}-{weight_lb_element.text_content()}"
            )

            horse_age = (
                row.locator("td.rp-horseTable__spanNarrow[data-ending='yo']")
                .text_content()
                .strip()
            )

            official_rating = (
                row.locator("td.rp-horseTable__spanNarrow[data-ending='OR']")
                .text_content()
                .strip()
            )
            ts_value = (
                row.locator("td.rp-horseTable__spanNarrow[data-ending='TS']")
                .text_content()
                .strip()
            )
            rpr_value = (
                row.locator("td.rp-horseTable__spanNarrow[data-ending='RPR']")
                .text_content()
                .strip()
            )

            horse_price = (
                row.locator("span.rp-horseTable__horse__price").text_content().strip()
            )

            distnce_beaten_elements = row.locator(
                "span.rp-horseTable__pos__length > span"
            ).all()
            if len(distnce_beaten_elements) == 1:
                total_distance_beaten = (
                    distnce_beaten_elements[0].text_content().strip()
                )
            elif len(distnce_beaten_elements) == 2:
                total_distance_beaten = (
                    distnce_beaten_elements[1].text_content().strip()
                )
            else:
                total_distance_beaten = np.nan

            extra_weights_elements = row.locator(
                "span.rp-horseTable__extraData img[data-test-selector='img-extraWeights']"
            ).all()
            if extra_weights_elements:
                extra_weight = (
                    row.locator(
                        "span.rp-horseTable__extraData img[data-test-selector='img-extraWeights'] + span"
                    )
                    .text_content()
                    .strip()
                )
            else:
                extra_weight = np.nan

            headgear_elements = row.locator("span.rp-horseTable__headGear").all()
            if headgear_elements:
                headgear = headgear_elements[0].text_content().strip().replace("\n", "")
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
        page: Page,
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
        comment_rows = page.locator(
            "tr.rp-horseTable__commentRow[data-test-selector='text-comments']"
        ).all()

        if len(sorted_horse_data) != len(comment_rows):
            self.pipeline_status.add_error(
                "Error: The number of horses does not match the number of comment rows."
            )
            return horse_data

        for horse_data, comment_row in zip(sorted_horse_data, comment_rows):
            comment_text = comment_row.locator("td").text_content().strip()
            horse_data["comment"] = comment_text

        return sorted_horse_data

    def _get_horse_type_data(
        self,
        page: Page,
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
        horse_type_rows = page.locator(
            "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']"
        ).all()

        if len(sorted_horse_data) != len(horse_type_rows):
            self.pipeline_status.add_error(
                "Error: The number of horses does not match the number of horse type rows."
            )
            return horse_data

        for horse_data, horse_type_row in zip(sorted_horse_data, horse_type_rows):
            horse_type_raw_text = (
                horse_type_row.locator("td").first.text_content().strip()
            )
            horse_type_text = horse_type_raw_text.splitlines()[0].strip()
            horse_data["horse_type"] = horse_type_text

        return sorted_horse_data

    def _get_pedigree_data(
        self,
        page: Page,
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

        page.wait_for_selector(
            "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']",
            timeout=10000,
        )
        pedigree_rows = page.locator(
            "tr.rp-horseTable__pedigreeRow[data-test-selector='block-pedigreeInfoFullResults']"
        ).all()

        if len(sorted_horse_data) != len(pedigree_rows):
            self.pipeline_status.add_error(
                "Number of horses does not match the number of pedigree rows."
            )
            return horse_data

        pedigrees = []
        for row in pedigree_rows:
            pedigree = {}
            profile_links = row.locator("td > a.ui-profileLink").all()
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

    def _get_course_country_data(self, page: Page):
        course_name = self._return_element_text_from_css(
            page, "a.rp-raceTimeCourseName__name"
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
