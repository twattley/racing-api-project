class RawSQLGenerator:
    @staticmethod
    def define_upsert_sql(
        table_name: str,
    ):
        return f"""
            INSERT INTO tf_raw.{table_name}(
                tf_rating,
                tf_speed_figure,
                draw,
                trainer_name,
                trainer_id,
                jockey_name,
                jockey_id,
                sire_name,
                sire_id,
                dam_name,
                dam_id,
                finishing_position,
                horse_name,
                horse_id,
                horse_name_link,
                horse_age,
                equipment,
                official_rating,
                fractional_price,
                betfair_win_sp,
                betfair_place_sp,
                in_play_prices,
                tf_comment,
                course,
                race_date,
                race_time_debug,
                race_time,
                course_id,
                race,
                race_id,
                distance,
                going,
                prize,
                hcap_range,
                age_range,
                race_type,
                main_race_comment,
                debug_link,
                created_at,
                unique_id
            )
        SELECT
                tf_rating,
                tf_speed_figure,
                draw,
                trainer_name,
                trainer_id,
                jockey_name,
                jockey_id,
                sire_name,
                sire_id,
                dam_name,
                dam_id,
                finishing_position,
                horse_name,
                horse_id,
                horse_name_link,
                horse_age,
                equipment,
                official_rating,
                fractional_price,
                betfair_win_sp,
                betfair_place_sp,
                in_play_prices,
                tf_comment,
                course,
                race_date,
                race_time_debug,
                race_time,
                course_id,
                race,
                race_id,
                distance,
                going,
                prize,
                hcap_range,
                age_range,
                race_type,
                main_race_comment,
                debug_link,
                created_at,
                unique_id
            FROM
                tf_raw_{table_name}_tmp_load
            ON CONFLICT(unique_id)
            DO UPDATE SET
                tf_rating = EXCLUDED.tf_rating,
                tf_speed_figure = EXCLUDED.tf_speed_figure,
                draw = EXCLUDED.draw,
                trainer_name = EXCLUDED.trainer_name,
                trainer_id = EXCLUDED.trainer_id,
                jockey_name = EXCLUDED.jockey_name,
                jockey_id = EXCLUDED.jockey_id,
                sire_name = EXCLUDED.sire_name,
                sire_id = EXCLUDED.sire_id,
                dam_name = EXCLUDED.dam_name,
                dam_id = EXCLUDED.dam_id,
                finishing_position = EXCLUDED.finishing_position,
                horse_name = EXCLUDED.horse_name,
                horse_id = EXCLUDED.horse_id,
                horse_name_link = EXCLUDED.horse_name_link,
                horse_age = EXCLUDED.horse_age,
                equipment = EXCLUDED.equipment,
                official_rating = EXCLUDED.official_rating,
                fractional_price = EXCLUDED.fractional_price,
                betfair_win_sp = EXCLUDED.betfair_win_sp,
                betfair_place_sp = EXCLUDED.betfair_place_sp,
                in_play_prices = EXCLUDED.in_play_prices,
                tf_comment = EXCLUDED.tf_comment,
                course = EXCLUDED.course,
                race_date = EXCLUDED.race_date,
                race_time_debug = EXCLUDED.race_time_debug,
                race_time = EXCLUDED.race_time,
                course_id = EXCLUDED.course_id,
                race = EXCLUDED.race,
                race_id = EXCLUDED.race_id,
                distance = EXCLUDED.distance,
                going = EXCLUDED.going,
                prize = EXCLUDED.prize,
                hcap_range = EXCLUDED.hcap_range,
                age_range = EXCLUDED.age_range,
                race_type = EXCLUDED.race_type,
                main_race_comment = EXCLUDED.main_race_comment,
                debug_link = EXCLUDED.debug_link,
                created_at=now();
            """

    @staticmethod
    def get_results_data_upsert_sql():
        return RawSQLGenerator.define_upsert_sql("results_data")

    @staticmethod
    def get_results_data_world_upsert_sql():
        return RawSQLGenerator.define_upsert_sql("results_data_world")
