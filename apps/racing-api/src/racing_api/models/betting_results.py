from __future__ import annotations
from datetime import datetime
from typing import Optional

from .base_model import BaseRaceModel

class BettingResults(BaseRaceModel):
    number_of_bets : int
    return_on_investment : float
    results: list[BettingResult] 

class BettingResult(BaseRaceModel):
    unique_id : str
    created_at : datetime
    running_total_back_win : Optional[float]
    running_total_back_place : Optional[float]
    running_total_lay_win : Optional[float]
    running_total_lay_place : Optional[float]
    running_total_all_bets : Optional[float]
    running_stake_total : Optional[float]
    running_roi_back_win : Optional[float]
    running_roi_back_place : Optional[float]
    running_roi_lay_win : Optional[float]
    running_roi_lay_place : Optional[float]
    running_roi_overall : Optional[float]
    total_back_win_count : int
    total_back_place_count : int
    total_lay_win_count : int
    total_lay_place_count : int
    total_bet_count : int

