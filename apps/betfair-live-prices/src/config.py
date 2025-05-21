import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    root_dir: str
    bf_username: str
    bf_password: str
    bf_app_key: str
    bf_certs_path: str
    s3_region_name: str
    s3_endpoint_url: str
    s3_bucket_name: str
    s3_access_key: str
    s3_secret_access_key: str
    log_file_dir: str


def load_config():
    env = os.environ.get("ENV", "DEV")
    if env == "DEV":
        env_file = ".env"
    elif env == "TEST":
        env_file = "./tests/.test.env"
    load_dotenv(env_file, override=True)
    return Config()


config = load_config()
