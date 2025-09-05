import asyncio
from datetime import datetime, timedelta
import pandas as pd
from fastapi import Depends
from requests import get
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api_helpers.clients.betfair_client import BetFairClient
from racing_api.models.void_bet_request import VoidBetRequest
from ..storage.database_session_manager import database_session
from ..storage.query_generator.race_times import RaceTimesSQLGenerator
from ..storage.query_generator.store_selections import StoreSelectionsSQLGenerator
from ..storage.query_generator.get_live_selections import LiveSelectionsSQLGenerator
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

        await self.session.commit()

    async def get_live_betting_selections(self):
        # Run DB query and sync Betfair call concurrently
        start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        db_task = self.session.execute(
            text(LiveSelectionsSQLGenerator.get_live_selection_sql())
        )
        bf_task = asyncio.to_thread(
            self.betfair_client.get_past_orders_by_date_range, start, end
        )

        db_result, orders = await asyncio.gather(db_task, bf_task)
        selections_df = pd.DataFrame(db_result.fetchall())
        return selections_df, orders

    def cash_out_bets_for_selection(self, void_request: VoidBetRequest) -> pd.DataFrame:
        return self.betfair_client.cash_out_bets_for_selection(
            market_ids=[str(void_request.market_id)],
            selection_ids=[str(void_request.selection_id)],
        )

    async def mark_selection_as_invalid(self, void_request: VoidBetRequest) -> None:
        """Mark a selection as invalid in the live_betting.selections table."""

        invalidation_reason = (
            "Manual Cash Out"
            if void_request.size_matched > 0
            else "Manual Void - No Money Matched"
        )

        query = f"""
            UPDATE live_betting.selections
            SET valid = False,
                invalidated_at = '{datetime.now().replace(microsecond=0, second=0)}',
                invalidated_reason = '{invalidation_reason}'
            WHERE market_id = '{void_request.market_id}' 
            AND selection_id = {void_request.selection_id}
        """

        await self.session.execute(text(query))
        await self.session.commit()


def get_todays_repository(session: AsyncSession = Depends(database_session)):
    return TodaysRepository(session)
