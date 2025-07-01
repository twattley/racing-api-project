from api_helpers.clients import get_postgres_client
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..entity_matching.betfair.historical.entity_matcher import (
    BetfairEntityMatcher as HistoricalBetfairEntityMatcher,
)
from ..entity_matching.betfair.historical.generate_query import (
    MatchingBetfairSQLGenerator as HistoricalMatchingBetfairSQLGenerator,
)
from ..entity_matching.betfair.today.entity_matcher import (
    BetfairEntityMatcher as TodaysBetfairEntityMatcher,
)
from ..entity_matching.betfair.today.generate_query import (
    MatchingBetfairSQLGenerator as TodaysMatchingBetfairSQLGenerator,
)
from ..entity_matching.timeform.entity_matcher import TimeformEntityMatcher
from ..entity_matching.timeform.generate_query import MatchingTimeformSQLGenerator
from ..data_types.log_object import LogObject


def run_matching_pipeline(storage_client: IStorageClient):
    tf_entity_matcher = TimeformEntityMatcher(
        storage_client=storage_client,
        sql_generator=MatchingTimeformSQLGenerator,
        log_object=LogObject(
            job_name="timeform",
            pipeline_stage="entity_matching",
            storage_client=storage_client,
        ),
    )
    historical_betfair_entity_matcher = HistoricalBetfairEntityMatcher(
        storage_client=storage_client,
        sql_generator=HistoricalMatchingBetfairSQLGenerator,
        log_object=LogObject(
            job_name="betfair",
            pipeline_stage="historical_entity_matching",
            storage_client=storage_client,
        ),
    )
    todays_betfair_entity_matcher = TodaysBetfairEntityMatcher(
        storage_client=storage_client,
        sql_generator=TodaysMatchingBetfairSQLGenerator,
        log_object=LogObject(
            job_name="betfair",
            pipeline_stage="todays_entity_matching",
            storage_client=storage_client,
        ),
    )

    tf_entity_matcher.run_matching()
    historical_betfair_entity_matcher.run_matching()
    todays_betfair_entity_matcher.run_matching()
