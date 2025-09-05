import asyncio
import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


from ..storage.database_session_manager import database_session
from ..storage.query_generator.race_times import RaceTimesSQLGenerator
from ..storage.query_generator.store_selections import StoreSelectionsSQLGenerator
from .base_repository import BaseRepository


class TodaysRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_todays_race_times(self):
        result = await self.session.execute(
            text(RaceTimesSQLGenerator.get_todays_race_times()),
        )
        return pd.DataFrame(result.fetchall())

    async def store_betting_selections(
        self, selections: dict, market_state: list[dict]
    ) -> None:

        await self.session.execute(
            text(StoreSelectionsSQLGenerator.get_store_market_state_sql()), market_state
        )
        await self.session.execute(
            text(StoreSelectionsSQLGenerator.get_store_selection_sql()), selections
        )


def get_todays_repository(session: AsyncSession = Depends(database_session)):
    return TodaysRepository(session)
