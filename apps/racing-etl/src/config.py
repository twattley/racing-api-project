from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(dotenv_path=".env", override=True)


class TodaysData(BaseSettings):
    links_view: str = "missing_todays_dates"
    links_table: str = "todays_links"
    data_table: str = "todays_data"


class ResultsData(BaseSettings):
    links_view: str = "missing_dates"
    links_table: str = "results_links"

    data_view: str = "missing_results_links"
    data_table: str = "results_data"
    data_world_view: str = "missing_results_links_world"
    data_world_table: str = "results_data_world"


class RawSchema(BaseSettings):
    todays_data: TodaysData = TodaysData()
    results_data: ResultsData = ResultsData()


class DB(BaseSettings):
    raw: RawSchema = RawSchema()


class Config(BaseSettings):
    chromedriver_path: str

    bf_username: str
    bf_password: str
    bf_app_key: str
    bf_certs_path: str
    bf_historical_data_path: str

    pg_host: str
    pg_user: str
    pg_name: str
    pg_password: str
    pg_port: int

    tf_email: str
    tf_password: str
    tf_login_url: str

    s3_access_key: str
    s3_secret_access_key: str
    s3_region_name: str
    s3_endpoint_url: str
    s3_bucket_name: str

    db: DB = DB()
