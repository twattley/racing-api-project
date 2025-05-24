from pathlib import Path

import pandas as pd
from api_helpers.helpers.logging_config import E, I


class BetfairCache:
    DIR_PATH = Path(__file__).parent.resolve()
    CACHE_DIR = DIR_PATH / "cache"
    PROCESSED_FILENAMES = CACHE_DIR / "processed_filenames.parquet"
    ERROR_FILENAMES = CACHE_DIR / "error_filenames.parquet"

    def __init__(self):
        self.data = pd.read_parquet(self.PROCESSED_FILENAMES)
        self.error_filenames = pd.read_parquet(self.ERROR_FILENAMES)

    @property
    def max_processed_date(self):
        return self.data["filename_date"].max()

    @property
    def cached_files(self):
        return set(
            list(self.data["filename"].unique())
            + list(self.error_filenames["filename"].unique())
        )

    def store_data(self, data: pd.DataFrame):
        I(f"Received {len(data)} rows to store")
        self.data = pd.concat([self.data, data]).drop_duplicates()
        I(f"Stored {len(self.data)} rows")
        self.data.to_parquet(self.PROCESSED_FILENAMES)

    def store_error_data(self, data: pd.DataFrame):
        E(f"Received {len(data)} rows to store")
        self.error_filenames = pd.concat([self.error_filenames, data])
        self.error_filenames = self.error_filenames.drop_duplicates()
        E(f"Stored {len(self.error_filenames)} rows")
        self.error_filenames.to_parquet(self.ERROR_FILENAMES)
