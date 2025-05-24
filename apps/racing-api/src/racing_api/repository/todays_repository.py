from datetime import datetime

import pandas as pd
from api_helpers.clients import get_s3_client
from api_helpers.clients.s3_client import S3Client


class TodaysRepository:
    def __init__(self, s3_client: S3Client):
        self.s3_client = s3_client

    def get_todays_races(self) -> pd.DataFrame:
        file_name = (
            f"today/{datetime.now().strftime('%Y_%m_%d')}/race_data/race_times.parquet"
        )
        return self.s3_client.fetch_data(file_name)

    def get_todays_race_data(self):
        file_type = "updated_price_data"
        race_data = self.s3_client.fetch_data(
            f"today/{datetime.now().strftime('%Y_%m_%d')}/race_data/results_data.parquet"
        )
        price_data = self.s3_client.fetch_data(
            self.s3_client.get_latest_timestamped_file(
                base_path=f"today/{datetime.now().strftime('%Y_%m_%d')}/price_data",
                file_prefix=file_type,
                file_name=file_type,
            )
        )
        data = pd.merge(
            race_data[
                [
                    "horse_name",
                    "age",
                    "horse_sex",
                    "draw",
                    "headgear",
                    "weight_carried",
                    "weight_carried_lbs",
                    "extra_weight",
                    "jockey_claim",
                    "finishing_position",
                    "total_distance_beaten",
                    "industry_sp",
                    "betfair_win_sp",
                    "betfair_place_sp",
                    "price_change",
                    "official_rating",
                    "in_play_high",
                    "in_play_low",
                    "in_race_comment",
                    "tf_comment",
                    "rp_comment",
                    "tfr_view",
                    "race_id",
                    "horse_id",
                    "jockey_id",
                    "trainer_id",
                    "owner_id",
                    "sire_id",
                    "dam_id",
                    "unique_id",
                    "race_time",
                    "race_date",
                    "race_title",
                    "race_type",
                    "race_class",
                    "distance",
                    "distance_yards",
                    "distance_meters",
                    "distance_kilometers",
                    "conditions",
                    "going",
                    "number_of_runners",
                    "hcap_range",
                    "age_range",
                    "surface",
                    "total_prize_money",
                    "first_place_prize_money",
                    "winning_time",
                    "time_seconds",
                    "relative_time",
                    "relative_to_standard",
                    "country",
                    "main_race_comment",
                    "meeting_id",
                    "course_id",
                    "course",
                    "dam",
                    "sire",
                    "trainer",
                    "jockey",
                    "ts",
                    "rpr",
                    "tfr",
                    "tfig",
                    "data_type",
                    "todays_betfair_selection_id",
                ]
            ],
            price_data[
                [
                    "betfair_win_sp",
                    "betfair_place_sp",
                    "price_change",
                    "todays_betfair_selection_id",
                    "status",
                    "market_id_win",
                    "total_matched_win",
                    "back_price_1_win",
                    "back_price_1_depth_win",
                    "back_price_2_win",
                    "back_price_2_depth_win",
                    "back_price_3_win",
                    "back_price_3_depth_win",
                    "back_price_4_win",
                    "back_price_4_depth_win",
                    "back_price_5_win",
                    "back_price_5_depth_win",
                    "lay_price_1_win",
                    "lay_price_1_depth_win",
                    "lay_price_2_win",
                    "lay_price_2_depth_win",
                    "lay_price_3_win",
                    "lay_price_3_depth_win",
                    "lay_price_4_win",
                    "lay_price_4_depth_win",
                    "lay_price_5_win",
                    "lay_price_5_depth_win",
                    "total_matched_event_win",
                    "percent_back_win_book_win",
                    "percent_lay_win_book_win",
                    "market_place",
                    "market_id_place",
                    "total_matched_place",
                    "back_price_1_place",
                    "back_price_1_depth_place",
                    "back_price_2_place",
                    "back_price_2_depth_place",
                    "back_price_3_place",
                    "back_price_3_depth_place",
                    "back_price_4_place",
                    "back_price_4_depth_place",
                    "back_price_5_place",
                    "back_price_5_depth_place",
                    "lay_price_1_place",
                    "lay_price_1_depth_place",
                    "lay_price_2_place",
                    "lay_price_2_depth_place",
                    "lay_price_3_place",
                    "lay_price_3_depth_place",
                    "lay_price_4_place",
                    "lay_price_4_depth_place",
                    "lay_price_5_place",
                    "lay_price_5_depth_place",
                    "total_matched_event_place",
                    "percent_back_win_book_place",
                    "percent_lay_win_book_place",
                ]
            ],
            on="todays_betfair_selection_id",
            how="left",
        )

        data = data.assign(
            betfair_win_sp=data["betfair_win_sp_x"].fillna(data["betfair_win_sp_y"]),
            betfair_place_sp=data["betfair_place_sp_x"].fillna(
                data["betfair_place_sp_y"]
            ),
            price_change=data["price_change_x"].fillna(data["price_change_y"]),
        ).drop(
            columns=[
                "betfair_win_sp_x",
                "betfair_place_sp_x",
                "price_change_x",
                "betfair_win_sp_y",
                "betfair_place_sp_y",
                "price_change_y",
            ]
        )

        return data


def get_todays_repository():
    return TodaysRepository(get_s3_client())
