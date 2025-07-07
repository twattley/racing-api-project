import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.database_session_manager import database_session
from ..storage.query_generator.todays_pipeline_status import (
    PipelineStatusSQLGenerator,
)


class ETLStatusRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_pipeline_status(self):
        result = await self.session.execute(
            text(PipelineStatusSQLGenerator.get_todays_pipeline_status_sql()),
        )
        return pd.DataFrame(result.fetchall())


def get_etl_status_repository(session: AsyncSession = Depends(database_session)):
    return ETLStatusRepository(session)
