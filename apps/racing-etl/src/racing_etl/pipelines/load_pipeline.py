from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..load.data_loader_service import DataLoaderService
from ..storage.storage_client import get_storage_client


def run_load_pipeline(
    db_storage_client: IStorageClient, s3_storage_client: IStorageClient
):
    data_loader = DataLoaderService(
        db_storage_client=db_storage_client, s3_storage_client=s3_storage_client
    )
    data_loader.load_unioned_results_data()
    data_loader.load_todays_race_times()
    data_loader.load_todays_data()


if __name__ == "__main__":
    run_load_pipeline(
        db_storage_client=get_storage_client("postgres"),
        s3_storage_client=get_storage_client("s3"),
    )
