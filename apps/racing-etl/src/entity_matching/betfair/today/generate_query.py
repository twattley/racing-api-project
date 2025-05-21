class MatchingBetfairSQLGenerator:
    @staticmethod
    def define_upsert_sql():
        return """
            TRUNCATE TABLE bf_raw.today_horse;
            
            INSERT INTO bf_raw.today_horse (horse_id, bf_horse_id, race_date)
            SELECT DISTINCT horse_id, bf_horse_id, race_date
            FROM entities_todays_betfair_horse_ids_tmp_load
            ON CONFLICT ON CONSTRAINT todays_betfair_ids_horse_id_pd
            DO NOTHING;
            """
