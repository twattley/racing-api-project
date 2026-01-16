class LiveSelectionsSQLGenerator:
    @staticmethod
    def define_get_live_selection_sql(view_name: str) -> str:
        return f"""SELECT 
                unique_id, 
                race_id,
                race_time, 
                race_date, 
                horse_id, 
                horse_name, 
                selection_type, 
                market_type, 
                market_id, 
                selection_id, 
                requested_odds, 
                valid, 
                invalidated_at, 
                invalidated_reason, 
                size_matched, 
                average_price_matched, 
                cashed_out, 
                fully_matched,
                created_at,
                bet_outcome, 
                price_matched, 
                profit, 
                commission, 
                side 
            FROM live_betting.{view_name};
        """

    @staticmethod
    def get_to_run_sql():
        return LiveSelectionsSQLGenerator.define_get_live_selection_sql(
            "v_upcoming_bets"
        )

    @staticmethod
    def get_ran_sql():
        return LiveSelectionsSQLGenerator.define_get_live_selection_sql("v_live_results")
