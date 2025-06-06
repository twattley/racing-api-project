from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)


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

    monorepo_root: str = str(
        Path("~/App/racing-api-project/racing-api-project").expanduser()
    )
    print("Monorepo root:", monorepo_root)
    chromedriver_path: str = str(Path("~/chromedriver/chromedriver").expanduser())

    bf_username: str
    bf_password: str
    bf_app_key: str
    bf_certs_path: str = str(Path("~/.betfair/certs").expanduser())

    db_host: str
    db_user: str
    db_name: str
    db_password: str
    db_port: int

    tf_email: str
    tf_password: str
    tf_login_url: str

    s3_access_key: str
    s3_secret_access_key: str
    s3_region_name: str
    s3_endpoint_url: str
    s3_bucket_name: str

    db: DB = DB()


config = Config()
