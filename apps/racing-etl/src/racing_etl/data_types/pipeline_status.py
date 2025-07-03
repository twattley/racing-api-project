import pandas as pd
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.interfaces.storage_client_interface import IStorageClient
from .pipeline_status_types import PipelineJob, JobStatus


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

    def add_error(self, message: str = "") -> None:
        """Add an error and increment the error count"""
        self.errors += 1
        if message:
            self.error_messages.append({"ERROR": message})
            E(message)
        self._update_status()

    def add_info(self, message: str = "") -> None:
        """Add an informational message"""
        if message:
            self.info_messages.append({"INFO": message})
            I(message)
        self._update_status()

    def mark_success(self) -> None:
        """Mark the job as completed successfully"""
        if self.status == JobStatus.IN_PROGRESS:
            self._update_status()

    def mark_failure(self, message: str = "") -> None:
        """Mark the job as failed"""
        self.status = JobStatus.FAILURE
        if message:
            self.error_messages.append(message)

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
                    "job_name": self.pipeline_stage.job_name,
                    "job_id": self.pipeline_stage.job_id,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "pipeline_stage": self.pipeline_stage.pipeline_stage,
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
                    "job_name": self.pipeline_stage.job_name,
                    "job_id": self.pipeline_stage.job_id,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "pipeline_stage": self.pipeline_stage.pipeline_stage,
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
                    "job_name": self.pipeline_stage.job_name,
                    "job_id": self.pipeline_stage.job_id,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "pipeline_stage": self.pipeline_stage.pipeline_stage,
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
                    "job_name": self.pipeline_stage.job_name,
                    "job_id": self.pipeline_stage.job_id,
                    "stage_id": self.pipeline_stage.stage_id,
                    "source_id": self.pipeline_stage.source_id,
                    "pipeline_stage": self.pipeline_stage.pipeline_stage,
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
            f"pipeline_stage='{self.pipeline_stage.pipeline_stage}', "
            f"status={self.status.value}, "
            f"warnings={self.warnings}, "
            f"errors={self.errors})"
        )

    def __str__(self) -> str:
        return self.get_summary()
