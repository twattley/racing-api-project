class LastPriceUpdateSQLGenerator:
    @staticmethod
    def get_last_price_update():
        return """
            SELECT max(created_at) AS last_price_update
            FROM live_betting.updated_price_data;
            """
