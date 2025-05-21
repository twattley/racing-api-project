from datetime import datetime

import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database_session_manager import database_session
from src.storage.query_generator.todays_collateral_form_data import (
    TodaysCollateralFormSQLGenerator,
)


class CollateralRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_collateral_form_by_id(
        self, race_date: str, race_id: int, todays_race_date: str
    ):
        result = await self.session.execute(
            text(
                TodaysCollateralFormSQLGenerator.get_collateral_form_sql(
                    input_date=datetime.strptime(race_date, "%Y-%m-%d").date(),
                    input_race_id=race_id,
                    input_todays_race_date=datetime.strptime(
                        todays_race_date, "%Y-%m-%d"
                    ).date(),
                )
            ),
        )
        return pd.DataFrame(result.fetchall())


def get_collateral_repository(session: AsyncSession = Depends(database_session)):
    return CollateralRepository(session)
