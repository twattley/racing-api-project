from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..load.data_loader_service import DataLoaderService


def run_load_pipeline(postgres_client: IStorageClient):
    data_loader = DataLoaderService(postgres_client=postgres_client)
    data_loader.load_unioned_results_data()
    data_loader.load_todays_betfair_market_ids()
