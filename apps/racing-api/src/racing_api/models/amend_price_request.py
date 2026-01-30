from typing import Optional, Union

from .base_model import BaseRaceModel


class AmendPriceRequest(BaseRaceModel):
    """Model for amending the requested price of a betting selection."""

    unique_id: str
    market_id: str
    selection_id: Union[int, str]
    horse_name: str
    market_type: str
    selection_type: str
    race_time: str
    new_requested_odds: float
    size_matched: float
    price_matched: Optional[float] = None
