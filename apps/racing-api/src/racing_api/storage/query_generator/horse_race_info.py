class HorseRaceInfoSQLGenerator:
    @staticmethod
    def define_todays_horse_race_info_sql():
        return """
            WITH todays_betting_data AS (
                SELECT 
                    selection_id,
                    betfair_win_sp,
                    betfair_place_sp,
                    market_id_win,
                    market_id_place,
                    status
                FROM live_betting.v_latest_betfair_prices
                WHERE race_time::date = CURRENT_DATE
            ),
            contender_data AS (
                SELECT 
                    horse_id,
                    race_id,
                    status AS contender_status
                FROM live_betting.contender_selections
                WHERE race_id = :race_id
            ),
            combined_data AS (
                SELECT 
                    pd.unique_id,
                    pd.race_id,
                    pd.race_date,
                    pd.horse_id,
                    pd.race_class,
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
                    ROUND(COALESCE(pd.betfair_win_sp::numeric, p.betfair_win_sp::numeric), 1) AS betfair_win_sp,
                    ROUND(COALESCE(pd.betfair_place_sp::numeric, p.betfair_place_sp::numeric), 1) AS betfair_place_sp,
                    p.market_id_win,
                    p.market_id_place,
                    p.selection_id,
                    pd.headgear,
                    COALESCE(p.status, 'ACTIVE') AS status,
                    pd.win_percentage,
                    pd.place_percentage,
                    pd.number_of_runs,
                    cs.contender_status
                FROM public.unioned_results_data pd
                LEFT JOIN todays_betting_data p 
                    ON pd.betfair_id = p.selection_id
                LEFT JOIN contender_data cs
                    ON pd.horse_id = cs.horse_id AND pd.race_id = cs.race_id
                WHERE pd.race_id = :race_id
                )
            SELECT * FROM combined_data
            WHERE status = 'ACTIVE'
            ORDER BY betfair_win_sp ASC;

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
