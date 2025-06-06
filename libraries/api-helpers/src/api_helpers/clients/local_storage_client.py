from datetime import datetime
from pathlib import Path

import pandas as pd
from api_helpers.helpers.logging_config import I, W

from api_helpers.config import config


class LocalStorageClient:
    def __init__(self, keep_versions: int = 3):
        self.base_path = config.monorepo_root / "data"
        self.keep_versions = keep_versions

    def fetch_data(self, object_path: str) -> pd.DataFrame:
        """Fetch DataFrame from the latest version of the file"""
        if object_path is None:
            W("Object path is None. Returning empty DataFrame.")
            return pd.DataFrame()

        latest_file_path = self._get_latest_file(object_path)

        if latest_file_path is None:
            empty_result_keywords = [
                "selections",
                "invalidated",
                "cashed_out",
                "fully_matched",
                "current_orders",
                "requests_data",
            ]
            if any(keyword in object_path for keyword in empty_result_keywords):
                return pd.DataFrame()
            else:
                W(f"No files found for path: {object_path}")
                return pd.DataFrame()

        try:
            df = pd.read_parquet(latest_file_path)
            I(f"DataFrame loaded from {latest_file_path.relative_to(self.base_path)}")
            return df
        except Exception as e:
            W(f"Failed to load DataFrame from {latest_file_path}. Error: {e}")
            return pd.DataFrame()

    def store_data(self, data: pd.DataFrame, object_path: str) -> bool:
        """Store DataFrame with automatic versioning and cleanup"""
        # Generate timestamped filename
        base_name = Path(object_path).stem
        extension = Path(object_path).suffix or ".parquet"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_name = f"{base_name}_{timestamp}{extension}"

        # Create full path with timestamp
        directory = Path(object_path).parent
        timestamped_path: Path = self.base_path / directory / timestamped_name

        # Ensure directory exists
        timestamped_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data.to_parquet(timestamped_path, index=False)
            I(f"DataFrame saved to {timestamped_path.relative_to(self.base_path)}")

            # Clean up old versions
            self._cleanup_old_files(object_path)

            return True
        except Exception as e:
            W(f"Failed to save DataFrame to {timestamped_path}. Error: {e}")
            return False

    def _get_latest_file(self, object_path: str) -> Path:
        """Private method to get the latest version of a file based on modification time"""
        base_name = Path(object_path).stem
        extension = Path(object_path).suffix or ".parquet"
        directory: Path = self.base_path / Path(object_path).parent

        if not directory.exists():
            return None

        # Search for files matching the pattern: basename_*timestamp.extension
        pattern = f"{base_name}_*{extension}"
        matching_files = list(directory.glob(pattern))

        if not matching_files:
            # Also check for exact filename match (backwards compatibility)
            exact_file = self.base_path / object_path
            if exact_file.exists():
                matching_files = [exact_file]
            else:
                return None

        # Sort by modification time (newest first)
        files_with_times = [(f.stat().st_mtime, f) for f in matching_files]
        files_with_times.sort(key=lambda x: x[0], reverse=True)

        latest_file = files_with_times[0][1]
        I(f"Latest file found: {latest_file.relative_to(self.base_path)}")
        return latest_file

    def _cleanup_old_files(self, object_path: str):
        """Private method to clean up old versions, keeping only the specified number"""
        base_name = Path(object_path).stem
        extension = Path(object_path).suffix or ".parquet"
        directory: Path = self.base_path / Path(object_path).parent

        if not directory.exists():
            return

        # Find all timestamped versions
        pattern = f"{base_name}_*{extension}"
        matching_files = list(directory.glob(pattern))

        if len(matching_files) <= self.keep_versions:
            return

        # Sort by modification time (newest first)
        files_with_times = [(f.stat().st_mtime, f) for f in matching_files]
        files_with_times.sort(key=lambda x: x[0], reverse=True)

        # Delete files beyond the keep count
        files_to_delete = files_with_times[self.keep_versions :]

        for _, file_path in files_to_delete:
            try:
                file_path.unlink()
                I(f"Deleted old version: {file_path.relative_to(self.base_path)}")
            except Exception as e:
                W(f"Failed to delete {file_path}: {e}")

        I(
            f"Cleaned up {len(files_to_delete)} old versions. Kept {self.keep_versions} most recent."
        )
