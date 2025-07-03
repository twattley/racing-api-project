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

    @staticmethod
    def fetch_bf_entity_data():
        return """ 
        SELECT 
            b.race_time,
            b.race_date,
            b.horse_name,
            b.horse_id,
            ec.id AS course_id,
            'BF'::text AS data_source
        FROM bf_raw.todays_data b
            LEFT JOIN entities.course ec 
            ON b.course::text = ec.bf_name::text;
     """

    @staticmethod
    def fetch_rp_entity_data():
        return """ 
        SELECT 
            r.race_time,
            r.race_date,
            r.horse_name,
            eh.id AS horse_id,
            ec.id AS course_id,
            'RP'::text AS data_source
    FROM rp_raw.todays_data r
        LEFT JOIN entities.horse eh ON r.horse_id::text = eh.rp_id::text
        LEFT JOIN entities.course ec ON r.course_id::text = ec.rp_id::text
    WHERE ec.country_id::text = '1'::text;"""
