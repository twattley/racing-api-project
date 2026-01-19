class BettingResultsSQLGenerator:
    @staticmethod
    def define_betting_results_sql():
        return """ 
            SELECT 
                s.unique_id,
                s.race_id,
                s.race_time,
                s.race_date,
                s.horse_id,
                s.horse_name,
                s.selection_type,
                s.market_type,
                s.stake_points,
                CASE 
                    WHEN s.market_type = 'PLACE' THEN pd.betfair_place_sp
                    ELSE pd.betfair_win_sp
                END AS betfair_sp,
                s.created_at,
                pd.finishing_position,
                pd.number_of_runners
            FROM live_betting.selections s 
            LEFT JOIN public.unioned_results_data pd
                ON s.horse_id = pd.horse_id
                AND s.race_id = pd.race_id
            WHERE s.valid = true
            AND s.market_id = 'feedback'
            ORDER BY s.created_at;
            """

    @staticmethod
    def get_betting_results_sql():
        """
        Returns the query for betting results.
        """
        query = BettingResultsSQLGenerator.define_betting_results_sql()
        return query
