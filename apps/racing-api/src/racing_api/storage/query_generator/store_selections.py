class StoreSelectionsSQLGenerator:
    @staticmethod
    def define_store_selection_sql():
        return """
            INSERT INTO racing_api.selections(
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
                stake_points, 
                valid, 
                invalidated_at, 
                invalidated_reason, 
                size_matched, 
                average_price_matched, 
                cashed_out, 
                fully_matched, 
                customer_strategy_ref, 
                created_at, 
                processed_at
            )
            VALUES (
                :unique_id, 
                :race_id, 
                :race_time, 
                :race_date, 
                :horse_id, 
                :horse_name, 
                :selection_type, 
                :market_type, 
                :market_id, 
                :selection_id, 
                :requested_odds, 
                :stake_points,
                :valid, 
                :invalidated_at, 
                :invalidated_reason, 
                :size_matched, 
                :average_price_matched, 
                :cashed_out, 
                :fully_matched, 
                :customer_strategy_ref, 
                COALESCE(:created_at, NOW()), 
                COALESCE(:processed_at, NOW())
            )
            ON CONFLICT (unique_id) DO UPDATE SET
                race_id = EXCLUDED.race_id,
                race_time = EXCLUDED.race_time,
                race_date = EXCLUDED.race_date,
                horse_id = EXCLUDED.horse_id,
                horse_name = EXCLUDED.horse_name,
                selection_type = EXCLUDED.selection_type,
                market_type = EXCLUDED.market_type,
                market_id = EXCLUDED.market_id,
                selection_id = EXCLUDED.selection_id,
                requested_odds = EXCLUDED.requested_odds,
                stake_points = EXCLUDED.stake_points,
                valid = EXCLUDED.valid,
                invalidated_at = EXCLUDED.invalidated_at,
                invalidated_reason = EXCLUDED.invalidated_reason,
                size_matched = EXCLUDED.size_matched,
                average_price_matched = EXCLUDED.average_price_matched,
                cashed_out = EXCLUDED.cashed_out,
                fully_matched = EXCLUDED.fully_matched,
                customer_strategy_ref = EXCLUDED.customer_strategy_ref,
                processed_at = EXCLUDED.processed_at
        """

    @staticmethod
    def define_store_market_state():
        return """
        INSERT INTO racing_api.market_state (
            unique_id,
            bet_selection_id,
            bet_type,
            market_type,
            race_id,
            race_date,
            race_time,
            market_id_win,
            market_id_place,
            number_of_runners,
            back_price_win,
            horse_id,
            selection_id,
            created_at
        )
        VALUES (
            :unique_id,
            :bet_selection_id,
            :bet_type,
            :market_type,
            :race_id,
            :race_date,
            :race_time,
            :market_id_win,
            :market_id_place,
            :number_of_runners,
            :back_price_win,
            :horse_id,
            :selection_id,
            COALESCE(:created_at, NOW())
        )
        ON CONFLICT (unique_id, selection_id) DO UPDATE SET
            bet_selection_id = EXCLUDED.bet_selection_id,
            bet_type = EXCLUDED.bet_type,
            market_type = EXCLUDED.market_type,
            race_id = EXCLUDED.race_id,
            race_date = EXCLUDED.race_date,
            race_time = EXCLUDED.race_time,
            market_id_win = EXCLUDED.market_id_win,
            market_id_place = EXCLUDED.market_id_place,
            number_of_runners = EXCLUDED.number_of_runners,
            back_price_win = EXCLUDED.back_price_win,
            horse_id = EXCLUDED.horse_id,
            created_at = EXCLUDED.created_at
        """

    @staticmethod
    def get_store_selection_sql():
        """
        Returns the parameterized SQL query for storing selections.

        Parameters required when executing:
        - race_id (str): The race ID to get today's race details for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = StoreSelectionsSQLGenerator.define_store_selection_sql()
        return query

    @staticmethod
    def get_store_market_state_sql():
        """
        Returns the parameterized SQL query for storing market state.

        Parameters required when executing:
        - race_id (str): The race ID to get today's race details for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = StoreSelectionsSQLGenerator.define_store_market_state()
        return query
