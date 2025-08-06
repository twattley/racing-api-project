class RaceFormGraphSQLGenerator:
    @staticmethod
    def define_race_form_graph_sql():
        return """
                WITH todays_context AS (
                    SELECT 
                        pd.race_class AS todays_race_class,
                        pd.distance_yards AS todays_distance_yards,
                        pd.total_prize_money AS todays_total_prize_money,
                        pd.race_date AS todays_race_date,
                        CASE 
                            WHEN pd.conditions ~ '\d+-(\d+)' THEN 
                                COALESCE(
                                    CASE 
                                        WHEN substring(pd.conditions from '\d+-(\d+)') ~ '^\d+$' 
                                        THEN CAST(substring(pd.conditions from '\d+-(\d+)') AS INTEGER)
                                        ELSE 0 
                                    END,
                                    0
                                )
                            ELSE 0 
                        END AS todays_hcap_range
                    FROM public.unioned_results_data pd
                    WHERE pd.race_id = %(race_id)s
                    LIMIT 1
                ),
                -- Filter for last two years and apply other filters (equivalent to _filter_last_two_years)
                filtered_historical AS (
                    SELECT rd.*
                    FROM public.unioned_results_data rd
                    CROSS JOIN todays_context tc
                    WHERE rd.race_date >= (tc.todays_race_date - INTERVAL '2 years')
                        AND rd.race_date < tc.todays_race_date  -- Historical data only
                        AND rd.horse_id IN (
                            SELECT DISTINCT horse_id 
                            FROM public.unioned_results_data 
                            WHERE race_id = %(race_id)s
                        )
                )
                SELECT
                    hist.horse_name,
                    hist.official_rating,
                    hist.race_id,
                    hist.horse_id,
                    hist.race_date,
                    hist.race_class,
                    hist.race_type,
                    hist.distance,
                    hist.going,
                    hist.surface,
                    hist.course,
                    hist.rating,
                    hist.speed_figure,
                    hist.unique_id
                FROM filtered_historical hist
                CROSS JOIN todays_context tc
                ORDER BY hist.horse_id, hist.race_date DESC;
            """

    @staticmethod
    def get_race_form_graph_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (str): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with %(race_id)s named placeholders
        """
        query = RaceFormGraphSQLGenerator.define_race_form_graph_sql()
        return query

    @staticmethod
    def get_query_params(race_id: str):
        """
        Returns the parameters for the historical race form SQL query.

        Args:
        - race_id (str): The race ID to get historical form for

        Returns:
        - dict: Parameters dictionary to be used with the named parameterized query
        """
        return {"race_id": race_id}
