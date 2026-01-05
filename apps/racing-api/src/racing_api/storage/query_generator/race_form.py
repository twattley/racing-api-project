class RaceFormSQLGenerator:
    @staticmethod
    def define_historical_race_form_sql():
        return """
            WITH todays_context AS (
                SELECT 
                    pd.race_class AS todays_race_class,
                    pd.distance_yards AS todays_distance_yards,
                    pd.total_prize_money AS todays_total_prize_money,
                    pd.race_date AS todays_race_date,
                    CASE 
                        WHEN pd.conditions ~ '\\d+-(\\d+)' THEN 
                            COALESCE(
                                CASE 
                                    WHEN substring(pd.conditions from '\\d+-(\\d+)') ~ '^\\d+$' 
                                    THEN CAST(substring(pd.conditions from '\\d+-(\\d+)') AS INTEGER)
                                    ELSE 0 
                                END,
                                0
                            )
                        ELSE 0 
                    END AS todays_hcap_range
                FROM public.unioned_results_data pd
                WHERE pd.race_id = :race_id
                LIMIT 1
            ),
            rounded_data AS (
                SELECT 
                    *,
                    CASE 
                        WHEN betfair_win_sp IS NULL THEN NULL
                        WHEN ABS(betfair_win_sp) >= 10 THEN ROUND(betfair_win_sp::numeric, 0)
                        ELSE ROUND(betfair_win_sp::numeric, 1)
                    END AS betfair_win_sp_rounded,
                    CASE 
                        WHEN betfair_place_sp IS NULL THEN NULL
                        WHEN ABS(betfair_place_sp) >= 10 THEN ROUND(betfair_place_sp::numeric, 0)
                        ELSE ROUND(betfair_place_sp::numeric, 1)
                    END AS betfair_place_sp_rounded
                FROM public.unioned_results_data
            ),
            filtered_historical AS (
                SELECT rd.*
                FROM rounded_data rd
                CROSS JOIN todays_context tc
                WHERE rd.race_date >= (tc.todays_race_date - INTERVAL '2 years')
                    AND rd.race_date < tc.todays_race_date
                    AND rd.horse_id IN (
                        SELECT DISTINCT horse_id FROM public.unioned_results_data WHERE race_id = :race_id
                    )
            )
            SELECT
                hist.horse_name,
                hist.age,
                hist.finishing_position,
                hist.number_of_runners,
                hist.total_distance_beaten,
                    CASE 
                        WHEN hist.draw IS NOT NULL AND hist.number_of_runners IS NOT NULL THEN 
                            CONCAT('(', hist.draw, '/', hist.number_of_runners, ')')
                        WHEN hist.draw IS NOT NULL THEN 
                            CONCAT(hist.draw, '/?')
                        ELSE NULL
                    END AS draw_runners,
                -- Simple signed numeric parse (allow leading '-')
                CASE 
                    WHEN trim(hist.total_distance_beaten) ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN trim(hist.total_distance_beaten)::double precision
                    ELSE NULL
                END AS distance_beaten_signed,
                -- Absolute numeric (fallback 999 for non-numeric)
                CASE 
                    WHEN trim(hist.total_distance_beaten) ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN ABS(trim(hist.total_distance_beaten)::double precision)
                    ELSE 999::double precision
                END AS distance_beaten_numeric,
                -- Indicator: <0 green, 0-4 blue, >4 red; non-numeric red
                CASE 
                    WHEN trim(hist.total_distance_beaten) ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN
                        CASE 
                            WHEN trim(hist.total_distance_beaten)::double precision < 0 THEN 'green'
                            WHEN trim(hist.total_distance_beaten)::double precision <= 4 THEN 'blue'
                            ELSE 'red'
                        END
                    ELSE 'red'
                END AS distance_beaten_indicator,
                hist.betfair_win_sp,
                hist.betfair_place_sp,
                hist.official_rating,
                hist.race_id,
                hist.horse_id,
                hist.race_date,
                hist.race_class,
                hist.race_type,
                hist.race_title,
                hist.headgear,
                hist.distance,
                hist.going,
                hist.surface,
                hist.course,
                hist.total_prize_money,
                hist.first_place_prize_money,
                hist.rating,
                hist.speed_figure,
                hist.age_range,
                hist.hcap_range,
                hist.main_race_comment,
                hist.rp_comment,
                hist.tf_comment,
                hist.unique_id,
                hist.weeks_since_last_ran,
                -- Since ran indicator based on weeks_since_last_ran (<1 red, >8 red, else blue)
                CASE 
                    WHEN hist.weeks_since_last_ran IS NULL THEN 'blue'
                    WHEN hist.weeks_since_last_ran < 1 THEN 'red'
                    WHEN hist.weeks_since_last_ran > 8 THEN 'red'
                    ELSE 'blue'
                END AS since_ran_indicator,
                FLOOR((tc.todays_race_date - hist.race_date) / 7.0)::INTEGER AS total_weeks_since_run,
                CASE 
                    WHEN hist.distance_yards IS NOT NULL AND tc.todays_distance_yards IS NOT NULL THEN
                        CASE 
                            WHEN hist.distance_yards < tc.todays_distance_yards THEN 'lower'
                            WHEN hist.distance_yards = tc.todays_distance_yards THEN 'same'
                            WHEN hist.distance_yards > tc.todays_distance_yards THEN 'higher'
                            ELSE 'same'
                        END
                    ELSE 'same'
                END AS distance_diff,
                CASE 
                    WHEN hist.race_class IS NOT NULL AND tc.todays_race_class IS NOT NULL THEN
                        CASE 
                            WHEN hist.race_class < tc.todays_race_class THEN 'higher'
                            WHEN hist.race_class = tc.todays_race_class THEN 'same'
                            WHEN hist.race_class > tc.todays_race_class THEN 'lower'
                            ELSE 'same'
                        END
                    ELSE 'same'
                END AS class_diff,
                CASE 
                    WHEN hist.conditions ~ '\\d+-(\\d+)' AND tc.todays_hcap_range IS NOT NULL THEN
                        CASE 
                            WHEN substring(hist.conditions from '\\d+-(\\d+)') ~ '^\\d+$' THEN
                                CASE 
                                    WHEN CAST(substring(hist.conditions from '\\d+-(\\d+)') AS INTEGER) > tc.todays_hcap_range THEN 'higher'
                                    WHEN CAST(substring(hist.conditions from '\\d+-(\\d+)') AS INTEGER) = tc.todays_hcap_range THEN 'same'
                                    WHEN CAST(substring(hist.conditions from '\\d+-(\\d+)') AS INTEGER) < tc.todays_hcap_range THEN 'lower'
                                    ELSE 'same'
                                END
                            ELSE 'same'
                        END
                    ELSE 'same'
                END AS rating_range_diff
            FROM filtered_historical hist
            CROSS JOIN todays_context tc
            ORDER BY hist.horse_id, hist.race_date ASC;
            """

    @staticmethod
    def get_historical_race_form_sql():
        """
        Returns the parameterized SQL query for historical race form data.

        Parameters required when executing:
        - race_id (str): The race ID to get historical form for

        Returns:
        - str: Parameterized SQL query with :race_id named placeholders
        """
        query = RaceFormSQLGenerator.define_historical_race_form_sql()
        return query

    @staticmethod
    def get_query_params(race_id: int):
        """
        Returns the parameters for the historical race form SQL query.

        Args:
        - race_id (int): The race ID to get historical form for

        Returns:
        - dict: Parameters dictionary to be used with the named parameterized query
        """
        return {"race_id": race_id}
