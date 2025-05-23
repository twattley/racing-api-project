from datetime import datetime

import pandas as pd
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.s3_client import S3Client
from api_helpers.helpers.processing_utils import ptr
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.betting_selections import BettingSelections
from ..repository.clients import get_betfair_client, get_s3_client
from ..storage.database_session_manager import database_session
from ..storage.parquet_storage import deduplicate_dataframe


class BettingRepository:
    def __init__(
        self,
        session: AsyncSession,
        s3_storage_client: S3Client,
        betfair_client: BetFairClient,
    ):
        self.session = session
        self.betfair_client = betfair_client
        self.s3_storage_client = s3_storage_client

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
        file_path = (
            f"today/{datetime.now().strftime('%Y_%m_%d')}/trader/selections.parquet"
        )
        current_selections = self.s3_storage_client.fetch_data(file_path)
        if current_selections.empty:
            self.s3_storage_client.store_data(data, file_path)
        else:
            current_data = self.s3_storage_client.fetch_data(file_path)
            deduplicated_data = deduplicate_dataframe(
                data,
                current_data,
                [
                    "race_id",
                    "horse_id",
                    "selection_type",
                    "market_id",
                ],
                "timestamp",
            )
            self.s3_storage_client.store_data(deduplicated_data, file_path)

    async def get_live_betting_selections(self):
        file_path = (
            f"today/{datetime.now().strftime('%Y_%m_%d')}/trader/selections.parquet"
        )
        selections, orders = ptr(
            lambda: self.s3_storage_client.fetch_data(file_path),
            lambda: self.betfair_client.get_current_orders(),
        )
        return pd.merge(
            selections,
            orders,
            on=["market_id", "selection_id", "selection_type"],
            how="left",
        )

    async def store_market_state(self, data: pd.DataFrame):
        file_path = f"today/{datetime.now().strftime('%Y_%m_%d')}/market_state.parquet"
        current_market_state = self.s3_storage_client.fetch_data(file_path)
        race_id = data["race_id"].iloc[0]
        if current_market_state.empty:
            self.s3_storage_client.store_data(data, file_path)
        else:
            deduplicated_data = current_market_state[
                current_market_state["race_id"] != race_id
            ]
            updated_data = pd.concat([deduplicated_data, data])
            self.s3_storage_client.store_data(updated_data, file_path)

    async def get_betting_selections_analysis(self):
        result = await self.session.execute(
            text("SELECT * FROM api.betting_selections_info")
        )
        return pd.DataFrame(result.fetchall())


def get_betting_repository(session: AsyncSession = Depends(database_session)):
    return BettingRepository(session, get_s3_client(), get_betfair_client())
