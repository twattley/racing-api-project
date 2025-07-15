from datetime import datetime, timedelta

import pandas as pd
from api_helpers.clients import get_betfair_client, get_postgres_client
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.file_utils import S3FilePaths
from api_helpers.helpers.logging_config import I
from api_helpers.helpers.processing_utils import ptr
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.betting_selections import BettingSelections, VoidBetRequest
from ..storage.database_session_manager import database_session

paths = S3FilePaths()


class BettingRepository:
    def __init__(
        self,
        session: AsyncSession,
        postgres_client: PostgresClient,
        betfair_client: BetFairClient,
    ):
        self.session = session
        self.betfair_client = betfair_client
        self.postgres_client = postgres_client

    async def store_betting_selections(
        self, selections: BettingSelections, session_id: int
    ) -> dict:
        race_date = datetime.strptime(selections.race_date, "%Y-%m-%d").date()
        await self.session.execute(text("TRUNCATE TABLE api.betting_selections"))
        race_id = selections.race_id
        for selection in selections.selections:
            horse_id = selection.horse_id
            betting_type = selection.bet_type
            confidence = selection.confidence
            await self.session.execute(
                text(
                    """
                    INSERT INTO api.betting_selections (race_date, race_id, horse_id, betting_type, session_id, confidence, created_at) 
                    VALUES (:race_date, :race_id, :horse_id, :betting_type, :session_id, :confidence, :created_at)
                    """
                ),
                {
                    "race_date": race_date,
                    "race_id": race_id,
                    "horse_id": horse_id,
                    "betting_type": betting_type,
                    "session_id": session_id,
                    "confidence": confidence,
                    "created_at": datetime.now(),
                },
            )
        await self.session.commit()
        await self.session.execute(text("CALL api.update_betting_selections_info()"))
        await self.session.commit()
        return {
            "message": f"Stored {len(selections.selections)} selections for race {selections.race_id}"
        }

    async def store_live_betting_selections(self, data: pd.DataFrame):

        # Hack to ensure the created_at timestamp is always in front of trader
        data["created_at"] = datetime.now().replace(
            microsecond=0, second=0
        ) + timedelta(minutes=2)

        self.postgres_client.store_latest_data(
            data=data,
            schema="live_betting",
            table="selections",
            unique_columns=[
                "race_id",
                "horse_id",
                "market_id",
                "selection_id",
            ],
        )

    async def get_live_betting_selections(self):
        selections, orders = ptr(
            lambda: self.postgres_client.fetch_latest_data(
                schema="live_betting",
                table="selections",
                unique_columns=("unique_id",),
            ),
            lambda: self.betfair_client.get_past_orders_by_date_range(
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            ),
        )
        if selections.empty:
            return pd.DataFrame()

        # Filter out invalid selections (voided bets)
        selections = selections[selections["valid"] == True].copy()

        if selections.empty:
            return pd.DataFrame()

        if orders.empty:
            orders = pd.DataFrame(
                columns=[
                    "bet_outcome",
                    "event_id",
                    "market_id",
                    "price_matched",
                    "profit",
                    "commission",
                    "selection_id",
                    "side",
                ]
            )

        orders["grouped_pnl"] = orders.groupby(
            ["event_id", "market_id", "selection_id"]
        )["profit"].transform("sum")
        return (
            pd.merge(
                selections,
                orders[
                    [
                        "bet_outcome",
                        "event_id",
                        "market_id",
                        "price_matched",
                        "grouped_pnl",
                        "commission",
                        "selection_id",
                        "side",
                    ]
                ],
                on=["selection_id", "market_id"],
                how="left",
            )
            .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
            .rename(columns={"grouped_pnl": "profit"})
            .reset_index(drop=True)
        )

    async def store_market_state(self, data: pd.DataFrame):
        self.postgres_client.store_latest_data(
            data=data,
            schema="live_betting",
            table="market_state",
            unique_columns=[
                "race_id",
                "selection_id",
                "market_id_win",
                "market_id_place",
            ],
            created_at=True,
        )

    async def get_betting_selections_analysis(self):
        result = await self.session.execute(
            text("SELECT * FROM api.betting_selections_info")
        )
        return pd.DataFrame(result.fetchall())

    async def void_betting_selection(self, void_request: VoidBetRequest) -> dict:
        """Cash out a specific betting selection using Betfair API and mark as invalid in database."""

        try:
            cash_out_result = None

            # Check if there's any money matched that needs to be cashed out
            if void_request.size_matched > 0:
                # Step 1: Cash out the bet using Betfair API (only if money is matched)
                I(f"Cashing out bet with £{void_request.size_matched} matched")
                cash_out_result = self.betfair_client.cash_out_bets_for_selection(
                    market_ids=[str(void_request.market_id)],
                    selection_ids=[str(void_request.selection_id)],
                )
            else:
                # No money matched, just mark as invalid without calling Betfair API
                I(
                    f"No money matched (£{void_request.size_matched}), skipping Betfair cash out"
                )

            # Step 2: Update the database to mark the selection as invalid
            await self._mark_selection_as_invalid(void_request)

            return {
                "success": True,
                "message": f"Successfully voided {void_request.selection_type} bet on {void_request.horse_name}"
                + (
                    f" (£{void_request.size_matched} matched)"
                    if void_request.size_matched > 0
                    else " (no money matched)"
                ),
                "betfair_cash_out": (
                    cash_out_result.to_dict("records")
                    if cash_out_result is not None and not cash_out_result.empty
                    else []
                ),
                "database_updated": True,
                "selection_id": void_request.selection_id,
                "market_id": void_request.market_id,
                "size_matched": void_request.size_matched,
            }

        except Exception as e:
            raise Exception(f"Void failed: {str(e)}")

    async def _mark_selection_as_invalid(self, void_request: VoidBetRequest):
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


def get_betting_repository(session: AsyncSession = Depends(database_session)):
    return BettingRepository(session, get_postgres_client(), get_betfair_client())
