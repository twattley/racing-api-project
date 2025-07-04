from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..clean.clean_live_tables import CleanTablesService
from ..data_types.pipeline_status_types import Cleanup
from api_helpers.helpers.logging_config import check_pipeline_completion


def run_data_clean_pipeline(storage_client: IStorageClient):

    @check_pipeline_completion(Cleanup)
    def run_table_cleanup(pipeline_status):
        try:
            clean_service = CleanTablesService(storage_client)
            clean_service.run_table_cleanup()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to run table cleanup",
                exception=e,
            )
            raise e

    run_table_cleanup()
