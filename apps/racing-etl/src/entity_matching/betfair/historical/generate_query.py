class MatchingBetfairSQLGenerator:
    @staticmethod
    def define_upsert_sql():
        return """
            INSERT INTO bf_raw.results_data (
                horse_name, 
                race_time, 
                price_change, 
                unique_id, 
                horse_id, 
                race_id, 
                created_at
                )
            SELECT 
                horse_name, 
                race_time, 
                price_change, 
                unique_id, 
                horse_id, 
                race_id, 
                now()
            FROM bf_raw_results_data_tmp_load
            ON CONFLICT ON CONSTRAINT bf_raw_race_horse_id_unq
            DO UPDATE SET
                horse_name = EXCLUDED.horse_name,
                race_time = EXCLUDED.race_time,
                price_change = EXCLUDED.price_change,
                horse_id = EXCLUDED.horse_id,
                race_id = EXCLUDED.race_id;
            """

