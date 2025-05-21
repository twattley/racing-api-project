from typing import Protocol

import pandas as pd


class IStorageClient(Protocol):
    """
    Interface for a storage client that handles data storage and retrieval operations.

    This interface defines methods for storing data, fetching data, and executing queries
    on a storage system.

    Examples:
        >>> storage_client = ConcreteStorageClient()
        >>> data = pd.DataFrame({'column1': [1, 2, 3], 'column2': ['a', 'b', 'c']})
        >>> storage_client.store_data(data, 'my_table', 'my_schema')
        >>> result = storage_client.fetch_data("SELECT * FROM my_schema.my_table")
        >>> storage_client.execute_query("UPDATE my_schema.my_table SET column2 = 'x' WHERE column1 = 1")
    """

    def store_data(
        self,
        data: pd.DataFrame,
        table: str,
        schema: str,
        truncate: bool = False,
        created_at: bool = False,
    ) -> None:
        """
        Store data in the specified table and schema.

        Args:
            data (pd.DataFrame): The data to be stored.
            table (str): The name of the table to store the data in.
            schema (str): The schema name.
            truncate (bool, optional): Whether to truncate the table before inserting. Defaults to False.
            created_at (bool, optional): Whether to add a created_at timestamp. Defaults to False.

        Returns:
            None

        Example:
            >>> data = pd.DataFrame({'column1': [1, 2, 3], 'column2': ['a', 'b', 'c']})
            >>> storage_client.store_data(data, 'my_table', 'my_schema', truncate=True)
        """
        ...

    def fetch_data(
        self,
        query: str,
    ) -> pd.DataFrame:
        """
        Fetch data using the provided SQL query.

        Args:
            query (str): The SQL query to execute.

        Returns:
            pd.DataFrame: The result of the query as a pandas DataFrame.

        Example:
            >>> result = storage_client.fetch_data("SELECT * FROM my_schema.my_table WHERE column1 > 1")
        """
        ...

    def execute_query(self, query: str) -> None:
        """
        Execute a SQL query without returning results.

        Args:
            query (str): The SQL query to execute.

        Returns:
            None

        Example:
            >>> storage_client.execute_query("DELETE FROM my_schema.my_table WHERE column1 = 1")
        """
        ...

    def upsert_data(
        self,
        data: pd.DataFrame,
        schema: str,
        table_name: str,
        unique_columns: list[str],
        use_base_table: bool = False,
        upsert_procedure: str | None = None,
    ) -> None:
        """
        Upsert data into the specified table and schema.

        Args:
            data (pd.DataFrame): The data to be upserted.
            schema (str): The schema name.
            table_name (str): The name of the table to upsert the data into.
            unique_columns (List[str]): List of column names that define the uniqueness of a row.
            use_base_table (bool, optional): Whether to use the base table to create a temp table. Defaults to False.
            upsert_procedure (str | None, optional): The upsert procedure to call. Defaults to None.
        Returns:
            None

        Example:
            >>> data = pd.DataFrame({'id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie'], 'age': [25, 30, 35]})
            >>> storage_client.upsert_data(data, 'my_schema', 'my_table', unique_columns=['id'])
        """
        ...
