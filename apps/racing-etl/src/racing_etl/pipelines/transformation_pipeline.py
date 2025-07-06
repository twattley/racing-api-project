from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..data_types.pipeline_status import (
    TransformationHistorical,
    TransformationToday,
    check_pipeline_completion_standalone,
)
from ..transform.data_transformer_service import DataTransformation


def run_transformation_pipeline(storage_client: IStorageClient):

    @check_pipeline_completion_standalone(TransformationHistorical)
    def run_results_data_transformation(pipeline_status):
        transformation_service = DataTransformation(
            storage_client=storage_client, pipeline_status=pipeline_status
        )
        transformation_service.transform_results_data()

    @check_pipeline_completion_standalone(TransformationHistorical)
    def run_results_data_world_transformation(pipeline_status):
        transformation_service = DataTransformation(
            storage_client=storage_client, pipeline_status=pipeline_status
        )
        transformation_service.transform_results_data_world()

    @check_pipeline_completion_standalone(TransformationToday)
    def run_todays_data_transformation(pipeline_status):
        transformation_service = DataTransformation(
            storage_client=storage_client, pipeline_status=pipeline_status
        )
        transformation_service.transform_todays_data()

    # RUN JOBS
    run_results_data_transformation()
    run_results_data_world_transformation()
    run_todays_data_transformation()
