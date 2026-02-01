from datetime import datetime

import numpy as np
import pandas as pd
from fastapi import Depends

from ..models.betting_results import BettingResult, BettingResults
from ..models.betting_selections import BettingSelection
from ..models.contender_selection import ContenderSelection, ContenderSelectionResponse
from ..models.feedback_date import FeedbackDate
from ..models.race_result import HorsePerformance, RaceResult, RaceResultsResponse
from ..models.race_times import RaceTimeEntry, RaceTimesResponse
from ..repository.feedback_repository import FeedbackRepository, get_feedback_repository
from .base_service import BaseService, BetRequest


class FeedbackService(BaseService):
    def __init__(
        self,
        feedback_repository: FeedbackRepository,
    ):
        super().__init__(feedback_repository)
        self.feedback_repository = feedback_repository

    async def get_todays_race_times(self) -> RaceTimesResponse:
        """Get today's race times"""
        data = await self.feedback_repository.get_todays_race_times()
        data = self._format_todays_races(data)
        races = []
        for course in data["course"].unique():
            course_races = data[data["course"] == course]
            races.append(
                {
                    "course": course,
                    "races": [
                        RaceTimeEntry(**row.to_dict())
                        for _, row in course_races.iterrows()
                    ],
                }
            )
        return RaceTimesResponse(data=races)

    async def get_current_date_today(self) -> FeedbackDate:
        """Get current feedback date"""
        data = await self.feedback_repository.get_current_date_today()
        if data.empty:
            return FeedbackDate(today_date=None)
        return FeedbackDate(**data.iloc[0].to_dict())

    async def store_current_date_today(self, date: str):
        """Store current date"""
        return await self.feedback_repository.store_current_date_today(date)

    async def get_race_result(self, race_id: int) -> RaceResultsResponse:
        """Get race results by race ID"""
        race_data = await self.feedback_repository.get_race_result_info(race_id)
        performance_data = (
            await self.feedback_repository.get_race_result_horse_performance_data(
                race_id
            )
        )
        race_data_record = (
            race_data.to_dict("records")[0] if not race_data.empty else {}
        )
        race_data_record = {str(k): v for k, v in race_data_record.items()}
        return RaceResultsResponse(
            race_id=race_id,
            race_data=RaceResult(**race_data_record),
            horse_performance_data=[
                HorsePerformance(**row.to_dict())
                for _, row in performance_data.iterrows()
            ],
        )

    async def store_betting_selections(self, selections: BettingSelection) -> None:
        """Store betting selections"""
        unique_id = self.create_unique_bet_request_id(
            BetRequest(
                race_id=selections.race_id,
                horse_id=selections.horse_id,
                market=selections.bet_type.market,
                selection_id="feedback",
                market_id="feedback",
                stake_points=(
                    float(selections.stake_points)
                    if selections.stake_points is not None
                    else None
                ),
            )
        )
        payload = self._create_selections(selections, unique_id, "feedback")

        await self.feedback_repository.store_betting_selections(payload)

    async def get_betting_selections_analysis(self) -> BettingResults:
        """Get betting selections analysis"""
        data = await self.feedback_repository.get_betting_selections_analysis()
        processed_data = FeedbackService.process_betting_data(data)
        for i in [
            "running_stake_points_back_win_pnl",
            "running_stake_points_back_place_pnl",
            "running_stake_points_lay_win_pnl",
            "running_stake_points_lay_place_pnl",
            "running_stake_points_total_pnl",
            "running_stake_points_back_win",
            "running_stake_points_back_place",
            "running_stake_points_lay_win",
            "running_stake_points_lay_place",
            "running_stake_points_total",
            "running_roi_back_win",
            "running_roi_back_place",
            "running_roi_lay_win",
            "running_roi_lay_place",
            "running_roi_overall",
            "running_roi_stake_back_win",
            "running_roi_stake_back_place",
            "running_roi_stake_lay_win",
            "running_roi_stake_lay_place",
            "running_roi_overall_stake_points",
        ]:
            processed_data[i] = processed_data[i].fillna(0)
        last_row = (
            processed_data.sort_values("created_at").reset_index(drop=True).tail(1)
        )
        return BettingResults(
            number_of_bets=int(last_row["total_bet_count"].iloc[0]),
            return_on_investment=float(last_row["running_roi_overall"].iloc[0]),
            weighted_return_on_investment=float(
                last_row["running_roi_overall_stake_points"].iloc[0]
            ),
            results=BettingResult.from_dataframe(processed_data),
        )

    @staticmethod
    def add_results_booleans(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add win and place boolean columns based on finishing position and number of runners.
        Equivalent to the results_with_booleans CTE.
        """
        df = df.copy()

        # Win boolean: true if finishing_position = '1'
        df["win"] = df["finishing_position"] == "1"

        # Place boolean based on number of runners
        def calculate_placed(row):
            pos = row["finishing_position"]
            runners = row["number_of_runners"]

            # Convert position to int for comparison
            try:
                pos_int = int(pos)
            except (ValueError, TypeError):
                return False

            # Less than 8 runners: places 1-2
            if runners < 8:
                return pos_int in [1, 2]
            # 8-15 runners: places 1-3
            elif 8 <= runners <= 15:
                return pos_int in [1, 2, 3]
            # 16+ runners: places 1-4
            elif runners >= 16:
                return pos_int in [1, 2, 3, 4]
            else:
                return False

        df["placed"] = df.apply(calculate_placed, axis=1)

        return df

    @staticmethod
    def calculate_profit_loss(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate profit/loss for each bet, both regular and stake-points weighted.
        Equivalent to the profit_loss_calc CTE.

        For LAY bets, we use liability-based P&L:
        - stake_points represents the FIXED LIABILITY (max risk)
        - If horse wins (you lose): lose stake_points
        - If horse loses (you win): win stake_points / (odds - 1)

        This matches the trader's approach where liability is constant regardless of odds.
        """
        df = df.copy()

        def calc_pnl(row):
            selection_type = row["selection_type"]
            market_type = row["market_type"]
            # Force numeric values to float to avoid Decimal/float operations
            betfair_sp = (
                float(row["betfair_sp"]) if row.get("betfair_sp") is not None else 0.0
            )
            win = row["win"]
            placed = row["placed"]
            stake_points = (
                float(row["stake_points"])
                if row.get("stake_points") is not None
                else 0.0
            )
            odds_returned = betfair_sp - 1.0
            multiplier = 0.8  # 80% return on win bets

            # Regular profit/loss calculation
            if selection_type == "BACK" and market_type == "WIN":
                profit_loss = multiplier * odds_returned if win else -1
                profit_loss_stake_points = (
                    stake_points * multiplier * odds_returned if win else -stake_points
                )

            elif selection_type == "BACK" and market_type == "PLACE":
                profit_loss = multiplier * odds_returned if placed else -1
                profit_loss_stake_points = (
                    stake_points * multiplier * odds_returned
                    if placed
                    else -stake_points
                )

            elif selection_type == "LAY" and market_type == "WIN":
                # LAY with fixed liability approach:
                # stake_points = your liability (fixed risk)
                # If horse wins: you lose your liability
                # If horse loses: you win (liability / (odds - 1)) * multiplier
                lay_profit = (
                    (stake_points / odds_returned * multiplier)
                    if odds_returned > 0
                    else 0
                )
                profit_loss = (
                    -odds_returned
                    if win
                    else (1 / odds_returned * multiplier) if odds_returned > 0 else 0
                )
                profit_loss_stake_points = -stake_points if win else lay_profit

            elif selection_type == "LAY" and market_type == "PLACE":
                # Same liability-based approach for place markets
                lay_profit = (
                    (stake_points / odds_returned * multiplier)
                    if odds_returned > 0
                    else 0
                )
                profit_loss = (
                    -odds_returned
                    if placed
                    else (1 / odds_returned * multiplier) if odds_returned > 0 else 0
                )
                profit_loss_stake_points = -stake_points if placed else lay_profit

            else:
                profit_loss = 0
                profit_loss_stake_points = 0

            # Stake calculation
            if selection_type == "BACK":
                level_stake = 1.0
                confidence_stake = stake_points
            elif selection_type == "LAY":
                level_stake = betfair_sp - 1.0
                confidence_stake = (
                    stake_points / (betfair_sp - 1.0) if betfair_sp > 1.0 else 0.0
                )
            else:
                level_stake = 0.0
                confidence_stake = 0.0

            return pd.Series(
                {
                    "profit_loss": profit_loss,
                    "profit_loss_stake_points": profit_loss_stake_points,
                    "level_stake": level_stake,
                    "confidence_stake": confidence_stake,
                }
            )

        pnl_data = df.apply(calc_pnl, axis=1)
        df = pd.concat([df, pnl_data], axis=1)

        return df

    @staticmethod
    def calculate_level_stakes_running_totals(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate running totals and counts for different bet types.
        """
        df = df.copy()
        df = df.sort_values("created_at").reset_index(drop=True)

        # Create masks for different bet types
        back_win_mask = (df["selection_type"] == "BACK") & (df["market_type"] == "WIN")
        back_place_mask = (df["selection_type"] == "BACK") & (
            df["market_type"] == "PLACE"
        )
        lay_win_mask = (df["selection_type"] == "LAY") & (df["market_type"] == "WIN")
        lay_place_mask = (df["selection_type"] == "LAY") & (
            df["market_type"] == "PLACE"
        )

        # Running P&L totals
        df["running_total_back_win_pnl"] = (df["profit_loss"] * back_win_mask).cumsum()
        df["running_total_back_place_pnl"] = (
            df["profit_loss"] * back_place_mask
        ).cumsum()
        df["running_total_lay_win_pnl"] = (df["profit_loss"] * lay_win_mask).cumsum()
        df["running_total_lay_place_pnl"] = (
            df["profit_loss"] * lay_place_mask
        ).cumsum()
        df["running_total_all_bets_pnl"] = df["profit_loss"].cumsum()

        # Running stake totals
        df["running_stake_back_win"] = (df["level_stake"] * back_win_mask).cumsum()
        df["running_stake_back_place"] = (df["level_stake"] * back_place_mask).cumsum()
        df["running_stake_lay_win"] = (df["level_stake"] * lay_win_mask).cumsum()
        df["running_stake_lay_place"] = (df["level_stake"] * lay_place_mask).cumsum()
        df["running_stake_total"] = df["level_stake"].cumsum()

        # Running counts
        df["total_back_win_count"] = back_win_mask.cumsum()
        df["total_back_place_count"] = back_place_mask.cumsum()
        df["total_lay_win_count"] = lay_win_mask.cumsum()
        df["total_lay_place_count"] = lay_place_mask.cumsum()
        df["total_bet_count"] = range(1, len(df) + 1)

        return df

    @staticmethod
    def calculate_weighted_stakes_running_totals(df: pd.DataFrame) -> pd.DataFrame:

        df = df.copy()
        df = df.sort_values("created_at").reset_index(drop=True)

        # Create masks for different bet types
        back_win_mask = (df["selection_type"] == "BACK") & (df["market_type"] == "WIN")
        back_place_mask = (df["selection_type"] == "BACK") & (
            df["market_type"] == "PLACE"
        )
        lay_win_mask = (df["selection_type"] == "LAY") & (df["market_type"] == "WIN")
        lay_place_mask = (df["selection_type"] == "LAY") & (
            df["market_type"] == "PLACE"
        )

        df["running_stake_points_back_win_pnl"] = (
            df["profit_loss_stake_points"] * back_win_mask
        ).cumsum()
        df["running_stake_points_back_place_pnl"] = (
            df["profit_loss_stake_points"] * back_place_mask
        ).cumsum()
        df["running_stake_points_lay_win_pnl"] = (
            df["profit_loss_stake_points"] * lay_win_mask
        ).cumsum()
        df["running_stake_points_lay_place_pnl"] = (
            df["profit_loss_stake_points"] * lay_place_mask
        ).cumsum()
        df["running_stake_points_total_pnl"] = df["profit_loss_stake_points"].cumsum()

        # Running stake-points totals
        df["running_stake_points_back_win"] = (
            df["confidence_stake"] * back_win_mask
        ).cumsum()
        df["running_stake_points_back_place"] = (
            df["confidence_stake"] * back_place_mask
        ).cumsum()
        df["running_stake_points_lay_win"] = (
            df["confidence_stake"] * lay_win_mask
        ).cumsum()
        df["running_stake_points_lay_place"] = (
            df["confidence_stake"] * lay_place_mask
        ).cumsum()
        df["running_stake_points_total"] = df["confidence_stake"].cumsum()

        return df

    @staticmethod
    def calculate_level_stakes_roi_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ROI percentages for different bet types.
        Equivalent to the roi_calculations CTE.
        """
        df = df.copy()

        # Helper function to calculate ROI safely (avoid division by zero)
        def safe_roi(profit, stake):
            return np.where(stake > 0, (profit / stake) * 100, np.nan)

        # Running ROI calculations (as percentages)
        df["running_roi_back_win"] = safe_roi(
            df["running_total_back_win_pnl"], df["running_stake_back_win"]
        ).round(2)
        df["running_roi_back_place"] = safe_roi(
            df["running_total_back_place_pnl"], df["running_stake_back_place"]
        ).round(2)
        df["running_roi_lay_win"] = safe_roi(
            df["running_total_lay_win_pnl"], df["running_stake_lay_win"]
        ).round(2)
        df["running_roi_lay_place"] = safe_roi(
            df["running_total_lay_place_pnl"], df["running_stake_lay_place"]
        ).round(2)
        df["running_roi_overall"] = safe_roi(
            df["running_total_all_bets_pnl"], df["running_stake_total"]
        ).round(2)

        return df

    @staticmethod
    def calculate_weighted_stakes_roi_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate stake-points weighted ROI percentages for different bet types.
        """
        df = df.copy()

        # Helper function to calculate ROI safely (avoid division by zero)
        def safe_roi(profit, stake):
            return np.where(stake > 0, (profit / stake) * 100, np.nan)

        # Running stake-points weighted ROI calculations (as percentages)
        df["running_roi_stake_back_win"] = safe_roi(
            df["running_stake_points_back_win_pnl"], df["running_stake_points_back_win"]
        ).round(2)
        df["running_roi_stake_back_place"] = safe_roi(
            df["running_stake_points_back_place_pnl"],
            df["running_stake_points_back_place"],
        ).round(2)
        df["running_roi_stake_lay_win"] = safe_roi(
            df["running_stake_points_lay_win_pnl"], df["running_stake_points_lay_win"]
        ).round(2)
        df["running_roi_stake_lay_place"] = safe_roi(
            df["running_stake_points_lay_place_pnl"],
            df["running_stake_points_lay_place"],
        ).round(2)
        df["running_roi_overall_stake_points"] = safe_roi(
            df["running_stake_points_total_pnl"], df["running_stake_points_total"]
        ).round(2)

        return df

    @staticmethod
    def process_betting_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Main function to process raw betting data through all calculation steps.
        """
        # Ensure numeric inputs are floats (avoid Decimal/float mix during ops)
        df = df.copy()
        for col in ["stake_points", "betfair_sp"]:
            if col in df.columns:
                try:
                    df[col] = df[col].astype(float)
                except Exception:
                    # Fallback: attempt element-wise conversion
                    df[col] = df[col].apply(
                        lambda v: float(v) if v is not None else np.nan
                    )

        # Apply all transformations in sequence
        df = FeedbackService.add_results_booleans(df)
        df = FeedbackService.calculate_profit_loss(df)
        df = FeedbackService.calculate_level_stakes_running_totals(df)
        df = FeedbackService.calculate_weighted_stakes_running_totals(df)
        df = FeedbackService.calculate_level_stakes_roi_metrics(df)
        df = FeedbackService.calculate_weighted_stakes_roi_metrics(df)

        return df

    async def store_contender_selection(
        self, selection: ContenderSelection
    ) -> ContenderSelectionResponse:
        """Store a contender selection"""
        now = datetime.now()
        payload = {
            "horse_id": selection.horse_id,
            "horse_name": selection.horse_name,
            "race_id": selection.race_id,
            "race_date": selection.race_date,
            "race_time": selection.race_time,
            "status": selection.status,
            "created_at": now,
            "updated_at": now,
        }
        await self.feedback_repository.store_contender_selection(payload)
        return ContenderSelectionResponse(
            success=True,
            message=f"Stored {selection.status} selection for {selection.horse_name}",
        )

    async def get_contender_selections_by_race(self, race_id: int) -> list[dict]:
        """Get all contender selections for a race"""
        df = await self.feedback_repository.get_contender_selections_by_race(race_id)
        if df.empty:
            return []
        return df.to_dict("records")


def get_feedback_service(
    feedback_repository: FeedbackRepository = Depends(get_feedback_repository),
):
    return FeedbackService(feedback_repository)
