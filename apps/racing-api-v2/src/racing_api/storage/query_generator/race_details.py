class TodaysRaceDetailsSQLGenerator:
    @staticmethod
    def get_race_details_sql(
        input_race_id: int,
    ):
        query = f"""
            SELECT
                pd.race_id,
                pd.course,
                pd.distance,
                pd.going,
                pd.surface,
                pd.race_class,
                pd.hcap_range,
                pd.age_range,
                pd.conditions,
                pd.first_place_prize_money,
                pd.race_type,
                pd.race_title,
                pd.race_time,
                pd.race_date,
                -- is_hcap: true if hcap_range is not null, false otherwise
                CASE 
                    WHEN pd.hcap_range IS NOT NULL THEN true 
                    ELSE false 
                END AS is_hcap
            FROM public.unioned_results_data pd
            WHERE pd.race_id = {input_race_id}
            LIMIT 1;
        """
        return query
