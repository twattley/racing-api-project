import time

import pandas as pd
from selenium.webdriver.common.by import By

from ...config import Config
from ...raw.webdriver.web_driver import WebDriver
from ...storage.storage_client import get_storage_client

storage_client = get_storage_client("postgres")

TODAYS_QUERY = """
    SELECT horse_name, horse_id 
    ROM public.todays_data 
    WHERE race_class = 1
    """

QUERY = """
    WITH class1_horses AS (
        SELECT DISTINCT 
            pd.horse_id,
            pd.horse_name
        FROM 
            public.results_data pd
        WHERE 
            race_class = 1
            AND race_date > '2015-01-01'
            AND race_type > 'Flat'
    )

    SELECT 
        ch.horse_name, 
        eh.rp_id:: integer,
        COUNT(*) AS total_race_count
    FROM 
        class1_horses ch
    JOIN 
        public.results_data pd ON ch.horse_id = pd.horse_id
    LEFT JOIN 
        entities.horse eh ON pd.horse_id = eh.id
    GROUP BY 
        ch.horse_name, 
        eh.rp_id;
    """

URL_TEMPLATE = "https://www.racingpost.com/profile/horse/horse-id/horse-name/form"


def get_rules_races_data(rows):
    rules_races_data = {}
    for row in rows:
        # Get the first cell to check if it's Rules Races
        first_cell = row.find_element(By.CSS_SELECTOR, "td:first-child")
        category_button = first_cell.find_element(By.CSS_SELECTOR, "button")

        if category_button.get_attribute("value") == "Rules Races":
            print("Found Rules Races row!")

            # Extract all cell values from this row
            cells = row.find_elements(By.CSS_SELECTOR, "td")

            # Map the cells to their respective data
            headers = [
                "category",
                "runs",
                "wins",
                "2nds",
                "3rds",
                "winnings",
                "prize",
                "earnings",
                "or",
                "best_ts",
                "best_rpr",
                "best_mr",
            ]

            for i, cell in enumerate(cells):
                if i == 0:
                    # For the first cell, we already know it's "Rules Races"
                    rules_races_data[headers[i]] = "Rules Races"
                elif i == 2:
                    # For wins, we need to extract just the number (6) from the complex structure
                    wins_text = cell.find_element(By.TAG_NAME, "span").text
                    wins = wins_text.split("/")[0] if "/" in wins_text else wins_text
                    rules_races_data[headers[i]] = wins.strip()
                else:
                    rules_races_data[headers[i]] = cell.text
            print("found")
            break

    return rules_races_data


def save_data(data_type, horse_name, horse_id, url):
    data = pd.DataFrame({"horse": [horse_name], "horse_id": [horse_id], "url": [url]})
    data.to_csv(
        f"/Users/tomwattley/Code/python/racing-api-project/racing-etl/src/raw/racing_post/{data_type}.csv",
        mode="a",
        header=False,
        index=False,
    )


def main():
    passes = pd.read_csv(
        "/Users/tomwattley/Code/python/racing-api-project/racing-etl/src/raw/racing_post/pass.csv"
    )
    fails = pd.read_csv(
        "/Users/tomwattley/Code/python/racing-api-project/racing-etl/src/raw/racing_post/fail.csv"
    )

    tried = pd.concat([passes, fails])

    driver = WebDriver(config=Config())
    driver = driver.create_session()
    counts_df = storage_client.fetch_data(query=QUERY)

    not_tried = counts_df[
        ~counts_df["rp_id"].isin(tried["horse_id"].unique())
    ].reset_index(drop=True)

    for horse in not_tried.itertuples():
        print(f"iteration - {horse.Index} of {len(not_tried)}")
        try:
            h_url = URL_TEMPLATE.replace("horse-id", f"{horse.rp_id}").replace(
                "horse-name", f"{horse.horse_name.lower().replace(' ', '-')}"
            )
            driver.get(h_url)
            time.sleep(5)
            rows = driver.find_elements(
                By.CSS_SELECTOR, "table.ui-table.hp-raceRecords tbody tr"
            )
            rules_races = get_rules_races_data(rows)
            if horse.total_race_count == int(rules_races["runs"]):
                print(
                    f"Match - found {horse.total_race_count} DB records and {rules_races['runs']} RP records"
                )
                save_data("pass", horse.horse_name, horse.rp_id, h_url)
                continue
            else:
                print(
                    f"Fail - {h_url} found {horse.total_race_count} DB records and {rules_races['runs']} RP records"
                )
                save_data("fail", horse.horse_name, horse.rp_id, h_url)
        except Exception as e:
            print(e)
            continue


if __name__ == "__main__":
    main()
