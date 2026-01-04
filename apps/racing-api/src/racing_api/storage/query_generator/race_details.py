class RaceDetailsSQLGenerator:
    @staticmethod
    def define_race_details_sql():
        return """
            SELECT
                pd.race_id,
                pd.course,
                pd.distance,
                pd.going,
                pd.surface,
                pd.race_class,
                pd.hcap_range,
                pd.age_range,
                pd.conditions,
                pd.first_place_prize_money,
                pd.race_type,
                pd.race_title,
                pd.race_time,
                pd.race_date,
                -- is_hcap: true if hcap_range is not null, false otherwise
                CASE 
                    WHEN pd.hcap_range IS NOT NULL THEN true 
                    ELSE false 
                END AS is_hcap
            FROM racing_api.unioned_results_data pd
            WHERE pd.race_id = :race_id
            LIMIT 1;
        """

    @staticmethod
    def get_race_details_sql():
        """
        Returns the parameterized SQL query for today's race details.

        Parameters required when executing:
        - race_id (str): The race ID to get today's race details for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = RaceDetailsSQLGenerator.define_race_details_sql()
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
