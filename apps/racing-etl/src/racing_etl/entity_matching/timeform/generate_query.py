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
