from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..clean.clean_live_tables import CleanTablesService


def run_data_clean_pipeline(storage_client: IStorageClient):
    clean_service = CleanTablesService(storage_client)
    clean_service.run_table_cleanup()
