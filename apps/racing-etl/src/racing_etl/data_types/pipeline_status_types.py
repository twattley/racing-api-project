from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum, IntEnum
from typing import Optional


class JobStatus(Enum):
    """Enum for different job completion states"""

    SUCCESS = "SUCCESS"
    SUCCESS_WITH_WARNINGS = "SUCCESS_WITH_WARNINGS"
    SUCCESS_WITH_ERRORS = "SUCCESS_WITH_ERRORS"
    FAILURE = "FAILURE"
    IN_PROGRESS = "IN_PROGRESS"


class JobId(IntEnum):
    RESULTS_LINKS = 1
    TODAYS_LINKS = 2
    RESULTS_DATA = 3
    RESULTS_DATA_WORLD = 4
    TODAYS_DATA = 5
    COMMENTS_DATA = 6
    COMMENTS_DATA_WORLD = 7
    HISTORICAL_ENTITY_MATCHING = 8
    TODAYS_ENTITY_MATCHING = 9
    HISTORICAL_TRANSFORMATION = 10
    TODAYS_TRANSFORMATION = 11
    RACE_TIMES = 12


class SourceId(IntEnum):
    RACING_POST = 1
    TIMEFORM = 2
    BETFAIR = 3
    JOINED = 4


class StageId(IntEnum):
    INGESTION = 1
    ENTITY_MATCHING = 2
    TRANSFORMATION = 3
    LOAD = 4
    CLEANUP = 5


JobName = {
    JobId.RESULTS_LINKS: "Results Links",
    JobId.TODAYS_LINKS: "Today's Links",
    JobId.RESULTS_DATA: "Results Data",
    JobId.RESULTS_DATA_WORLD: "Results Data (World)",
    JobId.COMMENTS_DATA: "Comments Data",
    JobId.COMMENTS_DATA_WORLD: "Comments Data (World)",
    JobId.HISTORICAL_ENTITY_MATCHING: "Historical Entity Matching",
    JobId.TODAYS_ENTITY_MATCHING: "Today's Entity Matching",
}


@dataclass
class PipelineJob:
    """Data class for pipeline job metadata"""

    job_name: str
    job_id: int
    stage_id: int
    source_id: int
    pipeline_stage: str
    date_processed: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        self.date_processed = self.date_processed or date.today().strftime("%Y-%m-%d")
        self.created_at = self.created_at or datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


@dataclass
class IngestRPResultsLinks(PipelineJob):

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_LINKS]
    job_id: int = JobId.RESULTS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestRPResultsData(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestRPResultsDataWorld(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA_WORLD]
    job_id: int = JobId.RESULTS_DATA_WORLD
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestRPComments(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.COMMENTS_DATA]
    job_id: int = JobId.COMMENTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestRPCommentsWorld(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.COMMENTS_DATA_WORLD]
    job_id: int = JobId.COMMENTS_DATA_WORLD
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestRPTodaysLinks(PipelineJob):

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_LINKS]
    job_id: int = JobId.TODAYS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestRPTodaysData(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST


@dataclass
class IngestTFResultsLinks(PipelineJob):

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_LINKS]
    job_id: int = JobId.RESULTS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM


@dataclass
class IngestTFResultsData(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM


@dataclass
class IngestTFResultsDataWorld(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA_WORLD]
    job_id: int = JobId.RESULTS_DATA_WORLD
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM


@dataclass
class IngestTFTodaysLinks(PipelineJob):

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_LINKS]
    job_id: int = JobId.TODAYS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM


@dataclass
class IngestTFTodaysData(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM


@dataclass
class IngestBFResultsData(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.BETFAIR


@dataclass
class IngestBFTodaysData(PipelineJob):
    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.BETFAIR


@dataclass
class EntityMatchingTodaysTF(PipelineJob):
    """Data class for entity matching job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_ENTITY_MATCHING]
    job_id: int = JobId.TODAYS_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.TIMEFORM


@dataclass
class EntityMatchingHistoricalTF(PipelineJob):
    """Data class for entity matching job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.HISTORICAL_ENTITY_MATCHING]
    job_id: int = JobId.HISTORICAL_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.TIMEFORM


@dataclass
class EntityMatchingTodaysBF(PipelineJob):
    """Data class for entity matching job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_ENTITY_MATCHING]
    job_id: int = JobId.TODAYS_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.BETFAIR


@dataclass
class EntityMatchingHistoricalBF(PipelineJob):
    """Data class for entity matching job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.HISTORICAL_ENTITY_MATCHING]
    job_id: int = JobId.HISTORICAL_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.BETFAIR


@dataclass
class TransformationHistorical(PipelineJob):
    """Data class for historical transformation job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.HISTORICAL_TRANSFORMATION]
    job_id: int = JobId.HISTORICAL_TRANSFORMATION
    stage_id: int = StageId.TRANSFORMATION
    source_id: int = SourceId.JOINED


@dataclass
class TransformationToday(PipelineJob):
    """Data class for today's transformation job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_TRANSFORMATION]
    job_id: int = JobId.TODAYS_TRANSFORMATION
    stage_id: int = StageId.TRANSFORMATION
    source_id: int = SourceId.JOINED


@dataclass
class LoadUnionedData(PipelineJob):
    """Data class for loading unioned results data"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.LOAD
    source_id: int = SourceId.JOINED


@dataclass
class LoadTodaysRaceTimes(PipelineJob):
    """Data class for loading today's race times data"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RACE_TIMES]
    job_id: int = JobId.RACE_TIMES
    stage_id: int = StageId.LOAD
    source_id: int = SourceId.JOINED


@dataclass
class LoadTodaysData(PipelineJob):
    """Data class for loading today's data"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.LOAD
    source_id: int = SourceId.JOINED


@dataclass
class Cleanup(PipelineJob):
    """Data class for cleanup job metadata"""

    def __post_init__(self):
        super().__post_init__()

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.CLEANUP
    source_id: int = SourceId.JOINED
