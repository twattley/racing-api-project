# src/models/simulator.py
from typing import List, Optional
from pydantic import BaseModel


class HorseSimulatorInput(BaseModel):
    horse_id: str
    horse_name: str
    low: float
    high: float
    market_win_odds: float
    market_place_odds: float
    official_rating: Optional[int] = None
    weight_carried: Optional[int] = None
    is_hcap: bool | None = None


class SimulatorRaceId(BaseModel):
    race_id: int


class SimulatorRequest(BaseModel):
    horses: List[HorseSimulatorInput]
    race_id: int


class EdgeResult(BaseModel):
    adjusted_odds: float
    market_odds: float
    adjusted_prob: float
    market_prob: float
    edge: float


class StakeResult(BaseModel):
    stake: float
    odds: float
    edge: float
    potential_return: float


class SimulatedOdds(BaseModel):
    horse_id: str
    horse_name: str
    market_win_odds: float
    sim_win_odds: float
    market_place_odds: float
    sim_place_odds: float
    win_edge: float
    place_edge: float


class BetResult(BaseModel):
    horse_id: str
    horse_name: str
    bet_type: str
    bet_market: str
    bet_size: float


class SimulatorResponse(BaseModel):
    simulation_results: List[SimulatedOdds]
    bets: List[BetResult]


class HorseParameters(BaseModel):
    horse_id: str
    horse_name: str
    high: int
    low: int


class SimulatorParametersResponse(BaseModel):
    saved: bool
    simulation_parameters: List[HorseParameters] | None = None
