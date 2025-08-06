from collections import defaultdict

from fastapi import Depends

from ..models.etl_status import ETLStatus, PipelineStatus, StageStatus
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

        # Group pipeline status by stage
        stages_dict = defaultdict(list)

        for record in records:
            pipeline_status = PipelineStatus(
                job_id=record["job_id"],
                stage_id=record["stage_id"],
                stage_name=record["stage_name"],
                job_name=record["job_name"],
                source_id=record["source_id"],
                source_name=record["source_name"],
                warnings=record["warnings"],
                errors=record["errors"],
                success_indicator=record["success_indicator"],
                date_processed=record["date_processed"].isoformat(),
            )
            stages_dict[record["stage_id"]].append(pipeline_status)

        # Create stage status objects
        stages = []
        total_jobs = 0
        total_warnings = 0
        total_errors = 0

        for stage_id, jobs in stages_dict.items():
            stage_warnings = sum(job.warnings for job in jobs)
            stage_errors = sum(job.errors for job in jobs)

            stage_status = StageStatus(
                stage_id=stage_id,
                stage_name=jobs[0].stage_name,  # All jobs in stage have same stage_name
                jobs=jobs,
                total_jobs=len(jobs),
                total_warnings=stage_warnings,
                total_errors=stage_errors,
            )
            stages.append(stage_status)

            total_jobs += len(jobs)
            total_warnings += stage_warnings
            total_errors += stage_errors

        # Sort stages by stage_id
        stages.sort(key=lambda x: x.stage_id)

        return ETLStatus(
            stages=stages,
            total_jobs=total_jobs,
            total_warnings=total_warnings,
            total_errors=total_errors,
        )


def get_etl_status_service(
    etl_status_repository: ETLStatusRepository = Depends(get_etl_status_repository),
):
    return ETLStatusService(etl_status_repository)
