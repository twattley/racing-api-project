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

    bf_username: str
    bf_password: str
    bf_app_key: str
    bf_certs_path: str = str(Path("~/.betfair/certs").expanduser())

    mb_username: str
    mb_password: str

    db_host: str
    db_user: str
    db_name: str
    db_password: str
    db_port: int

    cloud_db_host: str
    cloud_db_user: str
    cloud_db_name: str
    cloud_db_password: str
    cloud_db_port: int
    cloud_db_sslmode: str = "prefer"  # Works based on your connection tests

    tf_email: str
    tf_password: str
    tf_login_url: str

    log_level: str

    stake_size: float = 50.0

    db: DB = DB()


config = Config()
