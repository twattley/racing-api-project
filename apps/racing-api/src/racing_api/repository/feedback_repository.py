from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from racing_api.storage.query_generator.store_selections import (
    StoreSelectionsSQLGenerator,
)

from ..storage.database_session_manager import database_session
from ..storage.query_generator.race_result import ResultsSQLGenerator
from ..storage.query_generator.race_times import RaceTimesSQLGenerator
from ..storage.query_generator.update_feedback_date import (
    UpdateFeedbackDateSQLGenerator,
)
from ..storage.query_generator.get_betting_results import BettingResultsSQLGenerator
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
        await self.session.commit()

    async def get_current_date_today(self):
        result = await self.session.execute(
            text("SELECT * from api.feedback_date"),
        )
        return pd.DataFrame(result.fetchall())

    async def store_betting_selections(self, selections: dict) -> None:

        await self.session.execute(
            text(StoreSelectionsSQLGenerator.get_store_selection_sql()), selections
        )

        await self.session.commit()

    async def get_betting_selections_analysis(self) -> pd.DataFrame:
        result = await self.session.execute(
            text(BettingResultsSQLGenerator.get_betting_results_sql()),
        )
        return pd.DataFrame(result.fetchall())


def get_feedback_repository(session: AsyncSession = Depends(database_session)):
    return FeedbackRepository(session)
