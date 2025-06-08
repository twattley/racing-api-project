from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..load.data_loader_service import DataLoaderService


def run_load_pipeline(db_client: IStorageClient):
    data_loader = DataLoaderService(db_client=db_client)
    data_loader.load_unioned_results_data()
    data_loader.load_todays_race_times()
    data_loader.load_todays_data()
