from dotenv import load_dotenv
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    db_name: str
    db_username: str
    db_host: str
    db_port: str
    db_password: str
    db_pool_size: int
    db_conn_timeout: int
    db_query_timeout: int
    service_name: str
    api_host: str
    api_port: int
    bf_username: str
    bf_password: str
    bf_app_key: str
    bf_certs_path: str
    s3_region_name: str
    s3_endpoint_url: str
    s3_bucket_name: str
    s3_access_key: str
    s3_secret_access_key: str


load_dotenv(".env", override=True)
config = Config()
