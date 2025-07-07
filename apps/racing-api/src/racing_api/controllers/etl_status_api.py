from fastapi import APIRouter, Depends

from ..models.etl_status import ETLStatus
from ..services.etl_status_service import ETLStatusService, get_etl_status_service

router = APIRouter()


@router.get("/etl_status/pipeline_status")
async def get_pipeline_status(
    service: ETLStatusService = Depends(get_etl_status_service),
) -> ETLStatus:
    return await service.get_pipeline_status()
