from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class LogObject:

    job_name: str
    pipeline_stage: str
    warnings: int
    errors: int
    success_indicator: bool
    date_processed: datetime = date.today().strftime("%Y-%m-%d")
    created_at: datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
