import traceback
from typing import Optional

import pandas as pd
from api_helpers.helpers.logging_config import D, E, I, W
from api_helpers.interfaces.storage_client_interface import IStorageClient
from api_helpers.clients import get_postgres_client
from functools import wraps
from .pipeline_status_types import (
    JobStatus,
    PipelineJob,
    IngestRPResultsLinksDTO,
    IngestRPResultsDataDTO,
    IngestRPResultsDataWorldDTO,
    IngestRPCommentsDTO,
    IngestRPCommentsWorldDTO,
    IngestRPTodaysLinksDTO,
    IngestRPTodaysDataDTO,
    IngestTFResultsLinksDTO,
    IngestTFResultsDataDTO,
    IngestTFResultsDataWorldDTO,
    IngestTFTodaysLinksDTO,
    IngestTFTodaysDataDTO,
    IngestBFResultsDataDTO,
    IngestBFTodaysDataDTO,
    EntityMatchingTodaysTFDTO,
    EntityMatchingHistoricalTFDTO,
    EntityMatchingTodaysBFDTO,
    EntityMatchingHistoricalBFDTO,
    TransformationHistoricalDTO,
    TransformationTodayDTO,
    LoadUnionedDataDTO,
    LoadTodaysRaceTimesDTO,
    LoadTodaysDataDTO,
    CleanupDTO,
)


class PipelineStatus:

    def __init__(
        self,
        pipeline_stage: PipelineJob,
        storage_client: IStorageClient,
    ):
        self.pipeline_stage = pipeline_stage
        self.storage_client = storage_client
        self.warnings = 0
        self.errors = 0
        self.status = JobStatus.IN_PROGRESS

        self.info_messages = []
        self.warning_messages = []
        self.error_messages = []

    def add_warning(self, message: str = "") -> None:
        """Add a warning and increment the warning count"""
        self.warnings += 1
        if message:
            self.warning_messages.append({"WARNING": message})
            W(message)
        self._update_status()

    def add_error(
        self,
        message: str = "",
        exception: Optional[Exception] = None,
        capture_traceback: bool = True,
    ) -> None:
        """Add an error and increment the error count"""
        self.errors += 1

        # Build flattened error message
        error_parts = []
        if message:
            error_parts.append(message)

        if exception:
            error_parts.append(
                f"Exception: {type(exception).__name__} - {str(exception)}"
            )

        if capture_traceback:
            if exception:
                traceback_str = "".join(
                    traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                )
            else:
                traceback_str = "".join(traceback.format_stack())
            error_parts.append(f"Traceback:\n{traceback_str}")

        flattened_message = " | ".join(error_parts)

        if flattened_message:
            self.error_messages.append({"ERROR": flattened_message})
            E(flattened_message)

        self._update_status()

    def add_info(self, message: str = "") -> None:
        """Add an informational message"""
        if message:
            self.info_messages.append({"INFO": message})
            I(message)
        self._update_status()

    def add_debug(self, message: str = "") -> None:
        """Add an informational message"""
        if message:
            self.info_messages.append({"DEBUG": message})
            D(message)
        self._update_status()

    def mark_success(self) -> None:
        """Mark the job as completed successfully"""
        if self.status == JobStatus.IN_PROGRESS:
            self._update_status()

    def mark_failure(
        self, message: str = "", exception: Optional[Exception] = None
    ) -> None:
        """Mark the job as failed"""
        self.status = JobStatus.FAILURE
        if message or exception:
            # Build flattened error message
            error_parts = []
            if message:
                error_parts.append(message)

            if exception:
                error_parts.append(
                    f"Exception: {type(exception).__name__} - {str(exception)}"
                )
                traceback_str = "".join(
                    traceback.format_exception(
                        type(exception), exception, exception.__traceback__
                    )
                )
                error_parts.append(f"Traceback:\n{traceback_str}")

            flattened_message = " | ".join(error_parts)
            self.error_messages.append({"ERROR": flattened_message})

    def _update_status(self) -> None:
        """Update status based on current error/warning counts"""
        if self.errors > 0:
            self.status = JobStatus.SUCCESS_WITH_ERRORS
        elif self.warnings > 0:
            self.status = JobStatus.SUCCESS_WITH_WARNINGS
        else:
            self.status = JobStatus.SUCCESS

    @property
    def is_successful(self) -> bool:
        """Returns True if job completed successfully (with or without warnings/errors)"""
        return self.status in [
            JobStatus.SUCCESS,
            JobStatus.SUCCESS_WITH_WARNINGS,
            JobStatus.SUCCESS_WITH_ERRORS,
        ]

    @property
    def has_issues(self) -> bool:
        """Returns True if there are any warnings or errors"""
        return self.warnings > 0 or self.errors > 0

    @property
    def success_indicator(self) -> bool:
        """Convert JobStatus to boolean for database compatibility"""
        return self.status in [
            JobStatus.SUCCESS,
            JobStatus.SUCCESS_WITH_WARNINGS,
            JobStatus.SUCCESS_WITH_ERRORS,
        ]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert PipelineStatus to DataFrame for database storage"""
        return pd.DataFrame(
            [
                {
                    "job_id": self.pipeline_stage.job_id,
                    "job_name": self.pipeline_stage.job_name,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "warnings": self.warnings,
                    "errors": self.errors,
                    "success_indicator": self.success_indicator,
                    "date_processed": pd.to_datetime(
                        self.pipeline_stage.date_processed
                    ).date(),
                    "created_at": pd.to_datetime(self.pipeline_stage.created_at),
                }
            ]
        )

    def get_logs_dataframe(self) -> pd.DataFrame:
        """Convert all log messages to DataFrame for database storage"""
        all_logs = []

        # Process info messages
        for msg in self.info_messages:
            all_logs.append(
                {
                    "job_id": self.pipeline_stage.job_id,
                    "job_name": self.pipeline_stage.job_name,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "log_level": "INFO",
                    "message": msg.get("INFO", ""),
                    "date_processed": pd.to_datetime(
                        self.pipeline_stage.date_processed
                    ).date(),
                    "created_at": pd.to_datetime(self.pipeline_stage.created_at),
                }
            )

        # Process warning messages
        for msg in self.warning_messages:
            all_logs.append(
                {
                    "job_id": self.pipeline_stage.job_id,
                    "job_name": self.pipeline_stage.job_name,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "log_level": "WARNING",
                    "message": msg.get("WARNING", ""),
                    "date_processed": pd.to_datetime(
                        self.pipeline_stage.date_processed
                    ).date(),
                    "created_at": pd.to_datetime(self.pipeline_stage.created_at),
                }
            )

        # Process error messages
        for msg in self.error_messages:
            all_logs.append(
                {
                    "job_id": self.pipeline_stage.job_id,
                    "job_name": self.pipeline_stage.job_name,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "log_level": "ERROR",
                    "message": msg.get("ERROR", ""),
                    "date_processed": pd.to_datetime(
                        self.pipeline_stage.date_processed
                    ).date(),
                    "created_at": pd.to_datetime(self.pipeline_stage.created_at),
                }
            )

        return pd.DataFrame(all_logs) if all_logs else pd.DataFrame()

    def save_to_database(self) -> None:
        """
        Save the PipelineStatus to the monitoring.pipeline_success table
        and logs to monitoring.pipeline_logs table
        """
        self._update_status()
        I(repr(self))

        # Save pipeline status
        self.storage_client.store_data(
            data=self.to_dataframe(),
            table="pipeline_success",
            schema="monitoring",
        )

        # Save logs if any exist
        logs_df = self.get_logs_dataframe()
        if not logs_df.empty:
            self.storage_client.store_data(
                data=logs_df,
                table="pipeline_logs",
                schema="monitoring",
            )

    def __repr__(self) -> str:
        return (
            f"PipelineStatus(job_name='{self.pipeline_stage.job_name}', "
            f"status={self.status.value}, "
            f"warnings={self.warnings}, "
            f"errors={self.errors})"
        )


def fetch_pipeline_status(pipeline_status: PipelineStatus) -> bool:

    D(f"Checking pipeline completion for {pipeline_status}")

    storage_client = get_postgres_client()

    pipeline_status = storage_client.fetch_data(
        query=f"""
            SELECT *
            FROM monitoring.pipeline_status
            WHERE job_id = '{pipeline_status.pipeline_stage.job_id}'
            AND stage_id = '{pipeline_status.pipeline_stage.stage_id}'
            AND source_id = '{pipeline_status.pipeline_stage.source_id}'
            AND success_indicator = TRUE
            AND date_processed = CURRENT_DATE
            LIMIT 1;
        """
    )

    if pipeline_status.empty:
        I(
            f"Pipeline {pipeline_status.pipeline_stage.job_name} at stage {pipeline_status.pipeline_stage.stage_id} is not completed today."
        )
        return False
    else:
        I(
            f"Pipeline {pipeline_status.pipeline_stage.job_name} at stage {pipeline_status.pipeline_stage.stage_id} is already completed today. Skipping."
        )
        return True


def check_pipeline_completion(pipeline_status: PipelineJob):
    """Decorator to check if a pipeline stage is already completed before executing the method."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            stage_completed = fetch_pipeline_status(pipeline_status=pipeline_status)
            if stage_completed:
                return

            return func(self, pipeline_status, *args, **kwargs)

        return wrapper

    return decorator


storage_client = get_postgres_client()
IngestRPResultsLinks = PipelineStatus(IngestRPResultsLinksDTO, storage_client)
IngestRPResultsData = PipelineStatus(IngestRPResultsDataDTO, storage_client)
IngestRPResultsDataWorld = PipelineStatus(IngestRPResultsDataWorldDTO, storage_client)
IngestRPComments = PipelineStatus(IngestRPCommentsDTO, storage_client)
IngestRPCommentsWorld = PipelineStatus(IngestRPCommentsWorldDTO, storage_client)
IngestRPTodaysLinks = PipelineStatus(IngestRPTodaysLinksDTO, storage_client)
IngestRPTodaysData = PipelineStatus(IngestRPTodaysDataDTO, storage_client)
IngestTFResultsLinks = PipelineStatus(IngestTFResultsLinksDTO, storage_client)
IngestTFResultsData = PipelineStatus(IngestTFResultsDataDTO, storage_client)
IngestTFResultsDataWorld = PipelineStatus(IngestTFResultsDataWorldDTO, storage_client)
IngestTFTodaysLinks = PipelineStatus(IngestTFTodaysLinksDTO, storage_client)
IngestTFTodaysData = PipelineStatus(IngestTFTodaysDataDTO, storage_client)
IngestBFResultsData = PipelineStatus(IngestBFResultsDataDTO, storage_client)
IngestBFTodaysData = PipelineStatus(IngestBFTodaysDataDTO, storage_client)
EntityMatchingTodaysTF = PipelineStatus(EntityMatchingTodaysTFDTO, storage_client)
EntityMatchingHistoricalTF = PipelineStatus(
    EntityMatchingHistoricalTFDTO, storage_client
)
EntityMatchingTodaysBF = PipelineStatus(EntityMatchingTodaysBFDTO, storage_client)
EntityMatchingHistoricalBF = PipelineStatus(
    EntityMatchingHistoricalBFDTO, storage_client
)
TransformationHistorical = PipelineStatus(TransformationHistoricalDTO, storage_client)
TransformationToday = PipelineStatus(TransformationTodayDTO, storage_client)
LoadUnionedData = PipelineStatus(LoadUnionedDataDTO, storage_client)
LoadTodaysRaceTimes = PipelineStatus(LoadTodaysRaceTimesDTO, storage_client)
LoadTodaysData = PipelineStatus(LoadTodaysDataDTO, storage_client)
Cleanup = PipelineStatus(CleanupDTO, storage_client)
