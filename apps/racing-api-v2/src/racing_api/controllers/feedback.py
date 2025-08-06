from fastapi import APIRouter, Depends, HTTPException

from ..models.feedback_date import DateRequest, FeedbackDate
from ..models.horse_race_info import RaceDataResponse
from ..models.race_details import RaceMetadata
from ..models.race_form import RaceFormResponse
from ..models.race_form_graph import RaceFormGraphResponse
from ..models.race_result import RaceResultsResponse
from ..models.race_times import RaceTimesResponse
from ..services.feedback_service import FeedbackService, get_feedback_service

router = APIRouter()


@router.get("/feedback/current-date", response_model=FeedbackDate)
async def get_current_date_today(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get current feedback date"""
    return await feedback_service.get_current_date_today()


@router.post("/feedback/current-date")
async def store_current_date_today(
    date_request: DateRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Store current feedback date"""
    try:
        result = await feedback_service.store_current_date_today(date=date_request.date)
        return result
    except HTTPException as http_exc:
        return {
            "status": "error",
            "message": http_exc.detail["message"],
            "code": http_exc.detail["code"],
        }


@router.get("/feedback/horse-race-info/{race_id}", response_model=RaceDataResponse)
async def get_horse_race_info(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get horse race information by race ID"""
    return await feedback_service.get_horse_race_info(race_id=race_id)


@router.get("/feedback/race-details/{race_id}", response_model=RaceMetadata)
async def get_race_details(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get race details by race ID"""
    return await feedback_service.get_race_details(race_id=race_id)


@router.get("/feedback/race-form-graph/{race_id}", response_model=RaceFormGraphResponse)
async def get_race_form_graph(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get race form graph data by race ID"""
    return await feedback_service.get_race_form_graph(race_id=race_id)


@router.get("/feedback/race-form/{race_id}", response_model=RaceFormResponse)
async def get_race_form(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get race form data by race ID"""
    return await feedback_service.get_race_form(race_id=race_id)


@router.get(
    "/feedback/race-result/{race_id}",
    response_model=RaceResultsResponse,
)
async def get_race_result(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get race results by race ID"""
    return await feedback_service.get_race_result(race_id=race_id)


@router.get("/feedback/todays-race-times", response_model=RaceTimesResponse)
async def get_todays_race_times(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    """Get today's race times"""
    return await feedback_service.get_todays_race_times()
