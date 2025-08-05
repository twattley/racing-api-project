from datetime import datetime

import pandas as pd
from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.database_session_manager import database_session
from ..storage.query_generator.todays_race_form import TodaysRaceFormSQLGenerator
from ..storage.query_generator.todays_race_times import TodaysRaceTimesSQLGenerator
from ..storage.query_generator.todays_results import TodaysResultsSQLGenerator
from ..storage.query_generator.update_feedback_date import (
    UpdateFeedbackDateSQLGenerator,
)


class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_todays_races(self):
        result = await self.session.execute(
            text(TodaysRaceTimesSQLGenerator.get_todays_feedback_race_times()),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_by_id(self, race_id: int):
        result = await self.session.execute(
            text(
                TodaysRaceFormSQLGenerator.get_todays_feedback_race_form_sql(
                    input_race_id=race_id
                )
            ),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_result_by_id(self, race_id: int):
        result = await self.session.execute(
            text(
                TodaysResultsSQLGenerator.get_todays_race_results(input_race_id=race_id)
            ),
        )
        return pd.DataFrame(result.fetchall())

    async def store_current_date_today(self, date: str):
        try:
            date_only = date.split("T")[0]
            date_object = datetime.strptime(date_only, "%Y-%m-%d").date()

            result = await self.session.execute(
                text(
                    UpdateFeedbackDateSQLGenerator.get_update_feedback_date_sql(
                        input_date=date_object
                    )
                )
            )
            await self.session.commit()

            if result.rowcount > 0:
                return {
                    "status": "success",
                    "message": "Date updated successfully",
                    "code": 200,
                }
            else:
                return {
                    "status": "warning",
                    "message": "No rows were updated",
                    "code": 204,
                }

        except ValueError as ve:
            raise HTTPException(
                status_code=400,
                detail={"message": f"Invalid date format: {str(ve)}", "code": 400},
            )
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=500,
                detail={"message": f"Database error: {str(e)}", "code": 500},
            )
        except Exception as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=500,
                detail={
                    "message": f"An unexpected error occurred: {str(e)}",
                    "code": 500,
                },
            )

    async def get_current_date_today(self):
        result = await self.session.execute(
            text("SELECT * from api.feedback_date"),
        )
        return pd.DataFrame(result.fetchall())


def get_feedback_repository(session: AsyncSession = Depends(database_session)):
    return FeedbackRepository(session)
