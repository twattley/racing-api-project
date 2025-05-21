from datetime import datetime

import pandas as pd
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.storage.database_session_manager import database_session

logger = logging.getLogger(__name__)


class SimulatorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def store_simulation_odds(
        self, simulation_results: pd.DataFrame, race_id: int
    ):
        async with self.session.begin():
            await self.session.execute(
                text("DELETE FROM simulation.bets WHERE race_id = :race_id"),
                {"race_id": str(race_id)},
            )
            for row in simulation_results.itertuples():
                await self.session.execute(
                    text(
                        """
                        INSERT INTO simulation.bets
                          (
                            race_id,
                            horse_id,
                            horse_name,
                            bet_type,
                            bet_market,
                            bet_size,
                            created_at
                        ) VALUES (
                            :race_id, 
                            :horse_id, 
                            :horse_name, 
                            :bet_type,
                            :bet_market,
                            :bet_size,
                            :created_at
                        )
                    """
                    ),
                    {
                        "race_id": str(race_id),
                        "horse_id": row.horse_id,
                        "horse_name": row.horse_name,
                        "bet_type": row.bet_type,
                        "bet_market": row.bet_market,
                        "bet_size": row.bet_size,
                        "created_at": datetime.now(),
                    },
                )

            await self.session.execute(text("CALL simulation.insert_individual_bets()"))
            await self.session.execute(text("CALL simulation.insert_race_bets()"))

    async def store_simulation_parameters(self, data: pd.DataFrame):
        race_id = data["race_id"].iloc[0]

        async with self.session.begin():
            await self.session.execute(
                text(
                    "DELETE FROM simulation.stored_parameters WHERE race_id = :race_id"
                ),
                {"race_id": race_id},
            )
            for row in data.itertuples():
                await self.session.execute(
                    text(
                        """
                        INSERT INTO simulation.stored_parameters (
                            race_id, 
                            horse_id, 
                            horse_name, 
                            low,
                            high,
                            created_at
                        ) VALUES (
                            :race_id, 
                            :horse_id, 
                            :horse_name, 
                            :low,
                            :high,
                            :created_at
                        )
                    """
                    ),
                    {
                        "race_id": row.race_id,
                        "horse_id": row.horse_id,
                        "horse_name": row.horse_name,
                        "low": row.low,
                        "high": row.high,
                        "created_at": datetime.now(),
                    },
                )

    async def get_simulation_parameters(self, race_id: int):
        result = await self.session.execute(
            text(
                """
                SELECT 
                    horse_id, 
                    horse_name, 
                    low,
                    high
                FROM simulation.stored_parameters 
                WHERE race_id = :race_id
                """
            ),
            {"race_id": race_id},
        )
        return pd.DataFrame(result.fetchall())


def get_simulator_repository(session: AsyncSession = Depends(database_session)):
    return SimulatorRepository(session)
