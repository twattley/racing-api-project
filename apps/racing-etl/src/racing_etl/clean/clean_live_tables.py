from api_helpers.helpers.logging_config import I
from api_helpers.interfaces.storage_client_interface import IStorageClient


class CleanTablesService:
    def __init__(
        self,
        postgres_client: IStorageClient,
    ):
        self.postgres_client = postgres_client

    def run_table_cleanup(self) -> None:
        self._clean_combined_price_data()
        self._clean_updated_price_data()

    def _clean_combined_price_data(self) -> None:
        self.postgres_client.execute_query(
            "DELETE FROM live_betting.combined_price_data WHERE race_date < CURRENT_DATE"
        )

    def _clean_updated_price_data(self) -> None:
        self.postgres_client.execute_query(
            """
            INSERT INTO api.historical_selections (
                unique_id,
                race_id,
                race_time,
                race_date,
                horse_id,
                horse_name,
                selection_type,
                market_type,
                market_id,
                selection_id,
                requested_odds,
                valid,
                invalidated_at,
                invalidated_reason,
                size_matched,
                average_price_matched,
                cashed_out,
                fully_matched,
                customer_strategy_ref,
                created_at,
                processed_at
            )
            SELECT 
                unique_id,
                race_id,
                race_time,
                race_date,
                horse_id,
                horse_name,
                selection_type,
                market_type,
                market_id,
                selection_id,
                requested_odds,
                valid,
                invalidated_at,
                invalidated_reason,
                size_matched,
                average_price_matched,
                cashed_out,
                fully_matched,
                customer_strategy_ref,
                created_at,
                processed_at
            FROM live_betting.selections
            WHERE race_date < CURRENT_DATE  -- Only move data from before today
            ON CONFLICT (race_date, market_id, selection_id) 
            DO UPDATE SET
                race_id = EXCLUDED.race_id,
                race_time = EXCLUDED.race_time,
                horse_id = EXCLUDED.horse_id,
                horse_name = EXCLUDED.horse_name,
                selection_type = EXCLUDED.selection_type,
                market_type = EXCLUDED.market_type,
                requested_odds = EXCLUDED.requested_odds,
                valid = EXCLUDED.valid,
                invalidated_at = EXCLUDED.invalidated_at,
                invalidated_reason = EXCLUDED.invalidated_reason,
                size_matched = EXCLUDED.size_matched,
                average_price_matched = EXCLUDED.average_price_matched,
                cashed_out = EXCLUDED.cashed_out,
                fully_matched = EXCLUDED.fully_matched,
                customer_strategy_ref = EXCLUDED.customer_strategy_ref,
                created_at = EXCLUDED.created_at,
                processed_at = EXCLUDED.processed_at;

            DELETE FROM live_betting.selections 
            WHERE race_date < CURRENT_DATE;

            """
        )
