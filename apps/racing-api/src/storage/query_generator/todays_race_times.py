from datetime import datetime

from api_helpers.helpers.logging_config import I


class TodaysRaceTimesSQLGenerator:
    @staticmethod
    def define_todays_races_sql(input_date: str):
        return f"""
            WITH distinct_races AS (
                SELECT DISTINCT ON (pd.race_id)
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
                    pd.race_date = {input_date}
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
    def get_todays_race_times():
        query = TodaysRaceTimesSQLGenerator.define_todays_races_sql(
            f"'{datetime.now().strftime('%Y-%m-%d')}'"
        )
        return query

    @staticmethod
    def get_todays_feedback_race_times():
        query = TodaysRaceTimesSQLGenerator.define_todays_races_sql(
            "(SELECT today_date from api.feedback_date)"
        )
        return query
