class HorseRaceInfoSQLGenerator:
    @staticmethod
    def define_todays_horse_race_info_sql():
        return """
            WITH todays_betting_data AS (
                SELECT 
                    selection_id,
                    betfair_win_sp,
                    betfair_place_sp
                FROM live_betting.updated_price_data
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
                        ELSE NULL
                    END AS draw_runners,
                    pd.horse_name,
                    pd.age,
                    pd.official_rating,
                    pd.weight_carried_lbs,
                    COALESCE(pd.betfair_win_sp, p.betfair_win_sp) AS betfair_win_sp,
                    COALESCE(pd.betfair_place_sp, p.betfair_place_sp) AS betfair_place_sp,
                    pd.win_percentage,
                    pd.place_percentage,
                    pd.number_of_runs
                FROM public.unioned_results_data pd
                LEFT JOIN 
                    todays_betfair_horse_ids bf 
                    ON pd.horse_id = bf.horse_id
                LEFT JOIN todays_betting_data p 
                    ON bf.bf_horse_id = p.selection_id
                WHERE pd.race_id = :race_id
                ORDER BY pd.betfair_win_sp;
            """

    @staticmethod
    def get_horse_race_info_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (int): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = HorseRaceInfoSQLGenerator.define_todays_horse_race_info_sql()
        return query

    @staticmethod
    def get_query_params(race_id: int):
        """
        Returns the parameters for the historical race form SQL query.

        Args:
        - race_id (int): The race ID to get historical form for

        Returns:
        - tuple: Parameters tuple to be used with the positional parameterized query
        """
        return (race_id,)
