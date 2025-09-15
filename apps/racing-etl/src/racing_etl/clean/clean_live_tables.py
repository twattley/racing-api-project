from api_helpers.interfaces.storage_client_interface import IStorageClient
from api_helpers.helpers.logging_config import I

class CleanTablesService:
    def __init__(
        self,
        postgres_client: IStorageClient,
    ):
        self.postgres_client = postgres_client

    def run_table_cleanup(self) -> None:
        self._clean_combined_price_data()
        self._clean_updated_price_data()
        self._clean_status_tables()

    def _clean_combined_price_data(self) -> None:
        I("Cleaning old records from live_betting.combined_price_data...")
        self.postgres_client.execute_query(
            "DELETE FROM live_betting.combined_price_data WHERE race_date < CURRENT_DATE"
        )
        I("Old records from live_betting.combined_price_data cleaned.")

    def _clean_updated_price_data(self) -> None:
        I("Cleaning old records from live_betting.updated_price_data...")
        self.postgres_client.execute_query(
            "DELETE FROM live_betting.updated_price_data WHERE race_date < CURRENT_DATE"
        )
        I("Old records from live_betting.updated_price_data cleaned.")

    def _clean_status_tables(self) -> None:
        I("Cleaning old records from monitoring.pipeline_status...")
        self.postgres_client.execute_query(
            """WITH latest_records AS (
                SELECT ctid,
                    ROW_NUMBER() OVER (
                        PARTITION BY job_id, stage_id, source_id 
                        ORDER BY created_at DESC, date_processed DESC
                    ) as rn
                FROM monitoring.pipeline_status
            )
            DELETE FROM monitoring.pipeline_status 
            WHERE ctid IN (
                SELECT ctid FROM latest_records WHERE rn > 1
            );      
            """
        )
        I("Old records from monitoring.pipeline_status cleaned.")
