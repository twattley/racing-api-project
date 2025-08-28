from . import pg_client
import pandas as pd
from api_helpers.helpers.processing_utils import ptr
from .betfair_prices import fetch_betting_odds


def fetch_race_info(race_id: int) -> pd.DataFrame:
    return pg_client.fetch_data(
        f"""
            SELECT 
                pd.unique_id,
                pd.race_id,
                pd.race_date,
                pd.horse_id,
                CASE 
                    WHEN pd.draw IS NOT NULL AND pd.number_of_runners IS NOT NULL THEN 
                        CONCAT('(', pd.draw, '/', pd.number_of_runners, ')')
                    WHEN pd.draw IS NOT NULL THEN 
                        CONCAT(pd.draw, '/?')
                    WHEN pd.number_of_runners IS NOT NULL THEN 
                        CONCAT('?/', pd.number_of_runners)
                    ELSE NULL
                END AS draw_runners,
                pd.horse_name,
                pd.headgear,
                pd.age,
                pd.official_rating,
                pd.weight_carried_lbs,
                pd.betfair_win_sp::numeric,
                pd.betfair_place_sp::numeric,
                pd.win_percentage,
                pd.place_percentage,
                pd.number_of_runs,
                bf.bf_horse_id as selection_id
            FROM public.unioned_results_data pd
            LEFT JOIN 
                bf_raw.today_horse bf
                ON pd.horse_id = bf.horse_id
            WHERE pd.race_id = {race_id} 

            """
    )


def get_horse_race_info(race_id: int) -> pd.DataFrame:
    ri, bf = ptr(
        lambda: fetch_race_info(race_id),
        lambda: fetch_betting_odds(race_id),
    )

    if bf.empty:
        return ri.drop(columns=["selection_id"]).sort_values(by=["betfair_win_sp"])

    return (
        pd.merge(bf, ri, on="selection_id", how="left")
        .assign(
            betfair_win_sp=pd.to_numeric(bf.last_traded_price_win, errors="coerce"),
            betfair_place_sp=pd.to_numeric(bf.last_traded_price_place, errors="coerce"),
        )
        .assign(
            tmp_betfair_sp_win=lambda x: x.betfair_win_sp.fillna(
                x.last_traded_price_win
            ),
            tmp_betfair_sp_place=lambda x: x.betfair_place_sp.fillna(
                x.last_traded_price_place
            ),
        )
        .drop(
            columns=[
                "last_traded_price_win",
                "last_traded_price_place",
                "betfair_win_sp",
                "betfair_place_sp",
            ]
        )
        .rename(
            columns={
                "tmp_betfair_sp_win": "betfair_win_sp",
                "tmp_betfair_sp_place": "betfair_place_sp",
            }
        )
        .sort_values(
            by=["betfair_win_sp"],
        )
    )
