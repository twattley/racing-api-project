class MatchingBettingSQLGenerator:
    @staticmethod
    def define_upsert_sql():
        return """
        SELECT DISTINCT
            race_time, 
            horse_name,
            race_id,
            horse_id,
            meeting_id,
            course_id,
            course 
        FROM 
            public.todays_data
            """

    @staticmethod
    def fetch_todays_entity_data():
        return """
        SELECT DISTINCT
            race_time, 
            horse_name,
            race_id,
            horse_id,
            meeting_id,
            course_id,
            course 
        FROM 
            public.todays_data
        """

    @staticmethod
    def fetch_rp_entity_data():
        return """ 
        SELECT 
            r.unique_id,
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
