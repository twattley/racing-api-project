

class TodaysRaceTimesSQLGenerator:
    @staticmethod
    def define_feedback_races_sql():
        return f"""
            WITH distinct_races AS (
                SELECT 
                    pd.horse_id,
					pd.horse_name,
					pd.age,
                    pd.race_id,
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
					pd.betfair_win_sp,
                    pd.number_of_runners,
                    pd.hcap_range,
                    pd.age_range,
                    pd.surface,
                    pd.total_prize_money,
                    pd.first_place_prize_money,
                    pd.course_id,
                    ec.name as course,
                    'today'::character varying AS data_type
                FROM
                    public.unioned_results_data pd
                LEFT JOIN
                    entities.course ec
                    ON pd.course_id = ec.id
                WHERE
                    pd.race_date = (SELECT today_date from api.feedback_date)
                AND pd.course_id IN (
                    SELECT id 
                    FROM entities.course 
                    WHERE country_id = '1'
                )
            )
            SELECT
                *
            FROM
                distinct_races
            ORDER BY
                course,
                race_time;


    """

    @staticmethod
    def define_todays_races_sql():
        return f"""
            WITH distinct_races AS (
                SELECT 
                	pd.horse_id,
					pd.horse_name,
					pd.age,
                    pd.race_id,
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
					ud.betfair_win_sp,
                    pd.number_of_runners,
                    pd.hcap_range,
                    pd.age_range,
                    pd.surface,
                    pd.total_prize_money,
                    pd.first_place_prize_money,
                    pd.course_id,
                    ec.name as course,
                    'today'::character varying AS data_type
                FROM
                    public.unioned_results_data pd
                LEFT JOIN
                    entities.course ec
                    ON pd.course_id = ec.id
	            LEFT JOIN 
	                bf_raw.today_horse tbf
	            ON 
	                pd.horse_id = tbf.horse_id 
	            LEFT JOIN
	                bf_raw.todays_data bf
	            ON
	                tbf.bf_horse_id = bf.horse_id
				LEFT JOIN
					live_betting.updated_price_data ud
					ON bf.horse_id = ud.todays_betfair_selection_id
                WHERE
                    pd.race_date = current_date
                AND pd.course_id IN (
                    SELECT id 
                    FROM entities.course 
                    WHERE country_id = '1'
                )
            )
            SELECT
                *
            FROM
                distinct_races
            ORDER BY
                course,
                race_time;


    """

    @staticmethod
    def get_todays_race_times() -> str:
        query = TodaysRaceTimesSQLGenerator.define_todays_races_sql()
        return query

    @staticmethod
    def get_todays_feedback_race_times() -> str:
        query = TodaysRaceTimesSQLGenerator.define_feedback_races_sql()
        return query
