from api_helpers.helpers.logging_config import I


class UpdateFeedbackDateSQLGenerator:
    @staticmethod
    def get_update_feedback_date_sql(
        input_date: str,
    ):
        query = f"UPDATE racing_api.feedback_date SET today_date = '{input_date}'"
        I(f": \n{query}")
        return query
