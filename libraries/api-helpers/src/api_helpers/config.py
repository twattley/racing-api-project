from pathlib import Path
from typing import List, Tuple

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

    log_level: str

    stake_size: int = 50

    # Time-based staking configuration
    enable_time_based_staking: bool = True

    # List of (minutes_threshold, stake_percentage) tuples
    # Stakes increase as race approaches, allowing gradual liquidity matching
    time_based_staking_thresholds: List[Tuple[int, float]] = [
        (240, 0.10),  # 4+ hours: 10%
        (210, 0.15),  # 3.5+ hours: 15%
        (180, 0.20),  # 3+ hours: 20%
        (150, 0.25),  # 2.5+ hours: 25%
        (120, 0.30),  # 2+ hours: 30%
        (90, 0.40),  # 1.5+ hours: 40%
        (60, 0.50),  # 1+ hour: 50%
        (45, 0.60),  # 45+ minutes: 60%
        (30, 0.70),  # 30+ minutes: 70%
        (20, 0.80),  # 20+ minutes: 80%
        (10, 0.90),  # 10+ minutes: 90%
        (5, 1.00),  # 5+ minutes: 100%
    ]

    # Minimum liquidity threshold - won't place bet if available liquidity is below this
    min_liquidity_threshold: float = 2.0

    db: DB = DB()


config = Config()
