from datetime import datetime


class RaceTimesSQLGenerator:
    @staticmethod
    def get_todays_race_times():
        return """
            SELECT DISTINCT ON (pd.race_id)
                race_id, 
                race_time, 
                race_date, 
                race_title, 
                race_type, 
                race_class, 
                distance, 
                going, 
                number_of_runners, 
                hcap_range, 
                age_range, 
                surface, 
                total_prize_money, 
                first_place_prize_money, 
                course_id, 
                course, 
            FROM live_betting.race_times 
            WHERE race_date = CURRENT_DATE
            ORDER BY
                course,
                race_time;
            """

    @staticmethod
    def get_todays_feedback_race_times():
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
                    pd.going,
                    pd.number_of_runners,
                    pd.hcap_range,
                    pd.age_range,
                    pd.surface,
                    pd.total_prize_money,
                    pd.first_place_prize_money,
                    pd.course_id,
                    CASE 
                        WHEN pd.hcap_range IS NOT NULL THEN true 
                        ELSE false 
                    END AS is_hcap
                    ec.name as course
                FROM
                    public.unioned_results_data pd
                LEFT JOIN
                    entities.course ec
                    ON pd.course_id = ec.id
                WHERE
                    pd.race_date = (SELECT today_date FROM api.feedback_date)
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
