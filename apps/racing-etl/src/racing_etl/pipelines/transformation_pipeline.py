from api_helpers.clients import get_postgres_client
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..transform.data_transformer_service import DataTransformation
from ..data_types.log_object import LogObject


def run_transformation_pipeline(storage_client: IStorageClient, log_object: LogObject):
    transformation_service = DataTransformation(storage_client=storage_client)
    transformation_service.transform_results_data(
        log_object=LogObject(
            job_name="transform_results_data",
            pipeline_stage="transformation_pipeline",
            storage_client=storage_client,
        )
    )
    transformation_service.transform_results_data_world(
        log_object=LogObject(
            job_name="transform_results_data_world",
            pipeline_stage="transformation_pipeline",
            storage_client=storage_client,
        )
    )
    transformation_service.transform_todays_data(
        log_object=LogObject(
            job_name="transform_todays_data",
            pipeline_stage="transformation_pipeline",
            storage_client=storage_client,
        )
    )
