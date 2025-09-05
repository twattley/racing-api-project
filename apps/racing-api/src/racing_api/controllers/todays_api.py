import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from ..models.horse_race_info import RaceDataResponse
from ..models.race_details import RaceDetailsResponse
from ..models.race_form import RaceFormResponse, RaceFormResponseFull
from ..models.race_form_graph import RaceFormGraphResponse
from ..models.race_times import RaceTimesResponse
from ..services.todays_service import TodaysService, get_todays_service
from ..repository.todays_repository import TodaysRepository
from ..storage.database_session_manager import sessionmanager, with_new_session

router = APIRouter()


# SINGLE CALLS --------------------------------------------------------------


@router.get("/today/todays-race-times", response_model=RaceTimesResponse)
async def get_todays_race_times(
    todays_service: TodaysService = Depends(get_todays_service),
):
    data = await todays_service.get_todays_race_times()
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Race times for today are not loaded yet. Please try again later.",
            headers={"Retry-After": "300"},
        )
    return data


# SINGLE CALLS --------------------------------------------------------------


@router.get("/today/horse-race-info/{race_id}", response_model=RaceDataResponse)
async def get_horse_race_info(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    return await todays_service.get_horse_race_info(race_id=race_id)


@router.get("/today/race-details/{race_id}", response_model=RaceDetailsResponse)
async def get_race_details(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    return await todays_service.get_race_details(race_id=race_id)


@router.get("/today/race-form-graph/{race_id}", response_model=RaceFormGraphResponse)
async def get_race_form_graph(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    return await todays_service.get_race_form_graph(race_id=race_id)


@router.get("/today/race-form/{race_id}", response_model=RaceFormResponse)
async def get_race_form(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    return await todays_service.get_race_form(race_id=race_id)


@router.get("/today/race-form/{race_id}/full", response_model=RaceFormResponseFull)
async def get_race_form_full(
    race_id: int,
    todays_service: TodaysService = Depends(get_todays_service),
):
    return await todays_service.get_full_race_data(race_id=race_id)
