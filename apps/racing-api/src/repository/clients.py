from api_helpers.clients.betfair_client import (
    BetFairCashOut,
    BetFairClient,
    BetfairCredentials,
)
from api_helpers.clients.s3_client import S3Client, S3Connection

from src.config import Config

config = Config()


def get_s3_client():
    return S3Client(
        S3Connection(
            access_key_id=config.s3_access_key,
            secret_access_key=config.s3_secret_access_key,
            region_name=config.s3_region_name,
            endpoint_url=config.s3_endpoint_url,
            bucket_name=config.s3_bucket_name,
        )
    )


def get_betfair_client():
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
