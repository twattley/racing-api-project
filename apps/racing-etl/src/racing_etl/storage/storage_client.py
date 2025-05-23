from typing import Literal

from api_helpers.clients.postgres_client import PostgresClient, PsqlConnection
from api_helpers.clients.s3_client import S3Client, S3Connection
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..config import Config


def get_storage_client(
    client_type: Literal["postgres", "s3"],
) -> IStorageClient:
    config = Config()
    if client_type == "postgres":
        return PostgresClient(
            PsqlConnection(
                user=config.pg_user,
                password=config.pg_password,
                host=config.pg_host,
                port=config.pg_port,
                db=config.pg_name,
            )
        )
    elif client_type == "s3":
        return S3Client(
            S3Connection(
                access_key_id=config.s3_access_key,
                secret_access_key=config.s3_secret_access_key,
                region_name=config.s3_region_name,
                endpoint_url=config.s3_endpoint_url,
                bucket_name=config.s3_bucket_name,
            )
        )
