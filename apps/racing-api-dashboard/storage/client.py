from libraries.api_helpers.src.api_helpers.clients.postgres_client import PostgresClient, PsqlConnection
import os

# You can load these from environment variables or a config file for security
PG_USER = os.getenv("PG_USER", "your_user")
PG_PASSWORD = os.getenv("PG_PASSWORD", "your_password")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", 5432))
PG_DB = os.getenv("PG_DB", "your_db")

connection = PsqlConnection(
    user=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    port=PG_PORT,
    db=PG_DB,
)

pg_client = PostgresClient(connection)
