from fastapi import Depends

from ..models.pipeline_status import (
    PipleineStatus
)
from ..repository.etl_status_repository import ETLStatusRepository, get_etl_status_repository
from .base_service import BaseService


class ETLStatusService(BaseService):
    def __init__(
        self,
        etl_status_repository: ETLStatusRepository,
    ):
        self.etl_status_repository = etl_status_repository


    async def get_pipeline_status(self):
        data = await self.etl_status_repository.get_pipeline_status()
        return data


def get_etl_status_service(
    etl_status_repository: ETLStatusRepository = Depends(get_etl_status_repository),
):
    return ETLStatusService(etl_status_repository)
