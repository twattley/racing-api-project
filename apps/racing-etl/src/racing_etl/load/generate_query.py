class LoadSQLGenerator:
    @staticmethod
    def define_upsert_sql():
        return """
        TRUNCATE public.unioned_results_data;

        WITH combined_data AS (
            -- Today's data
            SELECT
                pd.horse_name,
                pd.age,
                pd.horse_sex,
                pd.draw,
                pd.headgear,
                pd.weight_carried,
                pd.weight_carried_lbs,
                pd.extra_weight,
                pd.jockey_claim,
                NULL AS finishing_position,
                NULL AS total_distance_beaten,
                NULL AS industry_sp,
                NULL AS betfair_win_sp,
                NULL AS betfair_place_sp,
                pd.official_rating,
                NULL AS ts,
                NULL AS rpr,
                NULL AS tfr,
                NULL AS tfig,
                NULL AS in_play_high,
                NULL AS in_play_low,
                NULL AS price_change,
                NULL AS in_race_comment,
                NULL AS tf_comment,
                NULL AS rp_comment,
                NULL AS tfr_view,
                pd.race_id,
                pd.horse_id,
                pd.jockey_id,
                pd.trainer_id,
                pd.owner_id,
                pd.sire_id,
                pd.dam_id,
                pd.unique_id,
                tbf.bf_horse_id as betfair_id,
                pd.race_time,
                pd.race_date,
                pd.race_title,
                pd.race_type,
                pd.race_class,
                pd.distance,
                pd.distance_yards,
                pd.distance_meters,
                pd.distance_kilometers,
                pd.conditions,
                pd.going,
                pd.number_of_runners,
                pd.hcap_range,
                pd.age_range,
                es.name as surface,
                pd.total_prize_money,
                pd.first_place_prize_money,
                NULL AS winning_time,
                NULL AS time_seconds,
                NULL AS relative_time,
                NULL AS relative_to_standard,
                pd.country,
                NULL AS main_race_comment,
                pd.meeting_id,
                ec.country_id::integer,
                pd.course_id,
                pd.course,
                pd.dam,
                pd.sire,
                pd.trainer,
                pd.jockey,
                'today' AS data_type,
                NULL AS rating,
                NULL AS speed_figure
            FROM
                public.todays_data pd
            LEFT JOIN 
                bf_raw.today_horse tbf
            ON 
                pd.horse_id = tbf.horse_id 
            LEFT JOIN
                bf_raw.todays_data bf
            ON
                tbf.bf_horse_id = bf.horse_id
            LEFT JOIN
                entities.course ec
            ON
                pd.course_id = ec.id
            LEFT JOIN
                entities.surface es
            ON
                ec.surface_id = es.id
            WHERE pd.course_id IN (
                SELECT id 
                FROM entities.course 
                WHERE country_id = '1'
            )
                
            UNION ALL
            
            -- Historical data
            SELECT
                rd.horse_name,
                rd.age,
                rd.horse_sex,
                rd.draw,
                rd.headgear,
                rd.weight_carried,
                rd.weight_carried_lbs,
                rd.extra_weight,
                rd.jockey_claim,
                rd.finishing_position,
                rd.total_distance_beaten,
                rd.industry_sp,
                rd.betfair_win_sp,
                rd.betfair_place_sp,
                rd.official_rating,
                rd.ts,
                rd.rpr,
                rd.tfr,
                rd.tfig,
                rd.in_play_high,
                rd.in_play_low,
                bf.price_change,
                rd.in_race_comment,
                rd.tf_comment,
                rd.rp_comment,
                rd.tfr_view,
                rd.race_id,
                rd.horse_id,
                rd.jockey_id,
                rd.trainer_id,
                rd.owner_id,
                rd.sire_id,
                rd.dam_id,
                rd.unique_id,
                222222 as betfair_id,
                rd.race_time,
                rd.race_date,
                rd.race_title,
                rd.race_type,
                rd.race_class,
                rd.distance,
                rd.distance_yards,
                rd.distance_meters,
                rd.distance_kilometers,
                rd.conditions,
                rd.going,
                rd.number_of_runners,
                rd.hcap_range,
                rd.age_range,
                rd.surface,
                rd.total_prize_money,
                rd.first_place_prize_money,
                rd.winning_time,
                rd.time_seconds,
                rd.relative_time,
                rd.relative_to_standard,
                rd.country,
                rd.main_race_comment,
                rd.meeting_id,
                ec.country_id::integer,
                rd.course_id,
                rd.course,
                rd.dam,
                rd.sire,
                rd.trainer,
                rd.jockey,
                'historical' AS data_type,
                rd.rating,
                rd.speed_figure
            FROM
                public.results_data rd
            LEFT JOIN entities.horse eh
                ON rd.horse_id = eh.id
            LEFT JOIN (
                SELECT DISTINCT ON (id) id, country_id
                FROM entities.course
            ) ec ON rd.course_id = ec.id
            LEFT JOIN bf_raw.results_data bf
                ON eh.rp_id = bf.horse_id
                AND rd.race_id = bf.race_id::integer
        ),
        enriched_data AS (
            SELECT 
                *,
                -- Calculate days since last run for each horse
                COALESCE(
                    race_date - LAG(race_date) OVER (
                        PARTITION BY horse_id 
                        ORDER BY race_date, race_time
                    ), 
                    0
                ) as days_since_last_ran,

                COALESCE(
                ROUND((race_date - LAG(race_date) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time
                )) / 7.0), 
                0
                ) as weeks_since_last_ran,
                
                ROW_NUMBER() OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time
                ) as number_of_runs

            FROM combined_data
        ),
        places_data AS (
            SELECT 
                ed.*,
                -- Per-run flags using current race outcome (NULL for today's rows => 0)
                CASE WHEN finishing_position = '1' THEN 1 ELSE 0 END AS win_flag,
                CASE WHEN finishing_position = '2' THEN 1 ELSE 0 END AS second_flag,
                CASE WHEN finishing_position = '3' AND number_of_runners > 7 THEN 1 ELSE 0 END AS third_flag,
                CASE WHEN finishing_position = '4' AND number_of_runners > 12 THEN 1 ELSE 0 END AS fourth_flag,

                -- Cumulative counts up to and including t
                SUM(CASE WHEN finishing_position = '1' THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) AS first_places_t,
                SUM(CASE WHEN finishing_position = '2' THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) AS second_places_t,
                SUM(CASE WHEN finishing_position = '3' AND number_of_runners > 7 THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) AS third_places_t,
                SUM(CASE WHEN finishing_position = '4' AND number_of_runners > 12 THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) AS fourth_places_t
            FROM enriched_data ed
        ),
        final_data AS (
            SELECT 
                pd.*,
                -- Shift cumulative counts to t-1
                COALESCE(LAG(first_places_t)  OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) AS first_places,
                COALESCE(LAG(second_places_t) OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) AS second_places,
                COALESCE(LAG(third_places_t)  OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) AS third_places,
                COALESCE(LAG(fourth_places_t) OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) AS fourth_places,

                -- Percentages at t-1 using lagged counts and lagged denominator
                COALESCE(
                    ROUND(
                        (LAG(first_places_t) OVER (PARTITION BY horse_id ORDER BY race_date, race_time)::numeric)
                        / NULLIF(LAG(number_of_runs) OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) * 100,
                        0
                    )::INTEGER,
                0) AS win_percentage,
                COALESCE(
                    ROUND(
                        (
                            COALESCE(LAG(first_places_t)  OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) +
                            COALESCE(LAG(second_places_t) OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) +
                            COALESCE(LAG(third_places_t)  OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) +
                            COALESCE(LAG(fourth_places_t) OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0)
                        )::numeric
                        / NULLIF(LAG(number_of_runs) OVER (PARTITION BY horse_id ORDER BY race_date, race_time), 0) * 100,
                        0
                    )::INTEGER,
                0) AS place_percentage
            FROM places_data pd
        )

        INSERT INTO public.unioned_results_data (
            horse_name,
            age,
            horse_sex,
            draw,
            headgear,
            weight_carried,
            weight_carried_lbs,
            extra_weight,
            jockey_claim,
            finishing_position,
            total_distance_beaten,
            industry_sp,
            betfair_win_sp,
            betfair_place_sp,
            official_rating,
            ts,
            rpr,
            tfr,
            tfig,
            in_play_high,
            in_play_low,
            price_change,
            in_race_comment,
            tf_comment,
            rp_comment,
            tfr_view,
            race_id,
            horse_id,
            jockey_id,
            trainer_id,
            owner_id,
            sire_id,
            dam_id,
            unique_id,
			betfair_id,
            race_time,
            race_date,
            race_title,
            race_type,
            race_class,
            distance,
            distance_yards,
            distance_meters,
            distance_kilometers,
            conditions,
            going,
            number_of_runners,
            hcap_range,
            age_range,
            surface,
            total_prize_money,
            first_place_prize_money,
            winning_time,
            time_seconds,
            relative_time,
            relative_to_standard,
            country,
            main_race_comment,
            meeting_id,
            country_id,
            course_id,
            course,
            dam,
            sire,
            trainer,
            jockey,
            data_type,
            rating,
            speed_figure,
            days_since_last_ran,
            weeks_since_last_ran,
            number_of_runs,
            first_places,
            second_places,
            third_places,
            fourth_places,
            win_percentage,
            place_percentage
        )
        SELECT
            horse_name,
            age,
            horse_sex,
            draw,
            headgear,
            weight_carried,
            weight_carried_lbs,
            extra_weight,
            jockey_claim,
            finishing_position,
            total_distance_beaten,
            industry_sp,
            betfair_win_sp,
            betfair_place_sp,
            official_rating,
            ts,
            rpr,
            tfr,
            tfig,
            in_play_high,
            in_play_low,
            price_change,
            in_race_comment,
            tf_comment,
            rp_comment,
            tfr_view,
            race_id,
            horse_id,
            jockey_id,
            trainer_id,
            owner_id,
            sire_id,
            dam_id,
            unique_id,
			betfair_id,
            race_time,
            race_date,
            race_title,
            race_type,
            race_class,
            distance,
            distance_yards,
            distance_meters,
            distance_kilometers,
            conditions,
            going,
            number_of_runners,
            hcap_range,
            age_range,
            surface,
            total_prize_money,
            first_place_prize_money,
            winning_time,
            time_seconds,
            relative_time,
            relative_to_standard,
            country,
            main_race_comment,
            meeting_id,
            country_id,
            course_id,
            course,
            dam,
            sire,
            trainer,
            jockey,
            data_type,
            rating,
            speed_figure,
            days_since_last_ran,
            weeks_since_last_ran,
            number_of_runs,
            first_places,
            second_places,
            third_places,
            fourth_places,
            win_percentage,
            place_percentage
        FROM final_data;

        ANALYZE public.unioned_results_data;
            """

    @staticmethod
    def get_unioned_results_data_upsert_sql():
        return LoadSQLGenerator.define_upsert_sql()
