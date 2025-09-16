class LiveSelectionsSQLGenerator:
    @staticmethod
    def define_get_live_selection_sql(table_name: str) -> str:
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
                customer_strategy_ref, 
                created_at, 
                processed_at, 
                bet_outcome, 
                price_matched, 
                profit, 
                commission, 
                side 
            FROM live_betting.{table_name} 
            WHERE race_date = CURRENT_DATE;
        """

    @staticmethod
    def get_to_run_sql():

        query = LiveSelectionsSQLGenerator.define_get_live_selection_sql('upcoming_bets')
        return query

    @staticmethod
    def get_ran_sql():
        query = LiveSelectionsSQLGenerator.define_get_live_selection_sql('live_results')
        return query
