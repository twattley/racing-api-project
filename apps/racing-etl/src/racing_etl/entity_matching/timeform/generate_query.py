class MatchingTimeformSQLGenerator:
    @staticmethod
    def define_upsert_sql(
        entity_name: str,
    ):
        return f"""
            INSERT INTO entities.{entity_name} (rp_id, name, tf_id)
            SELECT rp_id, name, tf_id
            FROM
                entities_{entity_name}_tmp_load
            ON CONFLICT ON CONSTRAINT rp_tf_{entity_name}_unique_id
            DO NOTHING;
            """

    @staticmethod
    def get_upsert_sql(entity_name: str):
        if entity_name == "owner":
            return MatchingTimeformSQLGenerator.get_owner_upsert_sql()
        return MatchingTimeformSQLGenerator.define_upsert_sql(entity_name)

    @staticmethod
    def get_owner_upsert_sql():
        return """
            INSERT INTO entities.owner (rp_id, name)
            SELECT rp_id, name
            FROM
                entities_owner_tmp_load
            ON CONFLICT ON CONSTRAINT rp_owner_unique_id
            DO NOTHING;
            """

    @staticmethod
    def fetch_rp_entity_data(matching_type: str):
        if matching_type == "historical":
            return """
                 SELECT DISTINCT 
                    r.race_time,
                    r.race_date,
                    r.horse_name,
                    r.official_rating,
                    r.finishing_position,
                    r.course,
                    r.jockey_name,
                    r.trainer_name,
                    r.sire_name,
                    r.dam_name,
                    r.dams_sire,
                    r.owner_name,
                    r.horse_id,
                    r.trainer_id,
                    r.jockey_id,
                    r.sire_id,
                    r.dam_id,
                    r.dams_sire_id,
                    r.owner_id,
                    ec.id AS course_id
                FROM rp_raw.results_data r
                    LEFT JOIN entities.horse eh ON r.horse_id::text = eh.rp_id::text
                    LEFT JOIN entities.sire es ON r.sire_id::text = es.rp_id::text
                    LEFT JOIN entities.dam ed ON r.dam_id::text = ed.rp_id::text
                    LEFT JOIN entities.trainer et ON r.trainer_id::text = et.rp_id::text
                    LEFT JOIN entities.jockey ej ON r.jockey_id::text = ej.rp_id::text
                    LEFT JOIN entities.owner eo ON r.owner_id::text = eo.rp_id::text
                    LEFT JOIN entities.course ec ON r.course_id::text = ec.rp_id::text
                WHERE r.unique_id IS NOT NULL 
                    AND (eh.rp_id IS NULL OR es.rp_id IS NULL OR ed.rp_id IS NULL OR et.rp_id IS NULL OR ej.rp_id IS NULL OR eo.rp_id IS NULL OR ec.rp_id IS NULL)
            """
        elif matching_type == "todays":
            return """
                SELECT DISTINCT 
                    r.race_time,
                    r.race_date,
                    r.horse_name,
                    r.official_rating,
                    r.finishing_position,
                    r.course,
                    r.jockey_name,
                    r.trainer_name,
                    r.sire_name,
                    r.dam_name,
                    r.dams_sire,
                    r.owner_name,
                    r.horse_id,
                    r.trainer_id,
                    r.jockey_id,
                    r.sire_id,
                    r.dam_id,
                    r.dams_sire_id,
                    r.owner_id,
                    ec.id AS course_id
                FROM rp_raw.todays_data r
                    LEFT JOIN entities.horse eh ON r.horse_id::text = eh.rp_id::text
                    LEFT JOIN entities.sire es ON r.sire_id::text = es.rp_id::text
                    LEFT JOIN entities.dam ed ON r.dam_id::text = ed.rp_id::text
                    LEFT JOIN entities.trainer et ON r.trainer_id::text = et.rp_id::text
                    LEFT JOIN entities.jockey ej ON r.jockey_id::text = ej.rp_id::text
                    LEFT JOIN entities.owner eo ON r.owner_id::text = eo.rp_id::text
                    LEFT JOIN entities.course ec ON r.course_id::text = ec.rp_id::text
                WHERE r.unique_id IS NOT NULL AND (eh.rp_id IS NULL OR es.rp_id IS NULL OR ed.rp_id IS NULL OR et.rp_id IS NULL OR ej.rp_id IS NULL OR eo.rp_id IS NULL OR ec.rp_id IS NULL);

            """
        else:
            raise ValueError(
                f"Invalid matching type: {matching_type}. Expected 'historical' or 'todays'."
            )

    @staticmethod
    def fetch_tf_entity_data(matching_type: str):
        if matching_type == "historical":
            return """
                SELECT 
                    t.race_time,
                    t.race_date,
                    t.trainer_name,
                    t.trainer_id,
                    t.jockey_name,
                    t.jockey_id,
                    t.sire_name,
                    t.sire_id,
                    t.dam_name,
                    t.dam_id,
                    t.finishing_position,
                    t.horse_name,
                    t.horse_id,
                    t.horse_age,
                    ec.id AS course_id
                FROM tf_raw.results_data t
                    LEFT JOIN entities.course ec ON t.course_id::text = ec.tf_id::text
                WHERE (t.race_date IN ( SELECT DISTINCT matching_rp_entities.race_date
                        FROM entities.matching_rp_entities))
            """
        elif matching_type == "todays":
            return """
                SELECT t.race_time,
                    t.race_date,
                    t.trainer_name,
                    t.trainer_id,
                    t.jockey_name,
                    t.jockey_id,
                    t.sire_name,
                    t.sire_id,
                    t.dam_name,
                    t.dam_id,
                    t.finishing_position,
                    t.horse_name,
                    t.horse_id,
                    t.horse_age,
                    ec.id AS course_id
                FROM tf_raw.todays_data t
                    LEFT JOIN entities.course ec ON t.course_id::text = ec.tf_id::text;
            """
        else:
            raise ValueError(
                f"Invalid matching type: {matching_type}. Expected 'historical' or 'todays'."
            )
