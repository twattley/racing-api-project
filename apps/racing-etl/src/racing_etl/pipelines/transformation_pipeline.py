from api_helpers.interfaces.storage_client_interface import IStorageClient

from api_helpers.clients import get_postgres_client
from ..transform.data_transformer_service import DataTransformation


def run_transformation_pipeline(storage_client: IStorageClient):
    transformation_service = DataTransformation(storage_client)
    transformation_service.transform_results_data()
    transformation_service.transform_todays_data()


if __name__ == "__main__":
    run_transformation_pipeline(get_postgres_client())
