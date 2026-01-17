from api_helpers.interfaces.storage_client_interface import IStorageClient
from racing_etl.clean.clean_live_tables import CleanTablesService


def run_clean_tables_pipeline(storage_client: IStorageClient):
    clean_tables = CleanTablesService(postgres_client=storage_client)
    clean_tables.run_table_cleanup()
