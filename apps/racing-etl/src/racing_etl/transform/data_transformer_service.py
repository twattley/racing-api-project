from datetime import datetime

import pandas as pd

from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..data_models.data_validator import DataValidator
from ..data_models.interfaces.data_transformer_interface import IDataTransformer
from ..data_models.interfaces.data_validator_interface import IDataValidator
from ..data_models.interfaces.schema_model_interface import ISchemaModel
from ..data_models.schema_model import SchemaModel
from ..data_types.pipeline_status import PipelineStatus
from ..transform.data_transformer import DataTransformer
from ..transform.generate_query import ResultsDataSQLGenerator, TransformSQLGenerator


class DataTransformationService:
    REJECTED_COLUMNS = [
        "unique_id",
        "debug_link",
        "column",
        "error_value",
    ]

    """
    This class is responsible for running the transformation pipeline.
    """

    def __init__(
        self,
        data_validator: IDataValidator,
        schema_model: ISchemaModel,
        storage_client: IStorageClient,
        data_transformer: IDataTransformer,
        pipeline_status: PipelineStatus,
        table_name: str,
    ):
        self.data_validator = data_validator
        self.schema_model = schema_model
        self.storage_client = storage_client
        self.data_transformer = data_transformer
        self.table_name = table_name
        self.pipeline_status = pipeline_status

    def run_transformation(
        self, data: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        self.schema_model.get_schema_details()
        transformed_data = self.data_transformer.transform_data(data)

        validated_data, rejected_data = self.validate_data(
            transformed_data, self.schema_model
        )
        validated_data = self.convert_data_types(validated_data, self.schema_model)
        return validated_data, rejected_data

    def convert_data_types(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> pd.DataFrame:
        data = self._convert_to_integer(data, schema_model)
        data = self._convert_to_numeric(data, schema_model)
        return data

    def _convert_to_integer(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> pd.DataFrame:
        for column in schema_model.integer_columns:
            self.pipeline_status.add_info(f"Converting {column} to integer")
            data[column] = pd.to_numeric(data[column], errors="coerce")
            data[column] = data[column].astype("Int64")
        return data

    def _convert_to_numeric(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> pd.DataFrame:
        for column in schema_model.numeric_columns:
            self.pipeline_status.add_info(f"Converting {column} to numeric")
            data[column] = pd.to_numeric(data[column], errors="coerce")
        return data

    def validate_data(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        accepted_data, null_data = self.data_validator.validate_non_null_columns(
            data, schema_model
        )
        accepted_data, field_lengths_data = self.data_validator.validate_field_lengths(
            accepted_data, schema_model
        )
        rejected_data = pd.concat([null_data, field_lengths_data])
        accepted_data = accepted_data.assign(
            created_at=datetime.now(),
        )
        return (
            accepted_data[self.schema_model.columns],
            rejected_data[self.REJECTED_COLUMNS],
        )

    def _store_todays_data(
        self, accepted_data: pd.DataFrame, rejected_data: pd.DataFrame
    ) -> None:
        table_name = "todays_data"
        self.pipeline_status.add_info(
            f"Storing {len(accepted_data)} rows in {table_name} data"
        )
        self.storage_client.store_data(
            accepted_data, "public", table_name, truncate=True
        )
        if rejected_data.empty:
            self.pipeline_status.add_info("No rejected data in Transform")
        else:
            self.storage_client.store_data(
                rejected_data[self.REJECTED_COLUMNS],
                "data_quality",
                f"{table_name}_rejected",
            )


class DataTransformation:
    REJECTED_COLUMNS = [
        "unique_id",
        "debug_link",
        "column",
        "error_value",
    ]

    def __init__(self, storage_client: IStorageClient, pipeline_status: PipelineStatus):
        self.storage_client = storage_client
        self.pipeline_status = pipeline_status
        self.schema_model = SchemaModel(
            storage_client=self.storage_client,
            schema_name="public",
            table_name="results_data",
        )

    def transform_results_data(self):
        d = DataTransformationService(
            data_validator=DataValidator(),
            schema_model=self.schema_model,
            storage_client=self.storage_client,
            data_transformer=DataTransformer(),
            pipeline_status=self.pipeline_status,
            table_name="results_data",
        )
        data = self.storage_client.fetch_data(
            TransformSQLGenerator.get_results_data_join_sql()
        )
        try:
            accepted_data, rejected_data = d.run_transformation(data)
        except Exception as e:
            self.pipeline_status.add_error(f"Error transforming results_data: {e}")
            self.pipeline_status.save_to_database()
            raise e

        self.storage_client.upsert_data(
            data=accepted_data,
            schema="public",
            table_name="results_data",
            unique_columns=["unique_id"],
            use_base_table=True,
            upsert_procedure=ResultsDataSQLGenerator.get_results_data_upsert_sql(),
        )
        self.storage_client.store_data(
            rejected_data[self.REJECTED_COLUMNS],
            "data_quality",
            "results_data_rejected",
        )

    def transform_results_data_world(self, log_object: PipelineStatus):
        d = DataTransformationService(
            data_validator=DataValidator(),
            schema_model=self.schema_model,
            storage_client=self.storage_client,
            data_transformer=DataTransformer(),
            pipeline_status=self.pipeline_status,
            table_name="results_data",
        )
        data = self.storage_client.fetch_data(
            TransformSQLGenerator.get_results_data_world_join_sql()
        )
        try:
            self.pipeline_status.add_info("Transforming results_data_world")
            accepted_data, rejected_data = d.run_transformation(data)
        except Exception as e:
            self.pipeline_status.add_error(
                f"Error transforming results_data_world: {e}"
            )
            self.pipeline_status.save_to_database()
            raise e

        self.storage_client.upsert_data(
            data=accepted_data,
            schema="public",
            table_name="results_data",
            unique_columns=["unique_id"],
            use_base_table=True,
            upsert_procedure=ResultsDataSQLGenerator.get_results_data_upsert_sql(),
        )
        self.storage_client.store_data(
            rejected_data[self.REJECTED_COLUMNS],
            "data_quality",
            "results_data_rejected",
        )

    def transform_todays_data(self, log_object: PipelineStatus):
        d = DataTransformationService(
            data_validator=DataValidator(),
            schema_model=self.schema_model,
            storage_client=self.storage_client,
            data_transformer=DataTransformer(),
            table_name="todays_data",
        )

        data = self.storage_client.fetch_data(
            TransformSQLGenerator.get_joined_todays_data_sql()
        )
        try:
            accepted_data, rejected_data = d.run_transformation(data)
        except Exception as e:
            log_object.add_error(f"Error transforming todays_data: {e}")
            log_object.save_to_database()
            raise e

        self.storage_client.store_data(
            accepted_data,
            "todays_data",
            "public",
            truncate=True,
        )
        self.storage_client.store_data(
            rejected_data[self.REJECTED_COLUMNS],
            "data_quality",
            "todays_data_rejected",
        )
