from api_helpers.config import config

from .betfair_client import (
    BetFairCashOut,
    BetFairClient,
    BetfairCredentials,
)
from .postgres_client import PostgresClient, PsqlConnection
from .s3_client import S3Client, S3Connection

# Import for shared client access
_shared_betfair_client = None

# Singleton pattern for PostgresClient
_local_postgres_client = None
_cloud_postgres_client = None


def set_shared_betfair_client(client: BetFairClient):
    """Set the shared Betfair client instance (used by main.py)."""
    global _shared_betfair_client
    _shared_betfair_client = client


def get_s3_client(connect=True) -> S3Client:
    s3_client = S3Client(
        S3Connection(
            access_key_id=config.s3_access_key,
            secret_access_key=config.s3_secret_access_key,
            region_name=config.s3_region_name,
            endpoint_url=config.s3_endpoint_url,
            bucket_name=config.s3_bucket_name,
        )
    )
    if connect:
        s3_client.connect_to_s3()
    return s3_client


def get_betfair_client(connect=True) -> BetFairClient:
    """Get the shared Betfair client instance or create a new one if shared instance is not available."""
    global _shared_betfair_client

    # If we have a shared client, return it
    if _shared_betfair_client is not None:
        return _shared_betfair_client

    # Fallback: create a new client (for standalone usage outside of FastAPI app)
    betfair_client = BetFairClient(
        BetfairCredentials(
            username=config.bf_username,
            password=config.bf_password,
            app_key=config.bf_app_key,
            certs_path=config.bf_certs_path,
        ),
        BetFairCashOut(),
    )
    betfair_client.logout()
    if connect:
        betfair_client.login()
    return betfair_client


def get_local_postgres_client() -> PostgresClient:
    """Get the singleton local PostgresClient instance."""
    global _local_postgres_client
    if _local_postgres_client is None:
        connection = PsqlConnection(
            user=config.db_user,
            password=config.db_password,
            host=config.db_host,
            port=config.db_port,
            db=config.db_name,
        )
        _local_postgres_client = PostgresClient(connection)
    return _local_postgres_client
