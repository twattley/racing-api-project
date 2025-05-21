from api_helpers.helpers.logging_config import I


class TodaysCollateralFormSQLGenerator:
    @staticmethod
    def get_collateral_form_sql(
        input_date: str,
        input_race_id: int,
        input_todays_race_date: str,
    ):
        query = f"""
            SELECT
                pd.*,
                'collateral'::character varying AS collateral_form_type
            FROM
                public.unioned_results_data pd
            WHERE
                pd.horse_id IN (
                    SELECT
                        pd.horse_id
                    FROM
                        public.unioned_results_data pd
                    WHERE
                        pd.race_id = {input_race_id}
                )
                AND pd.race_date > '{input_date}'
                AND pd.race_date < '{input_todays_race_date}'
            UNION 

            SELECT
                pd.*,
                'race_form'::character varying AS collateral_form_type
            FROM
                public.unioned_results_data pd
            WHERE
                pd.race_id = {input_race_id}
        """
        return query
