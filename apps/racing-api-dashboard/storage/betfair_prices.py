from api_helpers.interfaces.storage_client_interface import IStorageClient
import pandas as pd
from . import bf_client, pg_client


def get_market_ids(race_id: int) -> tuple[str, str]:
    """
    Get the Betfair market IDs for WIN and PLACE markets
    """
    market_ids = pg_client.fetch_data(
        f"""
        SELECT market_id_win, market_id_place FROM bf_raw.today_betfair_market_ids
        WHERE race_id = {race_id}
        """,
    )

    if market_ids.empty:
        return None

    return (
        market_ids["market_id_win"].values[0],
        market_ids["market_id_place"].values[0],
    )


def create_betting_odds_data(data: pd.DataFrame) -> pd.DataFrame:

    return pd.merge(
        data[data["market"] == "WIN"],
        data[data["market"] == "PLACE"],
        on="selection_id",
        suffixes=("_win", "_place"),
    )[
        [
            "selection_id",
            "status_win",
            "last_traded_price_win",
            "last_traded_price_place",
        ]
    ].rename(
        columns={
            "race_time_win": "race_time",
            "status_win": "status",
        }
    )

def fetch_betting_odds(race_id: int) -> pd.DataFrame:
    """Get the betting odds for a specific race."""
    market_ids = get_market_ids(race_id)
    if not market_ids:
        return pd.DataFrame()
    return create_betting_odds_data(
        bf_client.create_single_market_data(market_ids)
    )



