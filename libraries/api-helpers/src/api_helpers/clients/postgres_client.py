from dataclasses import dataclass
from typing import List, Optional, Union

import pandas as pd
import sqlalchemy

from api_helpers.helpers.logging_config import I
from api_helpers.helpers.time_utils import get_uk_time_now


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
                self = data.assign(created_at=get_uk_time_now())
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

        I(f"Fetching data with query: {query}")

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
