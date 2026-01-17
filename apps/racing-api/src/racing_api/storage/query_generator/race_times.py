class RaceTimesSQLGenerator:
    @staticmethod
    def get_todays_race_times():
        return """
            WITH latest_prices AS (
                SELECT 
                    selection_id,
                    betfair_win_sp,
                    ROW_NUMBER() OVER (PARTITION BY selection_id ORDER BY created_at DESC) as rn
                FROM live_betting.v_latest_betfair_prices
                WHERE race_time::date = CURRENT_DATE
            )
            SELECT 
                pd.horse_id,
                pd.horse_name,
                pd.age,
                pd.race_id,
                pd.race_time,
                pd.race_time::time as time_hours,
                pd.race_date,
                pd.race_title,
                pd.race_type,
                pd.race_class,
                pd.distance,
                pd.distance_yards,
                pd.conditions,
                pd.going,
                COALESCE(lp.betfair_win_sp, pd.betfair_win_sp) as betfair_win_sp,
                pd.number_of_runners,
                pd.hcap_range,
                pd.age_range,
                pd.surface,
                pd.total_prize_money,
                pd.first_place_prize_money,
                pd.course_id,
                pd.course as course,
                'today'::character varying AS data_type
            FROM
                public.unioned_results_data pd
            LEFT JOIN latest_prices lp
                ON pd.betfair_id = lp.selection_id AND lp.rn = 1
            WHERE 
                pd.race_date = CURRENT_DATE
                AND pd.race_time > CURRENT_TIMESTAMP
            ORDER BY
                pd.course,
                pd.race_time;
            """

    @staticmethod
    def get_todays_feedback_race_times():
        return f"""
            SELECT 
                pd.horse_id,
                pd.horse_name,
                pd.age,
                pd.race_id,
                pd.race_time,
                pd.race_time::time as time_hours,
                pd.race_date,
                pd.race_title,
                pd.race_type,
                pd.race_class,
                pd.distance,
                pd.distance_yards,
                pd.conditions,
                pd.going,
                pd.betfair_win_sp,
                pd.number_of_runners,
                pd.hcap_range,
                pd.age_range,
                pd.surface,
                pd.total_prize_money,
                pd.first_place_prize_money,
                pd.course_id,
                pd.course,
                'today'::character varying AS data_type
            FROM
                public.unioned_results_data pd
            WHERE
                pd.race_date = (SELECT today_date FROM api.feedback_date LIMIT 1)
            AND 
                pd.country_id = 1
            ORDER BY
                pd.course,
                pd.race_time;
    """
