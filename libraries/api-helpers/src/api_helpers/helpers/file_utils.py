from datetime import datetime
from pathlib import Path
from typing import Optional


def create_file(filepath: str | Path):
    """
    Ensures a file exists at the given path.
    If the file does not exist, it creates an empty file.
    If the file already exists, it updates its last access and modification times (like 'touch').

    Args:
        filepath: The path to the file (string or Path object).
    """
    path_obj = Path(filepath)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    path_obj.touch()

    print(f"Ensured file exists: {path_obj}")
    if path_obj.is_file():
        print(f"Confirmation: '{path_obj}' is a file.")
    else:
        print(
            f"Warning: '{path_obj}' exists but is not a file (e.g., it's a directory)."
        )


def create_todays_log_file(log_dir: str, prefix: Optional[str] = "execution_"):
    log_file_path = Path(log_dir) / f"{prefix}{datetime.now().strftime('%Y_%m_%d')}.log"
    create_file(log_file_path)

    return log_file_path


def delete_files_in_directory(directory: str | Path, file_pattern: str):
    """
    Deletes files in a specified directory that contain a given file pattern in their name.

    Args:
        directory: The path to the directory (string or Path object).
        file_pattern: A string pattern to search for within filenames (e.g., '.tmp', 'old_').
    """
    dir_path = Path(directory)

    if not dir_path.is_dir():
        print(
            f"Warning: Directory '{directory}' does not exist or is not a valid directory. Skipping file deletion."
        )
        return

    print(
        f"Searching for files matching pattern '{file_pattern}' in '{dir_path}' to delete..."
    )

    for file_path in dir_path.iterdir():
        if file_path.is_file():
            if file_pattern in file_path.name:
                try:
                    file_path.unlink()
                    print(f"Deleted file: {file_path}")
                except OSError as e:
                    print(f"Error deleting file {file_path}: {e}")

    print(f"Finished checking for files to delete in '{dir_path}'.")


class S3FilePaths:
    BASE_FOLDER = "today"
    TRADER_FOLDER = "trader_data"
    RACES_FOLDER = "race_data"

    @property
    def folder(self) -> str:
        """Get the base folder path for today's trading data."""
        return f"{self.BASE_FOLDER}/{self._get_uk_time_now()}"

    @property
    def selections(self) -> str:
        return f"{self.folder}/{self.TRADER_FOLDER}/selections.parquet"

    @property
    def market_state(self) -> str:
        return f"{self.folder}/{self.TRADER_FOLDER}/market_state.parquet"

    @property
    def fully_matched_bets(self) -> str:
        return f"{self.folder}/{self.TRADER_FOLDER}/fully_matched_bets.parquet"

    @property
    def cashed_out_bets(self) -> str:
        return f"{self.folder}/{self.TRADER_FOLDER}/cashed_out_bets.parquet"

    @property
    def invalidated_bets(self) -> str:
        return f"{self.folder}/{self.TRADER_FOLDER}/invalidated_bets.parquet"

    @property
    def current_requests(self) -> str:
        return f"{self.folder}/{self.TRADER_FOLDER}/current_requests_data.parquet"

    @property
    def race_times(self) -> str:
        return f"{self.folder}/{self.RACES_FOLDER}/race_times.parquet"

    @property
    def results_data(self) -> str:
        return f"{self.folder}/{self.RACES_FOLDER}/results_data.parquet"

    def _get_uk_time_now(self) -> str:
        return datetime.now().strftime("%Y_%m_%d")
