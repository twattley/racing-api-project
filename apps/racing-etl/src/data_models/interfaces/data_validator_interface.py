from typing import Protocol

import pandas as pd
from typing import Tuple

from src.data_models.interfaces.schema_model_interface import ISchemaModel

validated_data = Tuple[pd.DataFrame, pd.DataFrame]


class IDataValidator(Protocol):
    def validate_columns(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> validated_data:
        """
        Validate that the input DataFrame contains all required columns.

        Args:
            data (pd.DataFrame): The input data to validate.

        Raises:
            ValueError: If any required columns are missing.

        Example:
            data_validator.validate_columns(input_data)
        """
        ...

    def validate_field_lengths(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> validated_data:
        """
        Validate the field lengths of string columns in the input DataFrame.

        Args:
            data (pd.DataFrame): The input data to validate.

        Returns:
            validated_data: A tuple containing two DataFrames:
                - The first DataFrame contains rows that passed validation.
                - The second DataFrame contains rows that failed validation, with error information.

        Example:
            accepted_df, rejected_df = data_validator.validate_field_lengths(input_data)
        """
        ...

    def validate_non_null_columns(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> validated_data:
        """
        Validate that required non-null columns do not contain null values.

        Args:
            data (pd.DataFrame): The input data to validate.

        Returns:
            validated_data: A tuple containing two DataFrames:
                - The first DataFrame contains rows that passed validation.
                - The second DataFrame contains rows that failed validation, with error information.

        Example:
            accepted_df, rejected_df = data_validator.validate_non_null_columns(input_data)
        """
        ...
