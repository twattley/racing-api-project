from datetime import date, datetime

from .base_entity import BaseEntity


class PipelineStatus(BaseEntity):
    job_id: int
    stage_id: int
    stage_name: str
    job_name: str
    source_id: int
    source_name: str
    warnings: int
    errors: int
    success_indicator: bool
    date_processed: datetime | date


class StageStatus(BaseEntity):
    stage_id: int
    stage_name: str
    jobs: list[PipelineStatus]
    total_jobs: int
    total_warnings: int
    total_errors: int


class ETLStatus(BaseEntity):
    stages: list[StageStatus]
    total_jobs: int
    total_warnings: int
    total_errors: int
