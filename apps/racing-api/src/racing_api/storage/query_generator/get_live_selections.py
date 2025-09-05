class LiveSelectionsSQLGenerator:
    @staticmethod
    def define_get_live_selection_sql():
        return (
            """SELECT * FROM live_betting.selections WHERE race_date = CURRENT_DATE;"""
        )

    @staticmethod
    def get_live_selection_sql():
        """
        Returns the parameterized SQL query for getting live selections.

        Parameters required when executing:
        - race_id (str): The race ID to get today's race details for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = LiveSelectionsSQLGenerator.define_get_live_selection_sql()
        return query
