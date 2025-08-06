class HorseRaceInfoSQLGenerator:
    @staticmethod
    def define_todays_horse_race_info_sql():
        return """
            WITH todays_betting_data AS (
                SELECT 
                    todays_betfair_selection_id,
                    betfair_win_sp,
                    betfair_place_sp,
                    price_change
                FROM live_betting.updated_price_data
                WHERE race_date = CURRENT_DATE
            ),
            todays_betfair_horse_ids as (
                SELECT DISTINCT ON (bf_horse_id, horse_id)
                    bf_horse_id,
                    horse_id
                FROM bf_raw.today_horse
                WHERE race_date = CURRENT_DATE
            )
                SELECT 
                    pd.unique_id,
                    pd.race_id,
                    pd.race_date,
                    pd.horse_id,
                    CASE 
                        WHEN pd.draw IS NOT NULL AND pd.number_of_runners IS NOT NULL THEN 
                            CONCAT('(', pd.draw, '/', pd.number_of_runners, ')')
                        WHEN pd.draw IS NOT NULL THEN 
                            CONCAT(pd.draw, '/?')
                        WHEN pd.number_of_runners IS NOT NULL THEN 
                            CONCAT('?/', pd.number_of_runners)
                        ELSE NULL
                    END AS draw_runners,
                    pd.horse_name,
                    pd.age,
                    pd.official_rating,
                    pd.weight_carried_lbs,
                    COALESCE(pd.betfair_win_sp, p.betfair_win_sp) AS betfair_win_sp,
                    COALESCE(pd.betfair_place_sp, p.betfair_place_sp) AS betfair_place_sp,
                    COALESCE(pd.price_change, p.price_change) AS price_change,
                    pd.win_percentage,
                    pd.place_percentage,
                FROM public.unioned_results_data pd
                LEFT JOIN 
                    todays_betfair_horse_ids bf 
                    ON pd.horse_id = bf.horse_id
                LEFT JOIN todays_betting_data p 
                    ON bf.bf_horse_id = p.todays_betfair_selection_id
                WHERE pd.race_id = %(race_id)s
                ORDER BY pd.betfair_win_sp;
            """

    @staticmethod
    def get_historical_race_form_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (str): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with %(race_id)s named placeholders
        """
        query = HorseRaceInfoSQLGenerator.define_todays_horse_race_info_sql()
        return query

    @staticmethod
    def get_query_params(race_id: str):
        """
        Returns the parameters for the historical race form SQL query.

        Args:
        - race_id (str): The race ID to get historical form for

        Returns:
        - dict: Parameters dictionary to be used with the named parameterized query
        """
        return {"race_id": race_id}
