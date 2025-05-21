from typing import List

from fastapi import APIRouter, Depends, HTTPException

from src.models.feedback_date import DateRequest, TodaysFeedbackDateResponse
from src.models.feedback_result import (
    TodaysRacesResultWithSimulationResponse,
)
from src.models.form_data import InputRaceFilters, TodaysRaceFormData
from src.models.todays_race_times import TodaysRacesResponse
from ..services.feedback_service import FeedbackService, get_feedback_service


router = APIRouter()


@router.get(
    "/feedback/todays-races/current-date", response_model=TodaysFeedbackDateResponse
)
async def get_current_date_today(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    data = await feedback_service.get_current_date_today()
    return {
        "today_date": data["today_date"].astype(str).iloc[0],
        "success": True,
        "message": "Date fetched successfully",
    }


@router.post("/feedback/todays-races/selected-date")
async def store_current_date_today(
    date_request: DateRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    try:
        result = await feedback_service.store_current_date_today(date=date_request.date)
        return result
    except HTTPException as http_exc:
        return {
            "status": "error",
            "message": http_exc.detail["message"],
            "code": http_exc.detail["code"],
        }


@router.get("/feedback/todays-races/by-date", response_model=List[TodaysRacesResponse])
async def get_todays_races(
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_todays_races()


@router.get("/feedback/todays-races/by-race-id", response_model=TodaysRaceFormData)
async def get_race_by_id(
    filters: InputRaceFilters = Depends(),
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_by_id(filters)


@router.get(
    "/feedback/todays-races/by-race-id-and-date",
    response_model=TodaysRaceFormData,
)
async def get_race_by_id_and_date(
    filters: InputRaceFilters = Depends(),
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_by_id_and_date(filters)


@router.get(
    "/feedback/todays-races/result/by-race-id",
    response_model=List[TodaysRacesResultWithSimulationResponse],
)
async def get_race_result_by_id(
    race_id: int,
    feedback_service: FeedbackService = Depends(get_feedback_service),
):
    return await feedback_service.get_race_result_by_id(race_id=race_id)
