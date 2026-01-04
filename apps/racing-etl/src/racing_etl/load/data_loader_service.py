import subprocess

from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..data_types.pipeline_status import (
    LoadUnionedData,
    SyncTodaysData,
    check_pipeline_completion,
)
from ..load.generate_query import LoadSQLGenerator


class DataLoaderService:
    def __init__(self, postgres_client: IStorageClient):
        self.postgres_client = postgres_client

    @check_pipeline_completion(LoadUnionedData)  # type: ignore[misc]
    def load_unioned_results_data(self, pipeline_status):
        try:
            sql = LoadSQLGenerator.get_unioned_results_data_upsert_sql()
            self.postgres_client.execute_query(sql)
            pipeline_status.save_to_database()
        except Exception as e:
            pipeline_status.add_error(
                message="Failed to load unioned results data",
                exception=e,
            )
            pipeline_status.save_to_database()
            raise e

    @check_pipeline_completion(SyncTodaysData)  # type: ignore[misc]
    def refresh_data(self, pipeline_status):
        try:
            pipeline_status.add_info("Starting refresh_data script")
            result = subprocess.run(
                [
                    "zsh",
                    str(
                        "/Users/tomwattley/App/racing-api-project/racing-api-project/scripts/sync/refresh_data"
                    ),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                pipeline_status.add_info(f"refresh_data stdout:\n{result.stdout}")
            if result.stderr:
                # psql may write notices to stderr; log them as info
                pipeline_status.add_info(f"refresh_data stderr:\n{result.stderr}")
            pipeline_status.add_info("Finished refresh_data script")
            # Optionally use result.stdout / result.stderr for logging
            pipeline_status.save_to_database()
        except Exception as e:
            # If subprocess failed, try to surface captured output
            if isinstance(e, subprocess.CalledProcessError):
                if e.stdout:
                    pipeline_status.add_info(
                        f"refresh_data stdout (on error):\n{e.stdout}"
                    )
                if e.stderr:
                    pipeline_status.add_info(
                        f"refresh_data stderr (on error):\n{e.stderr}"
                    )
            pipeline_status.add_error(
                message="Failed to run refresh_data script",
                exception=e,
            )
            pipeline_status.save_to_database()
