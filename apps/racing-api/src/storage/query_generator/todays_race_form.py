from datetime import datetime

from api_helpers.helpers.logging_config import I


class TodaysRaceFormSQLGenerator:
    @staticmethod
    def define_todays_race_form_sql(input_date: str, input_race_id: str):
        return f"""
            WITH 
            todays_horse_ids AS (
                SELECT
                    pd.horse_id
                FROM
                    public.unioned_results_data pd
                WHERE
                    pd.race_id = {input_race_id}
            ),
            todays_form AS (
                SELECT
                    pd.horse_name,
                    pd.age,
                    pd.horse_sex,
                    pd.draw,
                    pd.headgear,
                    pd.weight_carried,
                    pd.weight_carried_lbs,
                    pd.extra_weight,
                    pd.jockey_claim,
                    pd.finishing_position,
                    pd.total_distance_beaten,
                    pd.industry_sp,
                    pd.betfair_win_sp,
                    pd.betfair_place_sp,
                    pd.official_rating,
                    CAST(NULL AS smallint) AS ts,
                    CAST(NULL AS smallint) AS rpr,
                    CAST(NULL AS smallint) AS tfr,
                    CAST(NULL AS smallint) AS tfig,
                    pd.in_play_high,
                    pd.in_play_low,
                    pd.price_change,
                    pd.in_race_comment,
                    pd.tf_comment,
                    pd.rp_comment,
                    pd.tfr_view,
                    pd.race_id,
                    pd.horse_id,
                    pd.jockey_id,
                    pd.trainer_id,
                    pd.owner_id,
                    pd.sire_id,
                    pd.dam_id,
                    pd.unique_id,
                    pd.race_time,
                    pd.race_date,
                    pd.race_title,
                    pd.race_type,
                    pd.race_class,
                    pd.distance,
                    pd.distance_yards,
                    pd.distance_meters,
                    pd.distance_kilometers,
                    pd.conditions,
                    pd.going,
                    pd.number_of_runners,
                    pd.hcap_range,
                    pd.age_range,
                    pd.surface,
                    pd.total_prize_money,
                    pd.first_place_prize_money,
                    pd.winning_time,
                    pd.time_seconds,
                    pd.relative_time,
                    pd.relative_to_standard,
                    pd.country,
                    pd.main_race_comment,
                    pd.meeting_id,
                    pd.course_id,
                    pd.course,
                    pd.dam,
                    pd.sire,
                    pd.trainer,
                    pd.jockey,
                    'today'::character varying AS data_type,
                    NULL::integer AS todays_betfair_selection_id,
                    NULL::varchar(50) AS status,
                    NULL::varchar(50) AS market_id_win,
                    NULL::real AS total_matched_win,
                    NULL::real AS back_price_1_win,
                    NULL::real AS back_price_1_depth_win,
                    NULL::real AS back_price_2_win,
                    NULL::real AS back_price_2_depth_win,
                    NULL::real AS back_price_3_win,
                    NULL::real AS back_price_3_depth_win,
                    NULL::real AS back_price_4_win,
                    NULL::real AS back_price_4_depth_win,
                    NULL::real AS back_price_5_win,
                    NULL::real AS back_price_5_depth_win,
                    NULL::real AS lay_price_1_win,
                    NULL::real AS lay_price_1_depth_win,
                    NULL::real AS lay_price_2_win,
                    NULL::real AS lay_price_2_depth_win,
                    NULL::real AS lay_price_3_win,
                    NULL::real AS lay_price_3_depth_win,
                    NULL::real AS lay_price_4_win,
                    NULL::real AS lay_price_4_depth_win,
                    NULL::real AS lay_price_5_win,
                    NULL::real AS lay_price_5_depth_win,
                    NULL::integer AS total_matched_event_win,
                    NULL::integer AS percent_back_win_book_win,
                    NULL::integer AS percent_lay_win_book_win,
                    NULL::varchar(50) AS market_place,
                    NULL::varchar(50) AS market_id_place,
                    NULL::real AS total_matched_place,
                    NULL::real AS back_price_1_place,
                    NULL::real AS back_price_1_depth_place,
                    NULL::real AS back_price_2_place,
                    NULL::real AS back_price_2_depth_place,
                    NULL::real AS back_price_3_place,
                    NULL::real AS back_price_3_depth_place,
                    NULL::real AS back_price_4_place,
                    NULL::real AS back_price_4_depth_place,
                    NULL::real AS back_price_5_place,
                    NULL::real AS back_price_5_depth_place,
                    NULL::real AS lay_price_1_place,
                    NULL::real AS lay_price_1_depth_place,
                    NULL::real AS lay_price_2_place,
                    NULL::real AS lay_price_2_depth_place,
                    NULL::real AS lay_price_3_place,
                    NULL::real AS lay_price_3_depth_place,
                    NULL::real AS lay_price_4_place,
                    NULL::real AS lay_price_4_depth_place,
                    NULL::real AS lay_price_5_place,
                    NULL::real AS lay_price_5_depth_place,
                    NULL::integer AS total_matched_event_place,
                    NULL::integer AS percent_back_win_book_place,
                    NULL::integer AS percent_lay_win_book_place
                FROM
                    public.unioned_results_data pd
                WHERE
                    pd.horse_id IN(SELECT horse_id FROM todays_horse_ids)
                    AND pd.race_date = {input_date}
            ),
            historical_form AS(
                SELECT
                    pd.horse_name,
                    pd.age,
                    pd.horse_sex,
                    pd.draw,
                    pd.headgear,
                    pd.weight_carried,
                    pd.weight_carried_lbs,
                    pd.extra_weight,
                    pd.jockey_claim,
                    pd.finishing_position,
                    pd.total_distance_beaten,
                    pd.industry_sp,
                    pd.betfair_win_sp,
                    pd.betfair_place_sp,
                    pd.official_rating,
                    pd.ts,
                    pd.rpr,
                    pd.tfr,
                    pd.tfig,
                    pd.in_play_high,
                    pd.in_play_low,
                    pd.price_change,
                    pd.in_race_comment,
                    pd.tf_comment,
                    pd.rp_comment,
                    pd.tfr_view,
                    pd.race_id,
                    pd.horse_id,
                    pd.jockey_id,
                    pd.trainer_id,
                    pd.owner_id,
                    pd.sire_id,
                    pd.dam_id,
                    pd.unique_id,
                    pd.race_time,
                    pd.race_date,
                    pd.race_title,
                    pd.race_type,
                    pd.race_class,
                    pd.distance,
                    pd.distance_yards,
                    pd.distance_meters,
                    pd.distance_kilometers,
                    pd.conditions,
                    pd.going,
                    pd.number_of_runners,
                    pd.hcap_range,
                    pd.age_range,
                    pd.surface,
                    pd.total_prize_money,
                    pd.first_place_prize_money,
                    pd.winning_time,
                    pd.time_seconds,
                    pd.relative_time,
                    pd.relative_to_standard,
                    pd.country,
                    pd.main_race_comment,
                    pd.meeting_id,
                    pd.course_id,
                    pd.course,
                    pd.dam,
                    pd.sire,
                    pd.trainer,
                    pd.jockey,
                    'historical'::character varying AS data_type,
                    NULL::integer AS todays_betfair_selection_id,
                    NULL::varchar(50) AS status,
                    NULL::varchar(50) AS market_id_win,
                    NULL::real AS total_matched_win,
                    NULL::real AS back_price_1_win,
                    NULL::real AS back_price_1_depth_win,
                    NULL::real AS back_price_2_win,
                    NULL::real AS back_price_2_depth_win,
                    NULL::real AS back_price_3_win,
                    NULL::real AS back_price_3_depth_win,
                    NULL::real AS back_price_4_win,
                    NULL::real AS back_price_4_depth_win,
                    NULL::real AS back_price_5_win,
                    NULL::real AS back_price_5_depth_win,
                    NULL::real AS lay_price_1_win,
                    NULL::real AS lay_price_1_depth_win,
                    NULL::real AS lay_price_2_win,
                    NULL::real AS lay_price_2_depth_win,
                    NULL::real AS lay_price_3_win,
                    NULL::real AS lay_price_3_depth_win,
                    NULL::real AS lay_price_4_win,
                    NULL::real AS lay_price_4_depth_win,
                    NULL::real AS lay_price_5_win,
                    NULL::real AS lay_price_5_depth_win,
                    NULL::integer AS total_matched_event_win,
                    NULL::integer AS percent_back_win_book_win,
                    NULL::integer AS percent_lay_win_book_win,
                    NULL::varchar(50) AS market_place,
                    NULL::varchar(50) AS market_id_place,
                    NULL::real AS total_matched_place,
                    NULL::real AS back_price_1_place,
                    NULL::real AS back_price_1_depth_place,
                    NULL::real AS back_price_2_place,
                    NULL::real AS back_price_2_depth_place,
                    NULL::real AS back_price_3_place,
                    NULL::real AS back_price_3_depth_place,
                    NULL::real AS back_price_4_place,
                    NULL::real AS back_price_4_depth_place,
                    NULL::real AS back_price_5_place,
                    NULL::real AS back_price_5_depth_place,
                    NULL::real AS lay_price_1_place,
                    NULL::real AS lay_price_1_depth_place,
                    NULL::real AS lay_price_2_place,
                    NULL::real AS lay_price_2_depth_place,
                    NULL::real AS lay_price_3_place,
                    NULL::real AS lay_price_3_depth_place,
                    NULL::real AS lay_price_4_place,
                    NULL::real AS lay_price_4_depth_place,
                    NULL::real AS lay_price_5_place,
                    NULL::real AS lay_price_5_depth_place,
                    NULL::integer AS total_matched_event_place,
                    NULL::integer AS percent_back_win_book_place,
                    NULL::integer AS percent_lay_win_book_place
                    
                FROM
                    public.unioned_results_data pd
                WHERE
                    pd.horse_id IN(SELECT horse_id FROM todays_horse_ids)
                    AND pd.race_date < {input_date}
                )
                SELECT
                    *
                FROM
                    todays_form
                UNION
                SELECT
                    *
                FROM
                    historical_form;
            """

    @staticmethod
    def get_todays_race_form_sql(input_race_id: str):
        query = TodaysRaceFormSQLGenerator.define_todays_race_form_sql(
            f"'{datetime.now().strftime('%Y-%m-%d')}'::date",
            input_race_id,
        )
        return query

    @staticmethod
    def get_todays_feedback_race_form_sql(input_race_id: str):
        query = TodaysRaceFormSQLGenerator.define_todays_race_form_sql(
            "(SELECT today_date::date from api.feedback_date)", input_race_id
        )
        return query

    @staticmethod
    def get_todays_feedback_race_form_by_date_sql(
        input_race_id: str, input_race_date: str
    ):
        query = TodaysRaceFormSQLGenerator.define_todays_race_form_sql(
            f"'{input_race_date}'::date",
            input_race_id,
        )
        return query
