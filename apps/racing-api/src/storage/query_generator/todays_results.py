from api_helpers.helpers.logging_config import I


class TodaysResultsSQLGenerator:
    @staticmethod
    def get_todays_race_results(input_race_id: str):
        query = f"""
            SELECT
                pd.race_time,
                pd.race_date,
                pd.race_title,
                pd.race_type,
                pd.race_class,
                pd.distance,
                pd.conditions,
                pd.going,
                pd.number_of_runners,
                pd.hcap_range,
                pd.age_range,
                pd.surface,
                pd.total_prize_money,
                pd.winning_time,
                pd.relative_time,
                pd.relative_to_standard,
                pd.main_race_comment,
                pd.course_id,
                pd.course,
                pd.race_id,
                pd.horse_name,
                pd.horse_id,
                pd.age,
                pd.draw,
                pd.headgear,
                pd.weight_carried,
                pd.finishing_position,
                pd.total_distance_beaten,
                pd.betfair_win_sp,
                pd.official_rating,
                pd.ts,
                pd.rpr,
                pd.tfr,
                pd.tfig,
                pd.in_play_high,
                pd.in_play_low,
                pd.tf_comment,
                pd.tfr_view,
                pd.rp_comment
            FROM
                public.unioned_results_data pd
            WHERE
                pd.race_id = {input_race_id}

        """
        return query

    @staticmethod
    def get_simulated_odds_individual_bets(input_race_id: str):
        query = f"""
            SELECT
                horse_name,
                finishing_position,
                number_of_runners,
                bet_type,
                bet_market,
                p_and_l
            FROM
                simulation.individual_bets
            WHERE
                race_id = {input_race_id}
        """
        return query

    @staticmethod
    def get_simulated_odds_race_total(input_race_id: str):
        query = f"""
            SELECT 
                ROUND(SUM(p_and_l)::numeric, 2) as total_p_and_l
	        FROM 
                simulation.individual_bets 
            WHERE 
                race_id = {input_race_id}
        """
        return query
