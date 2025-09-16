import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


from ..storage.query_generator.horse_race_info import HorseRaceInfoSQLGenerator
from ..storage.query_generator.race_details import RaceDetailsSQLGenerator
from ..storage.query_generator.race_form import RaceFormSQLGenerator
from ..storage.query_generator.race_form_graph import RaceFormGraphSQLGenerator


class BaseRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_horse_race_info(self, race_id: int):
        result = await self.session.execute(
            text(HorseRaceInfoSQLGenerator.get_horse_race_info_sql()),
            {"race_id": race_id},
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
            text(RaceFormSQLGenerator.get_historical_race_form_sql()),
            RaceFormSQLGenerator.get_query_params(race_id=race_id),
        )
        return pd.DataFrame(result.fetchall())
