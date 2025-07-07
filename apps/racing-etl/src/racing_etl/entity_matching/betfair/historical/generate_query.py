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

    @staticmethod
    def fetch_bf_entity_data():
        return """ 
            SELECT regexp_replace(rw.horse_name, '^\d+\.\s+'::text, ''::text) AS horse_name,
                rw.course_name,
                rw.race_time,
                rw.race_date,
                rw.min_price,
                rw.max_price,
                rw.latest_price,
                rw.earliest_price,
                rw.price_change,
                rw.non_runners,
                rw.unique_id,
                rw.created_at
            FROM bf_raw.raw_data rw
                LEFT JOIN bf_raw.results_data rs ON rw.unique_id = rs.unique_id
            WHERE rs.unique_id IS NULL AND rw.horse_name !~ '^\d+$'::text;
        """

    @staticmethod
    def fetch_rp_entity_data():
        return """ 
            SELECT 
                unique_id,
                horse_name,
                course_name,
                horse_id,
                race_date,
                race_id
            FROM rp_raw.results_data
            WHERE (race_date IN ( 
                SELECT DISTINCT matching_historical_bf_entities.race_date
                    FROM entities.matching_historical_bf_entities));
            """
