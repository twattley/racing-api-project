from api_helpers.interfaces.storage_client_interface import IStorageClient
import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client

bf_client = get_betfair_client()
pg_client = get_postgres_client()


def get_market_ids(race_id: int, pg_client: IStorageClient) -> tuple[str, str]:
    """
    Get the Betfair market IDs for WIN and PLACE markets
    """
    market_ids = pg_client.fetch_data(
        f"""
        SELECT market_id_win, market_id_place FROM bf_raw.today_betfair_market_ids
        WHERE race_id = {race_id}
        """,
    )

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

def betting_odds(race_id: int) -> pd.DataFrame:
    """Get the betting odds for a specific race."""
    return create_betting_odds_data(
        bf_client.create_single_market_data(get_market_ids(race_id, pg_client))
    )



