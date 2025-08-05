from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..models.form_data import InputRaceFilters, TodaysRaceFormData
from ..models.todays_race_times import TodaysRacesResponse
from ..services.todays_service import TodaysService, get_todays_service

router = APIRouter()


@router.get("/today/todays-races/by-date", response_model=List[TodaysRacesResponse])
def get_todays_races(
    today_service: TodaysService = Depends(get_todays_service),
):
    return today_service.get_todays_races()


@router.get("/today/todays-races/by-race-id", response_model=TodaysRaceFormData)
def get_race_by_id(
    filters: InputRaceFilters = Depends(),
    today_service: TodaysService = Depends(get_todays_service),
):
    data = today_service.get_race_by_id(filters=filters)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "error",
                "message": f"No data found for race_id: {filters.race_id}",
                "code": 404,
            },
        )
    return data
