import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Literal

import pandas as pd
from api_helpers.clients import get_postgres_client
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ...llm_models.chat_models import ChatModels
from ...raw.interfaces.data_scraper_interface import IDataScraper


class RPCommentDataScraper(IDataScraper):
    MIN_DATE = "2015-01-01"
    MAX_DATE = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")

    def __init__(
        self,
        chat_model: ChatModels,
        storage_client: IStorageClient,
        table_name: Literal["results_data", "results_data_world"],
    ) -> None:
        self.chat_model = chat_model
        self.storage_client = storage_client
        self.table_name = table_name

    def scrape_data(self) -> pd.DataFrame:
        links = self.fetch_data(self.table_name)
        num_rows = len(links)

        for i in range(num_rows):
            I(f"Iteration {i + 1} of {num_rows}")
            try:
                I(f"Processing row {i + 1} of {num_rows}")
                analysis_link, debug_link = self._get_sample_links(links)
                race_id, race_date, horse_ids = self._get_race_data(debug_link)
                self._chrome_get_content(analysis_link, load_time=3)
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                raw_text = self._format_raw_text(result.stdout)
                if (
                    raw_text == "No analysis available for this race"
                    or raw_text == "Awaiting analysis"
                ):
                    rp_comment = (
                        "no comment available"
                        if raw_text == "No analysis available for this race"
                        else None
                    )
                    comment_data = pd.DataFrame(horse_ids)
                    comment_data = comment_data.assign(
                        rp_comment=rp_comment,
                    )
                else:
                    model_result = self.chat_model.run_model(raw_text, horse_ids)
                    comment_data = self.convert_model_result_to_df(model_result)

                comment_data = comment_data.assign(
                    race_id=race_id,
                    race_date=race_date,
                )
                self.store_comments(comment_data)

            except KeyboardInterrupt:
                self.update_comments()
                sys.exit()
            except Exception as e:
                self.store_errors(
                    analysis_link, debug_link, race_id, race_date, horse_ids
                )
                E(e)
                E(f"Link: {debug_link}, Analysis link {analysis_link}, {e}")
                continue

        self.update_comments()

    def store_errors(
        self,
        analysis_link: str,
        debug_link: str,
        race_id: str,
        race_date: str,
        horse_ids: list[dict[str, str]],
    ) -> None:
        error_data = pd.DataFrame(horse_ids)
        error_data = error_data.assign(
            analysis_link=analysis_link,
            debug_link=debug_link,
            race_id=race_id,
            race_date=race_date,
        )
        sql_statements = []
        for horse in horse_ids:
            sql = f"UPDATE rp_raw.results_data SET rp_comment = '' WHERE horse_id = '{horse['horse_id']}' AND race_id = '{race_id}';"
            sql_statements.append({"horse_id": horse["horse_id"], "update_sql": sql})

        sql_statements_df = pd.DataFrame(sql_statements)
        error_data = pd.merge(error_data, sql_statements_df, on="horse_id", how="left")

        self.storage_client.store_data(error_data, "comment_errors", "rp_raw")

    def fetch_data(
        self, data_type: Literal["results_data", "results_data_world"]
    ) -> pd.DataFrame:
        if data_type == "results_data":
            data = self.storage_client.fetch_data(
                f"""
                SELECT DISTINCT
                    debug_link
                FROM
                    rp_raw.results_data
                WHERE
                    race_date > '{self.MIN_DATE}'
                    AND race_date <= '{self.MAX_DATE}'
                    AND rp_comment IS NULL
                

            """
            )
        else:
            data = self.storage_client.fetch_data(
                f"""
                WITH null_worlds AS (
                    SELECT
                        unique_id
                    FROM
                        public.results_data
                    WHERE
                        rp_comment IS NULL
                        AND race_date > '{self.MIN_DATE}'
                        AND race_date <= '{self.MAX_DATE}'
                )
                SELECT DISTINCT
                    rw.debug_link
                FROM
                    null_worlds nw
                    LEFT JOIN rp_raw.results_data_world rw 
                    ON nw.unique_id = rw.unique_id
                WHERE
                    rw.unique_id IS NOT NULL
                    AND rw.rp_comment IS NULL
            """
            )
        data["analysis_link"] = data["debug_link"] + "/analysis"
        return data

    def _get_race_data(self, debug_link: str) -> tuple[str, str, list[dict]]:
        horses = self.storage_client.fetch_data(
            f"""
            SELECT 
                horse_name, 
                horse_id, 
                race_id, 
                race_date 
            FROM rp_raw.{self.table_name}
            WHERE debug_link = '{debug_link}'
            """
        )
        race_id = horses["race_id"].iloc[0]
        race_date = horses["race_date"].iloc[0]
        horse_ids = horses[["horse_id", "horse_name"]].to_dict("records")

        return race_id, race_date, horse_ids

    @staticmethod
    def _get_sample_links(data: pd.DataFrame) -> tuple[str, str]:
        sample_race = data.sample(1)
        return sample_race["analysis_link"].iloc[0], sample_race["debug_link"].iloc[0]

    @staticmethod
    def _chrome_get_content(url, load_time=3):
        script = f"""
            tell application "Google Chrome"
                activate
                open location "{url}"
                delay {load_time}
            end tell
            
            tell application "System Events"
                keystroke "a" using command down
                delay 0.5
                keystroke "c" using command down
                delay 0.5
            end tell
            
            tell application "Google Chrome"
                tell front window
                    close active tab
                end tell
            end tell
        """

        subprocess.run(["osascript", "-e", script])

    @staticmethod
    def _format_raw_text(chrome_content):
        if "No analysis available for this race" in chrome_content:
            return "No analysis available for this race"
        if "Awaiting analysis" in chrome_content:
            return "Awaiting analysis"
        # Handle different page layouts
        if "past winners" in chrome_content.lower():
            formatted_comments = (
                chrome_content.split("Past Winners")[1]
                .replace("\nPast Winners\n\n", "")
                .split("\n\n\n")[0]
                .split("\n")
            )
        else:
            formatted_comments = (
                chrome_content.split("My Ratings")[1]
                .replace("\nMy Ratings\n\n", "")
                .split("\n\n\n")[0]
                .split("\n")
            )

        cleaned_comments = []
        for comment in formatted_comments:
            if comment:
                cleaned = (
                    comment.replace("'", "'")
                    .replace("\x92", "'")
                    .replace("\x93", '"')
                    .replace("\x94", '"')
                    .replace("\xa0", " ")
                    .replace("\x96", " ")
                    .replace("\x97", " ")
                )
                cleaned_comments.append(cleaned)

        return cleaned_comments

    @staticmethod
    def convert_model_result_to_df(model_result: str) -> pd.DataFrame:
        json_data = json.loads(
            model_result.replace("```json", "").replace("```", "").strip()
        )
        return pd.DataFrame(json_data)

    def store_comments(self, comment_data: pd.DataFrame) -> None:
        self.storage_client.store_data(comment_data, "temp_comments", "rp_raw")

    def update_comments(self) -> None:
        self.storage_client.execute_query(
            f"""
            UPDATE rp_raw.{self.table_name} rd
            SET rp_comment = tc.rp_comment
            FROM rp_raw.temp_comments tc
            WHERE rd.horse_id = tc.horse_id 
            AND rd.race_id = tc.race_id;
            """
        )
        self.storage_client.execute_query(
            """
            UPDATE public.results_data prd
            SET rp_comment = subquery.rp_comment
            FROM (
                SELECT rd.unique_id, tc.rp_comment
                FROM rp_raw.results_data rd
                INNER JOIN rp_raw.temp_comments tc
                    ON rd.horse_id = tc.horse_id
                    AND rd.race_id = tc.race_id
                    AND rd.race_date = tc.race_date
            ) AS subquery
            WHERE prd.unique_id = subquery.unique_id;
            """
        )
        self.storage_client.execute_query(
            """
            UPDATE public.results_data prd
            SET rp_comment = subquery.rp_comment
            FROM (
                SELECT rd.unique_id, tc.rp_comment
                FROM rp_raw.results_data_world rd
                INNER JOIN rp_raw.temp_comments tc
                    ON rd.horse_id = tc.horse_id
                    AND rd.race_id = tc.race_id
                    AND rd.race_date = tc.race_date
            ) AS subquery
            WHERE prd.unique_id = subquery.unique_id;
            """
        )
        self.storage_client.execute_query("TRUNCATE TABLE rp_raw.temp_comments")
