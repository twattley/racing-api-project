from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base_model import BaseRaceModel

class BettingResults(BaseRaceModel):
    number_of_bets : int
    return_on_investment : float
    weighted_return_on_investment : float
    results: list[BettingResult] 

class BettingResult(BaseRaceModel):
    unique_id : str
    race_id : int
    race_time : datetime
    race_date : datetime
    horse_id : int
    horse_name : str
    selection_type : str
    market_type : str
    stake_points : float
    betfair_sp : float
    created_at : datetime
    finishing_position : str
    number_of_runners : int
    win : bool
    placed : bool
    profit_loss : float
    profit_loss_stake_points : float
    level_stake : float
    confidence_stake : float
    running_total_back_win_pnl : float
    running_total_back_place_pnl : float
    running_total_lay_win_pnl : float
    running_total_lay_place_pnl : float
    running_total_all_bets_pnl : float
    running_stake_back_win : float
    running_stake_back_place : float
    running_stake_lay_win : float
    running_stake_lay_place : float
    running_stake_total : float
    total_back_win_count : int
    total_back_place_count : int
    total_lay_win_count : int
    total_lay_place_count : int
    total_bet_count : int
    running_stake_points_back_win_pnl : float
    running_stake_points_back_place_pnl : float
    running_stake_points_lay_win_pnl : float
    running_stake_points_lay_place_pnl : float
    running_stake_points_total_pnl : float
    running_stake_points_back_win : float
    running_stake_points_back_place : float
    running_stake_points_lay_win : float
    running_stake_points_lay_place : float
    running_stake_points_total : float
    running_roi_back_win : Optional[float]
    running_roi_back_place : Optional[float]
    running_roi_lay_win : float
    running_roi_lay_place : Optional[float]
    running_roi_overall : float
    running_roi_stake_back_win : Optional[float]
    running_roi_stake_back_place : Optional[float]
    running_roi_stake_lay_win : float
    running_roi_stake_lay_place : Optional[float]
    running_roi_overall_stake_points : float

