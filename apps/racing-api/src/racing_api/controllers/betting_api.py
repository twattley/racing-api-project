from datetime import date
from fastapi import APIRouter, Depends

from racing_api.models.live_bets_status import LiveBetStatus

from ..models.void_bet_request import VoidBetRequest

from ..models.betting_selections import BettingSelection

from ..services.todays_service import TodaysService, get_todays_service
from ..services.feedback_service import FeedbackService, get_feedback_service

router = APIRouter()


@router.post("/betting/selections")
async def store_betting_selections(
    selections: BettingSelection,
    todays_service: TodaysService = Depends(get_todays_service),
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    if selections.race_date == date.today():
        await todays_service.store_betting_selections(selections)
    else:
        await feedback_service.store_betting_selections(selections)


@router.get("/betting/live_selections", response_model=LiveBetStatus)
async def get_live_betting_selections(
    todays_service: TodaysService = Depends(get_todays_service),
):
    return await todays_service.get_live_betting_selections()


@router.post("/betting/live_selections/void_bets")
async def void_betting_selection(
    void_request: VoidBetRequest,
    todays_service: TodaysService = Depends(get_todays_service),
):
    """Cash out and invalidate a specific betting selection."""
    return await todays_service.void_betting_selection(void_request)
