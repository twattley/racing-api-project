from dataclasses import dataclass
from datetime import datetime
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
    UNIONED_RESULTS_DATA = 13
    TODAYS_LIVE_DATA = 14
    CLEANUP = 15


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
    JobId.TODAYS_LINKS: "Todays Links",
    JobId.TODAYS_DATA: "Todays Data",
    JobId.RESULTS_DATA: "Results Data",
    JobId.RESULTS_DATA_WORLD: "Results Data (World)",
    JobId.COMMENTS_DATA: "Comments Data",
    JobId.COMMENTS_DATA_WORLD: "Comments Data (World)",
    JobId.HISTORICAL_ENTITY_MATCHING: "Historical Entity Matching",
    JobId.TODAYS_ENTITY_MATCHING: "Todays Entity Matching",
    JobId.HISTORICAL_TRANSFORMATION: "Historical Transformation",
    JobId.TODAYS_TRANSFORMATION: "Todays Transformation",
    JobId.RACE_TIMES: "Race Times",
    JobId.UNIONED_RESULTS_DATA: "Unioned Results Data",
    JobId.TODAYS_LIVE_DATA: "Todays Live Data",
    JobId.CLEANUP: "Cleanup",
}


@dataclass
class PipelineJob:
    """Data class for pipeline job metadata"""

    job_name: str
    job_id: int
    stage_id: int
    source_id: int
    date_processed: Optional[str] = datetime.now().strftime("%Y-%m-%d")
    created_at: Optional[str] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class IngestRPResultsLinksDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_LINKS]
    job_id: int = JobId.RESULTS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestRPResultsDataDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestRPResultsDataWorldDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_DATA_WORLD]
    job_id: int = JobId.RESULTS_DATA_WORLD
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestRPCommentsDTO(PipelineJob):

    job_name: str = JobName[JobId.COMMENTS_DATA]
    job_id: int = JobId.COMMENTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestRPCommentsWorldDTO(PipelineJob):

    job_name: str = JobName[JobId.COMMENTS_DATA_WORLD]
    job_id: int = JobId.COMMENTS_DATA_WORLD
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestRPTodaysLinksDTO(PipelineJob):

    job_name: str = JobName[JobId.TODAYS_LINKS]
    job_id: int = JobId.TODAYS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestRPTodaysDataDTO(PipelineJob):

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.RACING_POST

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestTFResultsLinksDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_LINKS]
    job_id: int = JobId.RESULTS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestTFResultsDataDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestTFResultsDataWorldDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_DATA_WORLD]
    job_id: int = JobId.RESULTS_DATA_WORLD
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestTFTodaysLinksDTO(PipelineJob):

    job_name: str = JobName[JobId.TODAYS_LINKS]
    job_id: int = JobId.TODAYS_LINKS
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestTFTodaysDataDTO(PipelineJob):

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestBFResultsDataDTO(PipelineJob):

    job_name: str = JobName[JobId.RESULTS_DATA]
    job_id: int = JobId.RESULTS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.BETFAIR

    def __post_init__(self):
        super().__post_init__()


@dataclass
class IngestBFTodaysDataDTO(PipelineJob):

    job_name: str = JobName[JobId.TODAYS_DATA]
    job_id: int = JobId.TODAYS_DATA
    stage_id: int = StageId.INGESTION
    source_id: int = SourceId.BETFAIR

    def __post_init__(self):
        super().__post_init__()


@dataclass
class EntityMatchingTodaysTFDTO(PipelineJob):
    """Data class for entity matching job metadata"""

    job_name: str = JobName[JobId.TODAYS_ENTITY_MATCHING]
    job_id: int = JobId.TODAYS_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class EntityMatchingHistoricalTFDTO(PipelineJob):
    """Data class for entity matching job metadata"""

    job_name: str = JobName[JobId.HISTORICAL_ENTITY_MATCHING]
    job_id: int = JobId.HISTORICAL_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.TIMEFORM

    def __post_init__(self):
        super().__post_init__()


@dataclass
class EntityMatchingTodaysBFDTO(PipelineJob):
    """Data class for entity matching job metadata"""

    job_name: str = JobName[JobId.TODAYS_ENTITY_MATCHING]
    job_id: int = JobId.TODAYS_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.BETFAIR

    def __post_init__(self):
        super().__post_init__()


@dataclass
class EntityMatchingHistoricalBFDTO(PipelineJob):
    """Data class for entity matching job metadata"""

    job_name: str = JobName[JobId.HISTORICAL_ENTITY_MATCHING]
    job_id: int = JobId.HISTORICAL_ENTITY_MATCHING
    stage_id: int = StageId.ENTITY_MATCHING
    source_id: int = SourceId.BETFAIR

    def __post_init__(self):
        super().__post_init__()


@dataclass
class TransformationHistoricalDTO(PipelineJob):
    """Data class for historical transformation job metadata"""

    job_name: str = JobName[JobId.HISTORICAL_TRANSFORMATION]
    job_id: int = JobId.HISTORICAL_TRANSFORMATION
    stage_id: int = StageId.TRANSFORMATION
    source_id: int = SourceId.JOINED

    def __post_init__(self):
        super().__post_init__()


@dataclass
class TransformationTodayDTO(PipelineJob):
    """Data class for today's transformation job metadata"""

    job_name: str = JobName[JobId.TODAYS_TRANSFORMATION]
    job_id: int = JobId.TODAYS_TRANSFORMATION
    stage_id: int = StageId.TRANSFORMATION
    source_id: int = SourceId.JOINED

    def __post_init__(self):
        super().__post_init__()


@dataclass
class LoadUnionedDataDTO(PipelineJob):
    """Data class for loading unioned results data"""

    job_name: str = JobName[JobId.UNIONED_RESULTS_DATA]
    job_id: int = JobId.UNIONED_RESULTS_DATA
    stage_id: int = StageId.LOAD
    source_id: int = SourceId.JOINED

    def __post_init__(self):
        super().__post_init__()


@dataclass
class LoadTodaysRaceTimesDTO(PipelineJob):
    """Data class for loading today's race times data"""

    job_name: str = JobName[JobId.RACE_TIMES]
    job_id: int = JobId.RACE_TIMES
    stage_id: int = StageId.LOAD
    source_id: int = SourceId.JOINED

    def __post_init__(self):
        super().__post_init__()


@dataclass
class LoadTodaysDataDTO(PipelineJob):
    """Data class for loading today's data"""

    job_name: str = JobName[JobId.TODAYS_LIVE_DATA]
    job_id: int = JobId.TODAYS_LIVE_DATA
    stage_id: int = StageId.LOAD
    source_id: int = SourceId.JOINED

    def __post_init__(self):
        super().__post_init__()


@dataclass
class CleanupDTO(PipelineJob):
    """Data class for cleanup job metadata"""

    job_name: str = JobName[JobId.CLEANUP]
    job_id: int = JobId.CLEANUP
    stage_id: int = StageId.CLEANUP
    source_id: int = SourceId.JOINED

    def __post_init__(self):
        super().__post_init__()
