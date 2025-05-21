from src.raw.racing_post.results_data_scraper import RPResultsDataScraper
import pandas as pd
import pytest
from tests.test_helpers import assert_df_data_equal


@pytest.mark.parametrize(
    "input_df, output_df",
    [
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "", "", ""],
                    "finishing_position": ["1", "2", "3", "4"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "", "", ""],
                    "finishing_position": ["1", "2", "3", "4"],
                    "adj_total_distance_beaten": ["FOG", "FOG", "FOG", "FOG"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "[15]", "[26¾]", ""],
                    "finishing_position": ["1", "2", "3", "0"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "[15]", "[26¾]", ""],
                    "finishing_position": ["1", "2", "3", "0"],
                    "adj_total_distance_beaten": ["-15.0", "15.0", "26.75", "UND"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["2", "[4¾]", "", "[26¾]"],
                    "finishing_position": ["1", "2", "3", "0"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["2", "[4¾]", "", "[26¾]"],
                    "finishing_position": ["1", "2", "3", "0"],
                    "adj_total_distance_beaten": ["-2.75", "2.75", "(DSQ) 3", "24.75"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1"],
                    "unique_id": ["1"],
                    "total_distance_beaten": [""],
                    "finishing_position": ["1"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1"],
                    "unique_id": ["1"],
                    "total_distance_beaten": [""],
                    "finishing_position": ["1"],
                    "adj_total_distance_beaten": ["WO"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "2", "", ""],
                    "finishing_position": ["1", "2", "C", "D"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "2", "", ""],
                    "finishing_position": ["1", "2", "C", "D"],
                    "adj_total_distance_beaten": ["-2.0", "2.0", "C", "D"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "[3¼]", "[15]", "[26¾]"],
                    "finishing_position": ["1", "2", "3", "4"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "[3¼]", "[15]", "[26¾]"],
                    "finishing_position": ["1", "2", "3", "4"],
                    "adj_total_distance_beaten": ["-3.25", "3.25", "15.0", "26.75"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "[4½]", "[8¼]", "dht"],
                    "finishing_position": ["1", "2", "3", "1"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1", "1", "1"],
                    "unique_id": ["1", "2", "3", "4"],
                    "total_distance_beaten": ["", "[4½]", "[8¼]", "dht"],
                    "finishing_position": ["1", "2", "3", "1"],
                    "adj_total_distance_beaten": ["-4.5", "4.5", "8.25", "-4.5"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1"],
                    "unique_id": ["1", "2"],
                    "total_distance_beaten": ["", "dht"],
                    "finishing_position": ["1", "1"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1"],
                    "unique_id": ["1", "2"],
                    "total_distance_beaten": ["", "dht"],
                    "finishing_position": ["1", "1"],
                    "adj_total_distance_beaten": ["0", "0"],
                }
            ),
        ),
        (
            pd.DataFrame(
                {
                    "race_id": ["1", "1"],
                    "unique_id": ["1", "2"],
                    "total_distance_beaten": ["", "5"],
                    "finishing_position": ["1", "DSQ"],
                }
            ),
            pd.DataFrame(
                {
                    "race_id": ["1", "1"],
                    "unique_id": ["1", "2"],
                    "total_distance_beaten": ["", "5"],
                    "finishing_position": ["1", "DSQ"],
                    "adj_total_distance_beaten": ["0", "DSQ"],
                }
            ),
        ),
    ],
    ids=[
        "FOG",
        "UNDEFINED",
        "DSQ",
        "WO",
        "LETTERS",
        "FIRST_PLACE",
        "DEAD_HEAT",
        "DEAD_HEAT_2",
        "DSQ_2RNR",
    ],
)
def test_creates_raw_distance_beaten(input_df, output_df):
    assert_df_data_equal(
        RPResultsDataScraper.get_adj_total_distance_beaten(input_df), output_df
    )
