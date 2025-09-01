from fastapi import APIRouter, Depends
from pytz import UTC

from ..models.betting_selections import BettingSelection
from ..services.betting_service import BettingService, get_betting_service

router = APIRouter()


@router.post("/betting/selections")
async def store_betting_selections(
    selections: BettingSelection,
    betting_service: BettingService = Depends(get_betting_service),
):
    await betting_service.store_betting_selections(selections)


# @router.get("/betting/selections_analysis")
# async def get_betting_selections_analysis(
#     service: BettingService = Depends(get_betting_service),
# ) -> BettingSelectionsAnalysisResponse:
#     return await service.get_betting_selections_analysis()


# @router.get("/betting/live_selections")
# async def get_live_betting_selections(
#     service: BettingService = Depends(get_betting_service),
# ):
#     return await service.get_live_betting_selections()


# @router.post("/betting/live_selections/void_bets")
# async def void_betting_selection(
#     void_request: VoidBetRequest,
#     service: BettingService = Depends(get_betting_service),
# ):
#     """Cash out and invalidate a specific betting selection."""
#     return await service.void_betting_selection(void_request)
