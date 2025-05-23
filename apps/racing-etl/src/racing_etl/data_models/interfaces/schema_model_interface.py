from typing import Protocol

import pandas as pd
from api_helpers.interfaces.storage_client_interface import IStorageClient


class ISchemaModel(Protocol):
    def __init__(
        self, storage_client: IStorageClient, schema_name: str, table_name: str
    ):
        self.storage_client = storage_client
        self.schema_name = schema_name
        self.table_name = table_name
        self.character_lengths = {}
        self.columns = []
        self.non_null_columns = []
        self.integer_columns = []
        self.numeric_columns = []

        """
        Initialize the SchemaModel.

        Args:
            storage_client (IStorageClient): The storage client to use for database operations.
            schema_name (str): The name of the database schema.
            table_name (str): The name of the table within the schema.

        Example:
            schema_model = SchemaModel(my_storage_client, "public", "users")
        """
        ...

    def get_schema_details(self):
        """
        Retrieve and store schema details including character lengths, columns, and non-null columns.

        Example:
            schema_model.get_schema_details()
            self.character_lengths = self.get_character_lengths()
            self.columns = self.get_columns()
            self.non_null_columns = self.get_non_null_columns()
        """
        ...

    def get_data_schema(self) -> pd.DataFrame:
        """
        Fetch the data schema from the database.

        Returns:
            DataFrame: A DataFrame containing column names and data types.

        Example:
            schema_data = schema_model.get_data_schema()
        """
        ...

    def get_character_lengths(self) -> dict[str, int]:
        """
        Extract character lengths for varchar columns from the data schema.

        Returns:
            dict: A dictionary mapping column names to their maximum character lengths.

        Example:
            char_lengths = schema_model.get_character_lengths()
        """
        ...

    def get_columns(self) -> list[str]:
        """
        Retrieve all column names for the specified table.

        Returns:
            DataFrame: A DataFrame containing column names.

        Example:
            columns = schema_model.get_columns()
        """
        ...

    def get_non_null_columns(self) -> list[str]:
        """
        Retrieve names of columns that do not allow null values.

        Returns:
            DataFrame: A DataFrame containing names of non-null columns.

        Example:
            non_null_cols = schema_model.get_non_null_columns()
        """
        ...

    def get_table_definition(self) -> str:
        """
        Get the table definition for the specified table.
        """
        ...
