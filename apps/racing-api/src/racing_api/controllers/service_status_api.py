from fastapi import APIRouter, Depends
from racing_api.models.service_status import ServiceStatus
from racing_api.services.service_status_service import (
    ServiceStatusService,
    get_service_status_service,
)

router = APIRouter()


@router.get("/service_status/health_check", response_model=ServiceStatus)
async def get_service_status(
    service: ServiceStatusService = Depends(get_service_status_service),
) -> ServiceStatus:
    return await service.get_service_status()
