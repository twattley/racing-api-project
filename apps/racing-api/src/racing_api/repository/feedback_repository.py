from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from racing_api.models.betting_selections import BettingSelection

from ..storage.database_session_manager import database_session
from ..storage.query_generator.race_result import ResultsSQLGenerator
from ..storage.query_generator.race_times import RaceTimesSQLGenerator
from ..storage.query_generator.update_feedback_date import (
    UpdateFeedbackDateSQLGenerator,
)
from .base_repository import BaseRepository


class FeedbackRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_race_result_info(self, race_id: int):
        result = await self.session.execute(
            text(ResultsSQLGenerator.get_race_result_info_sql()),
            ResultsSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_result_horse_performance_data(self, race_id: int):
        result = await self.session.execute(
            text(ResultsSQLGenerator.get_race_result_horse_performance_sql()),
            ResultsSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_todays_race_times(self):
        result = await self.session.execute(
            text(RaceTimesSQLGenerator.get_todays_feedback_race_times()),
        )
        return pd.DataFrame(result.fetchall())

    async def store_current_date_today(self, date: str):
        await self.session.execute(
            text(
                UpdateFeedbackDateSQLGenerator.get_update_feedback_date_sql(
                    input_date=datetime.strptime(date.split("T")[0], "%Y-%m-%d").date()
                )
            )
        )

    async def get_current_date_today(self):
        result = await self.session.execute(
            text("SELECT * from api.feedback_date"),
        )
        return pd.DataFrame(result.fetchall())

    async def store_betting_selections(
        self, selections: Dict, market_state: List[Dict[str, Any]]
    ) -> None:
        """
        Unpack market_state into one row per horse and insert into live_betting.market_state.
        Note: horse_name, selection_id, race_time are set to None if not available in payload.
        """
        sql = text(
            """
            INSERT INTO live_betting.market_state (
                bet_selection_id,
                bet_type,
                market_type,
                race_id,
                race_date,
                market_id_win,
                market_id_place,
                number_of_runners,
                back_price_win,
                horse_id,
                selection_id,
                created_at
            )
            VALUES (
                :bet_selection_id,
                :bet_type,
                :market_type,
                :race_id,
                :race_date,
                :market_id_win,
                :market_id_place,
                :number_of_runners,
                :back_price_win,
                :horse_id,
                :selection_id,
                :created_at
            )
        """
        )
        async with self._engine.begin() as conn:
            await conn.execute(sql, market_state)


def get_feedback_repository(session: AsyncSession = Depends(database_session)):
    return FeedbackRepository(session)
