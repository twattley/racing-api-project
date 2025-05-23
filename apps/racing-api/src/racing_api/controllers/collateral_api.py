from fastapi import APIRouter, Depends

from ..models.collateral_form_data import CollateralFormResponse
from ..services.collateral_service import CollateralService, get_collateral_service

router = APIRouter()


@router.get("/collateral/form/by-race-id", response_model=CollateralFormResponse)
async def get_collateral_form_by_id(
    race_id: int,
    race_date: str,
    todays_race_date: str,
    horse_id: int,
    service: CollateralService = Depends(get_collateral_service),
):
    return await service.get_collateral_form_by_id(
        race_date=race_date,
        race_id=race_id,
        todays_race_date=todays_race_date,
        horse_id=horse_id,
    )
