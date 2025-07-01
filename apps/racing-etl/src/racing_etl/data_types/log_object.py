from datetime import date, datetime
from enum import Enum
from typing import Optional
import pandas as pd
from api_helpers.helpers.logging_config import I, W

from api_helpers.interfaces.storage_client_interface import IStorageClient


class JobStatus(Enum):
    """Enum for different job completion states"""

    SUCCESS = "SUCCESS"
    SUCCESS_WITH_WARNINGS = "SUCCESS_WITH_WARNINGS"
    SUCCESS_WITH_ERRORS = "SUCCESS_WITH_ERRORS"
    FAILURE = "FAILURE"
    IN_PROGRESS = "IN_PROGRESS"


class LogObject:

    def __init__(
        self,
        job_name: str,
        pipeline_stage: str,
        storage_client: IStorageClient,
        date_processed: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self.job_name = job_name
        self.pipeline_stage = pipeline_stage
        self.storage_client = storage_client
        self.warnings = 0
        self.errors = 0
        self.status = JobStatus.IN_PROGRESS
        self.date_processed = date_processed or date.today().strftime("%Y-%m-%d")
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.warning_messages = []
        self.error_messages = []

    def add_warning(self, message: str = "") -> None:
        """Add a warning and increment the warning count"""
        self.warnings += 1
        if message:
            self.warning_messages.append(message)
            W(message)
        self._update_status()

    def add_error(self, message: str = "") -> None:
        """Add an error and increment the error count"""
        self.errors += 1
        if message:
            self.error_messages.append(message)
            E(message)
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

    def get_summary(self) -> str:
        """Get a summary string of the job execution"""
        return (
            f"Job: {self.job_name} | Stage: {self.pipeline_stage} | "
            f"Status: {self.status.value} | Warnings: {self.warnings} | Errors: {self.errors}"
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convert LogObject to DataFrame for database storage"""
        return pd.DataFrame(
            [
                {
                    "job_name": self.job_name,
                    "pipeline_stage": self.pipeline_stage,
                    "warnings": self.warnings,
                    "errors": self.errors,
                    "success_indicator": self.success_indicator,
                    "date_processed": pd.to_datetime(self.date_processed).date(),
                    "created_at": pd.to_datetime(self.created_at),
                }
            ]
        )

    def save_to_database(self) -> None:
        """
        Save the LogObject to the monitoring.pipeline_success table

        Args:
            storage_client: Instance of IStorageClient for database operations

        """
        self._update_status()
        self.storage_client.store_latest_data(
            data=self.to_dataframe(),
            table="pipeline_success",
            schema="monitoring",
            unique_columns=["job_name", "pipeline_stage"],
        )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, row_index: int = 0) -> "LogObject":
        """
        Create a LogObject from a DataFrame row (useful for loading from database)

        Args:
            df: DataFrame containing pipeline_success data
            row_index: Which row to use (default 0)
        """
        row = df.iloc[row_index]

        # Create the object
        log_obj = cls(
            job_name=row["job_name"],
            pipeline_stage=row["pipeline_stage"],
            date_processed=str(row["date_processed"]),
            created_at=str(row["created_at"]),
        )

        # Set the counts (this will update status automatically)
        log_obj.warnings = int(row["warnings"])
        log_obj.errors = int(row["errors"])

        # Override status based on success_indicator if needed
        if not row["success_indicator"] and log_obj.errors == 0:
            log_obj.status = JobStatus.FAILURE

        return log_obj

    def __repr__(self) -> str:
        return (
            f"LogObject(job_name='{self.job_name}', "
            f"pipeline_stage='{self.pipeline_stage}', "
            f"status={self.status.value}, "
            f"warnings={self.warnings}, "
            f"errors={self.errors})"
        )

    def __str__(self) -> str:
        return self.get_summary()
