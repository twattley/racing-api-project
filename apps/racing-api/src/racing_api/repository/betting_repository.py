from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.data_utils import deduplicate_dataframe
from api_helpers.helpers.file_utils import S3FilePaths
from api_helpers.helpers.processing_utils import ptr
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.betting_selections import BettingSelections
from ..storage.database_session_manager import database_session

paths = S3FilePaths()


class BettingRepository:
    def __init__(
        self,
        session: AsyncSession,
        postgres_client: PostgresClient,
        betfair_client: BetFairClient,
    ):
        self.session = session
        self.betfair_client = betfair_client
        self.postgres_client = postgres_client

    async def store_betting_selections(
        self, selections: BettingSelections, session_id: int
    ) -> dict:
        race_date = datetime.strptime(selections.race_date, "%Y-%m-%d").date()
        await self.session.execute(text("TRUNCATE TABLE api.betting_selections"))
        race_id = selections.race_id
        for selection in selections.selections:
            horse_id = selection.horse_id
            betting_type = selection.bet_type
            confidence = selection.confidence
            await self.session.execute(
                text(
                    """
                    INSERT INTO api.betting_selections (race_date, race_id, horse_id, betting_type, session_id, confidence, created_at) 
                    VALUES (:race_date, :race_id, :horse_id, :betting_type, :session_id, :confidence, :created_at)
                    """
                ),
                {
                    "race_date": race_date,
                    "race_id": race_id,
                    "horse_id": horse_id,
                    "betting_type": betting_type,
                    "session_id": session_id,
                    "confidence": confidence,
                    "created_at": datetime.now(),
                },
            )
        await self.session.commit()
        await self.session.execute(text("CALL api.update_betting_selections_info()"))
        await self.session.commit()
        return {
            "message": f"Stored {len(selections.selections)} selections for race {selections.race_id}"
        }

    async def store_live_betting_selections(self, data: pd.DataFrame):
        self.postgres_client.store_latest_data(
            data=data,
            schema="live_betting",
            table="selections",
            unique_columns=[
                "race_id",
                "horse_id",
                "selection_type",
                "market_id",
            ],
        )

    async def get_live_betting_selections(self):
        selections, orders = ptr(
            lambda: self.postgres_client.fetch_latest_data(
                schema="live_betting",
                table="selections",
                unique_columns=[
                    "race_id",
                    "horse_id",
                    "selection_type",
                    "market_id",
                ],
            ),
            lambda: self.betfair_client.get_past_orders_by_date_range(
                (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
            ),
        )
        if selections.empty:
            return pd.DataFrame()
        return (
            pd.merge(
                selections,
                orders[
                    [
                        "bet_outcome",
                        "market_id",
                        "price_matched",
                        "profit",
                        "commission",
                        "selection_id",
                        "side",
                    ]
                ],
                on=["selection_id", "market_id"],
                how="left",
            )
            .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
            .reset_index(drop=True)
        )

    async def store_market_state(self, data: pd.DataFrame):
        self.postgres_client.store_latest_data(
            data=data,
            schema="live_betting",
            table="market_state",
            unique_columns=[
                "race_id",
                "market_id",
            ],
        )

    async def get_betting_selections_analysis(self):
        result = await self.session.execute(
            text("SELECT * FROM api.betting_selections_info")
        )
        return pd.DataFrame(result.fetchall())


def get_betting_repository(session: AsyncSession = Depends(database_session)):
    return BettingRepository(session, get_postgres_client(), get_betfair_client())
