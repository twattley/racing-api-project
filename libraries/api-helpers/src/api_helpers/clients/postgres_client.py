from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd
import sqlalchemy
from api_helpers.helpers.logging_config import D, E, I


@dataclass
class PsqlConnection:
    user: str
    password: str
    host: str
    port: int
    db: str


class PostgresClient:
    connection: PsqlConnection

    def __init__(self, connection: PsqlConnection):
        self.connection = connection

    def storage_connection(self) -> sqlalchemy.engine.Engine:
        for i in [
            ("user", self.connection.user),
            ("password", self.connection.password),
            ("host", self.connection.host),
            ("port", self.connection.port),
            ("db", self.connection.db),
        ]:
            if not i[1]:
                raise ValueError(f"Missing database connection parameter: {i[0]} ")

        return sqlalchemy.create_engine(
            f"postgresql://{self.connection.user}:{self.connection.password}@{self.connection.host}:{self.connection.port}/{self.connection.db}"
        )

    def store_data(
        self,
        data: pd.DataFrame,
        table: str,
        schema: str,
        truncate: bool = False,
        created_at: bool = False,
    ) -> None:
        if data.empty:
            I(f"No data to store in {schema}.{table}")
            return
        with self.storage_connection().begin() as conn:
            if truncate:
                I(f"Truncating {schema}.{table}")
                self.execute_query(f"TRUNCATE TABLE {schema}.{table}")
            if created_at:
                I(f"Adding created_at column to {schema}.{table}")
                data = data.assign(
                    created_at=datetime.now().replace(microsecond=0, second=0)
                )
            I(f"Storing {len(data)} records in {schema}.{table}")
            data.to_sql(
                name=table,
                con=conn,
                schema=schema,
                if_exists="append",
                index=False,
            )

    def fetch_data(
        self,
        query: str,
    ) -> pd.DataFrame:
        query = sqlalchemy.text(query)

        D(f"Fetching data with query: {query}")

        with self.storage_connection().begin() as conn:
            df = pd.read_sql(
                query,
                conn,
            )

        return df

    def execute_query(self, query: str) -> None:
        I(f"Executing query: {query}")

        with self.storage_connection().begin() as conn:
            result = conn.execute(sqlalchemy.text(query))
            affected_rows = result.rowcount

        I(f"Query executed. Number of rows affected: {affected_rows}")

    def upsert_data(
        self,
        data: pd.DataFrame,
        schema: str,
        table_name: str,
        unique_columns: List[str],
        use_base_table: bool = False,
        upsert_procedure: str | None = None,
    ):
        data = data.drop_duplicates(subset=unique_columns).reset_index(drop=True)

        temp_table_name = f"{schema}_{table_name}_tmp_load"

        with self.storage_connection().begin() as conn:
            if use_base_table:
                conn.execute(
                    sqlalchemy.text(
                        f"CREATE TABLE {temp_table_name} (LIKE {schema}.{table_name});"
                    )
                )
            data.to_sql(temp_table_name, conn, if_exists="append", index=False)
            I(f"Data loaded to temp table {temp_table_name}")
            if upsert_procedure:
                conn.execute(sqlalchemy.text(upsert_procedure))
                I(f"Upsert procedure {upsert_procedure} called")
            else:
                conn.execute(sqlalchemy.text(f"CALL {schema}.upsert_{table_name}();"))
                I(f"Upsert procedure {schema}.upsert_{table_name} called")
            conn.execute(sqlalchemy.text(f"DROP TABLE {temp_table_name};"))
            I(f"Temp table {temp_table_name} dropped")

        I(f"Upsert completed for {len(data)} records to {schema}.{table_name}")

    def store_latest_data(
        self,
        data: pd.DataFrame,
        table: str,
        schema: str,
        unique_columns: List[str] | str,
    ) -> None:
        if data.empty:
            I(f"No data to store in {schema}.{table}")
            return

        if isinstance(unique_columns, str):
            unique_columns = [unique_columns]

        unique_cols_str = ", ".join(unique_columns)

        data = data.assign(created_at=datetime.now().replace(microsecond=0, second=0))

        with self.storage_connection().begin() as conn:
            I(f"Storing {len(data)} records in {schema}.{table}")
            data.to_sql(
                name=table,
                con=conn,
                schema=schema,
                if_exists="append",
                index=False,
            )

            cleanup_query = f"""
            DELETE FROM {schema}.{table} 
            WHERE ctid NOT IN (
                SELECT DISTINCT ON ({unique_cols_str}) ctid
                FROM {schema}.{table}
                ORDER BY {unique_cols_str}, created_at DESC
            )
            """

            result = conn.execute(sqlalchemy.text(cleanup_query))
            deleted_rows = result.rowcount

            I(
                f"Cleanup completed. Deleted {deleted_rows} older records from {schema}.{table} based on columns: {unique_cols_str}"
            )

            # Log final count
            count_query = f"SELECT COUNT(*) as total FROM {schema}.{table}"
            count_result = conn.execute(sqlalchemy.text(count_query))
            total_records = count_result.fetchone()[0]

            I(f"Final record count in {schema}.{table}: {total_records}")

    def fetch_latest_data(
        self,
        table: str,
        schema: str,
        unique_columns: tuple[str] | str,
    ) -> pd.DataFrame:
        if isinstance(unique_columns, tuple):
            unique_columns = ", ".join(unique_columns)

        base_query = f"""
        SELECT *
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY {unique_columns} 
                       ORDER BY created_at DESC
                   ) as rn
            FROM {schema}.{table}
        ) ranked
        WHERE rn = 1
        """

        query = f"{base_query} ORDER BY {unique_columns}"

        D(f"Fetching latest data from {schema}.{table} with query: {query}")

        try:
            with self.storage_connection().begin() as conn:
                df = pd.read_sql(
                    sqlalchemy.text(query),
                    conn,
                )

            I(
                f"Fetched {len(df)} latest records from {schema}.{table} based on columns: {unique_columns}"
            )
            return df

        except Exception as e:
            E(f"Error fetching latest data from {schema}.{table}: {str(e)}")
            raise
