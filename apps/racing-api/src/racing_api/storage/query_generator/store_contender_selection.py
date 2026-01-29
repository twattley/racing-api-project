class StoreContenderSelectionSQLGenerator:
    @staticmethod
    def get_upsert_contender_selection_sql() -> str:
        """
        Upsert a contender selection - insert or update if horse_id/race_id exists.
        """
        return """
            INSERT INTO live_betting.contender_selections (
                horse_id,
                horse_name,
                race_id,
                race_date,
                race_time,
                selection_id,
                contender,
                created_at,
                updated_at
            ) VALUES (
                :horse_id,
                :horse_name,
                :race_id,
                :race_date,
                :race_time,
                :selection_id,
                :contender,
                :created_at,
                :updated_at
            )
            ON CONFLICT (horse_id, race_id)
            DO UPDATE SET
                contender = EXCLUDED.contender,
                selection_id = EXCLUDED.selection_id,
                updated_at = EXCLUDED.updated_at
        """

    @staticmethod
    def get_delete_contender_selection_sql() -> str:
        """
        Delete a contender selection when status is toggled off.
        """
        return """
            DELETE FROM live_betting.contender_selections
            WHERE horse_id = :horse_id AND race_id = :race_id
        """

    @staticmethod
    def get_contender_selections_by_race_sql() -> str:
        """
        Get all contender selections for a specific race.
        """
        return """
            SELECT 
                horse_id,
                horse_name,
                race_id,
                race_date,
                race_time,
                selection_id,
                contender,
                created_at,
                updated_at
            FROM live_betting.contender_selections
            WHERE race_id = :race_id
        """
