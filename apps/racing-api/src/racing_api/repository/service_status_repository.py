import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.database_session_manager import database_session
from ..storage.query_generator.todays_service_status import (
    ServiceStatusSQLGenerator,
)


class ServiceStatusRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_service_status(self):
        result = await self.session.execute(
            text(ServiceStatusSQLGenerator.get_todays_service_status_sql()),
        )
        return pd.DataFrame(result.fetchall())


def get_service_status_repository(session: AsyncSession = Depends(database_session)):
    return ServiceStatusRepository(session)
