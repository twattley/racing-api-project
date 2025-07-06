from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..data_types.pipeline_status import (
    EntityMatchingHistoricalBF,
    EntityMatchingHistoricalTF,
    EntityMatchingTodaysBF,
    EntityMatchingTodaysTF,
    check_pipeline_completion_standalone,
)
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


def run_matching_pipeline(storage_client: IStorageClient):

    @check_pipeline_completion_standalone(EntityMatchingHistoricalTF)
    def run_historical_tf_entity_matching(pipeline_status):
        historical_tf_entity_matcher = TimeformEntityMatcher(
            storage_client=storage_client,
            matching_type="historical",
            sql_generator=MatchingTimeformSQLGenerator,
            pipeline_status=pipeline_status,
        )
        historical_tf_entity_matcher.run_matching()

    @check_pipeline_completion_standalone(EntityMatchingTodaysTF)
    def run_todays_tf_entity_matching(pipeline_status):
        todays_tf_entity_matcher = TimeformEntityMatcher(
            storage_client=storage_client,
            matching_type="todays",
            sql_generator=MatchingTimeformSQLGenerator,
            pipeline_status=pipeline_status,
        )
        todays_tf_entity_matcher.run_matching()

    @check_pipeline_completion_standalone(EntityMatchingHistoricalBF)
    def run_historical_bf_entity_matching(pipeline_status):
        historical_bf_entity_matcher = HistoricalBetfairEntityMatcher(
            storage_client=storage_client,
            sql_generator=HistoricalMatchingBetfairSQLGenerator,
            pipeline_status=pipeline_status,
        )
        historical_bf_entity_matcher.run_matching()

    @check_pipeline_completion_standalone(EntityMatchingTodaysBF)
    def run_todays_bf_entity_matching(pipeline_status):
        todays_bf_entity_matcher = TodaysBetfairEntityMatcher(
            storage_client=storage_client,
            sql_generator=TodaysMatchingBetfairSQLGenerator,
            pipeline_status=pipeline_status,
        )
        todays_bf_entity_matcher.run_matching()

    # RUN JOBS
    run_historical_tf_entity_matching()
    run_todays_tf_entity_matching()
    run_historical_bf_entity_matching()
    run_todays_bf_entity_matching()
