from datetime import date

from fastapi import APIRouter, Depends
from racing_api.models.betting_results import BettingResults
from racing_api.models.live_bets_status import LiveBetStatus

from ..models.betting_selections import BettingSelection
from ..models.contender_selection import (
    ContenderSelection,
    ContenderSelectionResponse,
    ContenderValuesResponse,
)
from ..models.void_bet_request import VoidBetRequest
from ..services.feedback_service import FeedbackService, get_feedback_service
from ..services.todays_service import TodaysService, get_todays_service

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


@router.get("/betting/selections_analysis", response_model=BettingResults)
async def get_betting_selections_analysis(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_betting_selections_analysis()


@router.post("/betting/contender_selections", response_model=ContenderSelectionResponse)
async def store_contender_selection(
    selection: ContenderSelection,
    todays_service: TodaysService = Depends(get_todays_service),
):
    """Store a contender/not-contender selection for a horse."""
    return await todays_service.store_contender_selection(selection)


@router.get("/betting/contender_selections/{race_id}")
async def get_contender_selections(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    """Get all contender selections for a specific race."""
    return await todays_service.get_contender_selections_by_race(race_id)


@router.delete("/betting/contender_selections/{race_id}/{horse_id}")
async def delete_contender_selection(
    race_id: int,
    horse_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    """Delete a contender selection for a specific horse in a race."""
    return await todays_service.delete_contender_selection(race_id, horse_id)


@router.get(
    "/betting/contender_values/{race_id}", response_model=ContenderValuesResponse
)
async def get_contender_values(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    """
    Calculate and return value percentages for contenders in a race.

    Returns the calculated value for each horse marked as a contender,
    based on blending equal probability with normalized market probability.
    """
    return await todays_service.get_contender_values(race_id)
