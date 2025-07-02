from api_helpers.clients import get_postgres_client
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..transform.data_transformer_service import DataTransformation
from ..data_types.log_object import LogObject
from api_helpers.helpers.logging_config import I

def run_transformation_pipeline(storage_client: IStorageClient):
    PIPELINE_STAGE = "transformation"

    transformation_service = DataTransformation(storage_client=storage_client)

    results_data_name = "results_data"
    todays_data_name = "todays_data"
    results_data_name_world = "results_data_world"

    stage_completed = storage_client.check_pipeline_completion(
        job_name=results_data_name,
        pipeline_stage=PIPELINE_STAGE,
    )
    if not stage_completed:
        transformation_service.transform_results_data(
        log_object=LogObject(
            job_name=results_data_name,
            pipeline_stage=PIPELINE_STAGE,
            storage_client=storage_client,
        )
    )
    
    stage_completed = storage_client.check_pipeline_completion(
        job_name=results_data_name_world,
        pipeline_stage=PIPELINE_STAGE,
    )
    if not stage_completed:
        transformation_service.transform_results_data_world(
            log_object=LogObject(
                job_name=results_data_name_world,
                pipeline_stage=PIPELINE_STAGE,
                storage_client=storage_client,
            )
        )

    stage_completed = storage_client.check_pipeline_completion(
        job_name=todays_data_name,
        pipeline_stage=PIPELINE_STAGE,
    )
    if not stage_completed:
        transformation_service.transform_todays_data(
            log_object=LogObject(
                job_name=todays_data_name,
                pipeline_stage=PIPELINE_STAGE,
                storage_client=storage_client,
            )
        )


