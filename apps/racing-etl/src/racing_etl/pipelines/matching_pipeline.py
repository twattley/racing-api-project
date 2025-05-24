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


def run_matching_pipeline(storage_client: IStorageClient):
    tf_entity_matcher = TimeformEntityMatcher(
        storage_client, MatchingTimeformSQLGenerator
    )
    historical_betfair_entity_matcher = HistoricalBetfairEntityMatcher(
        storage_client, HistoricalMatchingBetfairSQLGenerator
    )
    todays_betfair_entity_matcher = TodaysBetfairEntityMatcher(
        storage_client, TodaysMatchingBetfairSQLGenerator
    )

    tf_entity_matcher.run_matching()
    historical_betfair_entity_matcher.run_matching()
    todays_betfair_entity_matcher.run_matching()


if __name__ == "__main__":
    storage_client = get_postgres_client()
    run_matching_pipeline(storage_client)
