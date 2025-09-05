from typing import Optional, Union

from .base_model import BaseRaceModel


class VoidBetRequest(BaseRaceModel):
    """Model for voiding/cashing out a specific bet selection."""

    market_id: str
    selection_id: Union[int, str]
    horse_name: str
    market_type: str
    selection_type: str
    race_time: str
    bet_id: str
    requested_odds: float
    size_matched: float
    price_matched: Optional[float] = None
