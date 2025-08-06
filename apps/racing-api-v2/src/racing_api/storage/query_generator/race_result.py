class ResultsSQLGenerator:
    @staticmethod
    def define_race_results_sql():
        return """
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
                pd.race_id,
                pd.horse_name,
                pd.horse_id,
                pd.age,
                pd.draw,
                pd.headgear,
                pd.finishing_position,
                pd.total_distance_beaten,
                pd.betfair_win_sp,
                pd.official_rating,
                pd.ts,
                pd.rpr,
                pd.tfr,
                pd.tfig,
                pd.in_play_high,
                pd.in_play_low,
                pd.tf_comment,
                pd.tfr_view,
                pd.rp_comment,
                pd.unique_id,
                
                -- Add the computed float_total_distance_beaten column
                COALESCE(
                    CASE 
                        WHEN pd.total_distance_beaten ~ '^[0-9]+\.?[0-9]*$' 
                        THEN CAST(pd.total_distance_beaten AS NUMERIC)
                        ELSE NULL 
                    END, 
                    999
                ) AS float_total_distance_beaten

            FROM
                public.unioned_results_data pd
            WHERE
                pd.race_id = %(race_id)s
            ORDER BY
                -- Sort by the computed float_total_distance_beaten (ascending = winners first)
                COALESCE(
                    CASE 
                        WHEN pd.total_distance_beaten ~ '^[0-9]+\.?[0-9]*$' 
                        THEN CAST(pd.total_distance_beaten AS NUMERIC)
                        ELSE NULL 
                    END, 
                    999
                ) ASC;

        """

    @staticmethod
    def get_race_results_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (str): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with %(race_id)s named placeholders
        """
        query = ResultsSQLGenerator.define_race_results_sql()
        return query

    @staticmethod
    def get_query_params(input_race_id: str):
        """
        Returns the parameters for the historical race form SQL query.

        Args:
        - input_race_id (str): The race ID to get historical form for

        Returns:
        - dict: Parameters dictionary to be used with the named parameterized query
        """
        return {"race_id": input_race_id}
