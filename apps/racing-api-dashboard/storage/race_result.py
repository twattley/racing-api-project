from . import pg_client


def get_race_result_info(race_id):
    return pg_client.fetch_data(
        f"""
            SELECT
                pd.race_time,
                pd.race_date,
                pd.race_title,
                pd.race_type,
                pd.race_class,
                pd.distance,
                pd.conditions,
                pd.going,
                pd.number_of_runners,
                pd.hcap_range,
                pd.age_range,
                pd.surface,
                pd.total_prize_money,
                pd.main_race_comment,
                pd.course_id,
                pd.course,
                pd.race_id
            FROM
                public.unioned_results_data pd
            WHERE
                pd.race_id = {race_id}
            LIMIT 1;
            """
    )
def get_race_result_horse_performance(race_id):
    return pg_client.fetch_data(
        f"""
            SELECT
                pd.horse_name,
                pd.horse_id,
                pd.age,
                pd.draw,
                pd.headgear,
                pd.finishing_position,
                pd.total_distance_beaten,
                pd.betfair_win_sp,
                pd.official_rating,
                pd.speed_figure,
                pd.rating,
                pd.in_play_high,
                pd.in_play_low,
                pd.tf_comment,
                pd.tfr_view,
                pd.rp_comment,
                pd.unique_id
            FROM
                public.unioned_results_data pd
            WHERE
                pd.race_id = {race_id}
            ORDER BY
                COALESCE(
                    CASE 
                        WHEN pd.finishing_position ~ '^[0-9]+\.?[0-9]*$' 
                        THEN CAST(pd.finishing_position AS NUMERIC)
                        ELSE NULL 
                    END, 
                    999
                ) ASC;

        """
    )
