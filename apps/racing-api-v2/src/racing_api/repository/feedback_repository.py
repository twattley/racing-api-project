from datetime import datetime

import pandas as pd
from fastapi import Depends, HTTPException
from ..storage.query_generator.race_form_graph import RaceFormGraphSQLGenerator
from ..storage.query_generator.race_details import RaceDetailsSQLGenerator
from ..storage.query_generator.horse_race_info import HorseRaceInfoSQLGenerator
from ..storage.query_generator.race_form import RaceFormSQLGenerator
from ..storage.query_generator.race_times import RaceTimesSQLGenerator
from ..storage.query_generator.race_result import ResultsSQLGenerator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.database_session_manager import database_session
from ..storage.query_generator.update_feedback_date import (
    UpdateFeedbackDateSQLGenerator,
)


class FeedbackRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_horse_race_info(self, race_id: int):
        result = await self.session.execute(
            text(HorseRaceInfoSQLGenerator.get_historical_race_form_sql()),
            HorseRaceInfoSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_details(self, race_id: int):
        result = await self.session.execute(
            text(RaceDetailsSQLGenerator.get_race_details_sql()),
            RaceDetailsSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_form_graph(self, race_id: int):
        result = await self.session.execute(
            text(RaceFormGraphSQLGenerator.get_race_form_graph_sql()),
            RaceFormGraphSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_form(self, race_id: int):
        result = await self.session.execute(
            text(
                RaceFormSQLGenerator.get_historical_race_form_sql(input_race_id=race_id)
            ),
            RaceFormSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_race_result_by_id(self, race_id: int):
        result = await self.session.execute(
            text(ResultsSQLGenerator.get_race_results_sql(input_race_id=race_id)),
            ResultsSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())

    async def get_todays_race_times(self):
        result = await self.session.execute(
            text(RaceTimesSQLGenerator.get_todays_feedback_race_times()),
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
