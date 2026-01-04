class ResultsSQLGenerator:
    @staticmethod
    def define_race_result_info_sql():
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
                pd.race_id
            FROM
                racing_api.unioned_results_data pd
            WHERE
                pd.race_id = :race_id
            LIMIT 1;
            """

    @staticmethod
    def define_race_result_horse_performance_sql():
        return """
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
                pd.tf_comment,
                pd.tfr_view,
                pd.rp_comment,
                pd.unique_id
            FROM
                racing_api.unioned_results_data pd
            WHERE
                pd.race_id = :race_id
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

    @staticmethod
    def get_race_result_info_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (str): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = ResultsSQLGenerator.define_race_result_info_sql()
        return query

    @staticmethod
    def get_race_result_horse_performance_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (str): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = ResultsSQLGenerator.define_race_result_horse_performance_sql()
        return query

    @staticmethod
    def get_query_params(race_id: int):
        """
        Returns the parameters for the historical race form SQL query.

        Args:
        - race_id (int): The race ID to get historical form for

        Returns:
        - dict: Parameters dictionary to be used with the named parameterized query
        """
        return {"race_id": race_id}
