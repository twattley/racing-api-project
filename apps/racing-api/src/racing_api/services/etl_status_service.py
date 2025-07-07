from fastapi import Depends

from ..models.etl_status import ETLStatus

from ..repository.etl_status_repository import (
    ETLStatusRepository,
    get_etl_status_repository,
)
from .base_service import BaseService


class ETLStatusService(BaseService):
    def __init__(
        self,
        etl_status_repository: ETLStatusRepository,
    ):
        self.etl_status_repository = etl_status_repository

    async def get_pipeline_status(self) -> ETLStatus:
        data = await self.etl_status_repository.get_pipeline_status()
        records = data.to_dict(orient="records")
        pipeline_status = [
            {
                "job_id": record["job_id"],
                "stage_id": record["stage_id"],
                "stage_name": record["stage_name"],
                "job_name": record["job_name"],
                "source_id": record["source_id"],
                "source_name": record["source_name"],
                "warnings": record["warnings"],
                "errors": record["errors"],
                "success_indicator": record["success_indicator"],
                "date_processed": record["date_processed"].isoformat(),
            }
            for record in records
        ]
        return ETLStatus(pipeline_status=pipeline_status)


def get_etl_status_service(
    etl_status_repository: ETLStatusRepository = Depends(get_etl_status_repository),
):
    return ETLStatusService(etl_status_repository)
