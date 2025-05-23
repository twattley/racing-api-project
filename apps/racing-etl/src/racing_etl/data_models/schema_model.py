from api_helpers.interfaces.storage_client_interface import IStorageClient


class SchemaModel:
    def __init__(
        self, storage_client: IStorageClient, schema_name: str, table_name: str
    ):
        self.storage_client = storage_client
        self.schema_name = schema_name
        self.table_name = table_name

    def get_schema_details(self):
        self.data_schema_df = self.get_data_schema()
        self.character_lengths = self.get_character_lengths()
        self.columns = self.get_columns()
        self.non_null_columns = self.get_non_null_columns()
        self.integer_columns = self.get_integer_columns()
        self.numeric_columns = self.get_numeric_columns()

    def get_data_schema(self):
        return self.storage_client.fetch_data(
            f"""
            SELECT 
                column_name, 
                CASE 
                    WHEN character_maximum_length IS NOT NULL 
                    THEN data_type || '(' || character_maximum_length || ')'
                    ELSE data_type
                END AS data_type
            FROM 
                information_schema.columns
            WHERE 
                table_schema = '{self.schema_name}'
                AND table_name = '{self.table_name}'
            ORDER BY 
                ordinal_position;

           """
        )

    def get_character_lengths(self):
        char_df = self.data_schema_df[
            self.data_schema_df["data_type"].str.contains("character varying")
        ]
        char_df = char_df.assign(
            max_length=lambda x: x["data_type"].str.extract(r"\((.*)\)")
        )
        return dict(zip(char_df["column_name"], char_df["max_length"]))

    def get_integer_columns(self) -> list[str]:
        int_df = self.data_schema_df[
            self.data_schema_df["data_type"].isin(["smallint", "integer", "bigint"])
        ]
        return int_df["column_name"].to_list()

    def get_numeric_columns(self) -> list[str]:
        num_df = self.data_schema_df[
            self.data_schema_df["data_type"].isin(["numeric", "decimal"])
        ]
        return num_df["column_name"].to_list()

    def get_columns(self) -> list[str]:
        columns_df = self.storage_client.fetch_data(
            f"""
            SELECT
                column_name AS columns
            FROM
                information_schema.columns
            WHERE
                table_schema = '{self.schema_name}'
                AND table_name = '{self.table_name}';
            """
        )
        return columns_df["columns"].to_list()

    def get_non_null_columns(self) -> list[str]:
        non_null_columns_df = self.storage_client.fetch_data(
            f"""
            SELECT
                column_name AS non_null_columns
            FROM
                information_schema.columns
            WHERE
                table_schema = '{self.schema_name}'
                AND table_name = '{self.table_name}'
                AND is_nullable = 'NO';
            """
        )

        return non_null_columns_df["non_null_columns"].to_list()

    def get_table_definition(self):
        table_def = self.storage_client.fetch_data(
            f"""

                SELECT 
                    'CREATE TABLE ' || quote_ident(table_schema) || '.' || quote_ident(table_name) || ' (' ||
                    string_agg(
                        quote_ident(column_name) || ' ' || 
                        data_type || 
                        CASE 
                            WHEN character_maximum_length IS NOT NULL 
                            THEN '(' || character_maximum_length || ')'
                            ELSE ''
                        END,
                        ', ' ORDER BY ordinal_position
                    ) || ');' AS table_definition
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = '{self.schema_name}'
                    AND table_name = '{self.table_name}'
                GROUP BY 
                    table_schema, table_name;

            """
        )
        return table_def["table_definition"].iloc[0]
