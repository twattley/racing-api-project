from api_helpers.config import config

from .betfair_client import (
    BetFairCashOut,
    BetFairClient,
    BetfairCredentials,
)
from .postgres_client import PostgresClient, PsqlConnection
from .s3_client import S3Client, S3Connection


def get_s3_client() -> S3Client:
    return S3Client(
        S3Connection(
            access_key_id=config.s3_access_key,
            secret_access_key=config.s3_secret_access_key,
            region_name=config.s3_region_name,
            endpoint_url=config.s3_endpoint_url,
            bucket_name=config.s3_bucket_name,
        )
    )


def get_betfair_client() -> BetFairClient:
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
    betfair_client.login()
    return betfair_client


def get_postgres_client() -> PostgresClient:
    return PostgresClient(
        PsqlConnection(
            user=config.db_user,
            password=config.db_password,
            host=config.db_host,
            port=config.db_port,
            db=config.db_name,
        )
    )
