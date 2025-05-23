from api_helpers.helpers.env_loader import load_app_env
from pydantic_settings import BaseSettings

load_app_env("trader")


class Config(BaseSettings):
    bf_username: str
    bf_password: str
    bf_app_key: str
    bf_certs_path: str
    bf_historical_data_path: str

    s3_access_key: str
    s3_secret_access_key: str
    s3_region_name: str
    s3_endpoint_url: str
    s3_bucket_name: str
