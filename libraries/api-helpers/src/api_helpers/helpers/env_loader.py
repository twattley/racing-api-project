from pathlib import Path
from typing import Literal

from dotenv import load_dotenv


def load_app_env(
    app: Literal["racing-etl", "racing-api", "betfair-live-prices", "trader"],
) -> None:
    current_file_dir = Path(__file__).parent
    dotenv_path = (
        current_file_dir.parent.parent.parent.parent.parent / "apps" / app / ".env"
    )
    load_dotenv(
        dotenv_path=dotenv_path,
        override=True,
    )
