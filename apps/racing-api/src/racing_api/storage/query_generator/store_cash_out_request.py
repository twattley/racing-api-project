class StoreCashOutRequestSQLGenerator:
    @staticmethod
    def define_store_cash_out_request_sql():
        return """

            INSERT INTO live_betting.cash_out_requests(
                market_id, 
                selection_id, 
                horse_name, 
                market_type, 
                selection_type, 
                race_time, 
                bet_id, 
                requested_odds, 
                size_matched, 
                price_matched,
                created_at
            )
            VALUES (
                :market_id, 
                :selection_id, 
                :horse_name, 
                :market_type, 
                :selection_type, 
                :race_time, 
                :bet_id, 
                :requested_odds, 
                :size_matched, 
                :price_matched,
                :created_at
            )

            ON CONFLICT (unique_id) DO NOTHING
        """
    @staticmethod
    def get_store_market_state_sql():
        """
        Returns the parameterized SQL query for storing market state.

        Parameters required when executing:
        - race_id (str): The race ID to get today's race details for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """

        query = StoreCashOutRequestSQLGenerator.define_store_cash_out_request_sql()
        return query