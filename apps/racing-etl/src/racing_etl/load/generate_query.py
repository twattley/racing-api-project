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
                ) as number_of_runs,
                
                LAG(finishing_position) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time
                ) as shifted_finishing_position
                
            FROM combined_data
        ),
        places_data AS (
            SELECT 
                *,
                -- Calculate cumulative places
                SUM(CASE WHEN shifted_finishing_position = '1' THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) as first_places,
                SUM(CASE WHEN shifted_finishing_position = '2' THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) as second_places,
                SUM(CASE WHEN shifted_finishing_position = '3' AND number_of_runners > 7 THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) as third_places,
                SUM(CASE WHEN shifted_finishing_position = '4' AND number_of_runners > 12 THEN 1 ELSE 0 END) OVER (
                    PARTITION BY horse_id 
                    ORDER BY race_date, race_time 
                    ROWS UNBOUNDED PRECEDING
                ) as fourth_places
                
            FROM enriched_data
        ),
        final_data AS (
            SELECT 
                *,
                -- Calculate percentages
                COALESCE(ROUND((first_places::numeric / NULLIF(number_of_runs, 0)) * 100, 0)::INTEGER, 0) as win_percentage,
                COALESCE(ROUND(((first_places + second_places + third_places + fourth_places)::numeric / NULLIF(number_of_runs, 0)) * 100, 0)::INTEGER, 0) as place_percentage
            FROM places_data
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
            """

    @staticmethod
    def get_unioned_results_data_upsert_sql():
        return LoadSQLGenerator.define_upsert_sql()
