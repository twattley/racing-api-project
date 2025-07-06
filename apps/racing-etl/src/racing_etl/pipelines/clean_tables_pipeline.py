from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..clean.clean_live_tables import CleanTablesService
from ..data_types.pipeline_status import Cleanup, check_pipeline_completion_standalone


def run_data_clean_pipeline(storage_client: IStorageClient):

    @check_pipeline_completion_standalone(Cleanup)
    def run_table_cleanup(pipeline_status):
        try:
            clean_service = CleanTablesService(storage_client)
            clean_service.run_table_cleanup()
            pipeline_status.save_to_database()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to run table cleanup",
                exception=e,
            )
            pipeline_status.save_to_database()
            raise e

    run_table_cleanup()
