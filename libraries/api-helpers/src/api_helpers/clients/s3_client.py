from datetime import datetime, timedelta
from io import BytesIO

import boto3
import botocore
import pandas as pd

from api_helpers.helpers.logging_config import I, W


class S3Connection:
    def __init__(
        self, region_name, endpoint_url, access_key_id, secret_access_key, bucket_name
    ):
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name


class S3Client:
    def __init__(self, connection: S3Connection):
        self.connection = connection
        self.session = None
        self.client = None
        self.last_validated = None
        self.validation_interval = timedelta(minutes=10)
        self._create_new_client()

    def _get_client(self):
        current_time = datetime.now()
        if self.client is None or (
            self.last_validated
            and current_time - self.last_validated > self.validation_interval
        ):
            if not self._is_session_valid():
                self._create_new_client()
            self.last_validated = current_time
        return self.client

    def _create_new_client(self):
        self.session = boto3.session.Session()
        self.client = self.session.client(
            "s3",
            region_name=self.connection.region_name,
            endpoint_url=self.connection.endpoint_url,
            aws_access_key_id=self.connection.access_key_id,
            aws_secret_access_key=self.connection.secret_access_key,
        )
        I("Created new S3 client.")

    def _is_session_valid(self):
        session_invalid_codes = {
            "ExpiredToken",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
        }
        if self.client is None:
            return False
        try:
            self.client.list_buckets(MaxBuckets=1)
            I("S3 session is still valid.")
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] in session_invalid_codes:
                I("S3 session expired. Creating new session.")
                return False
            else:
                W(f"An error occurred: {e}")
                return True

    def get_latest_file(self, object_path):
        client = self._get_client()

        try:
            response = client.list_objects_v2(
                Bucket=self.connection.bucket_name, Prefix=object_path
            )
            print(response)

            if "Contents" not in response:
                I(f"No files found in {object_path}")
                return None

            files = [
                obj["Key"]
                for obj in response["Contents"]
                if obj["Key"].endswith(".parquet")
            ]

            print(files)

            if not files:
                W(f"No parquet files found in {object_path}")
                return None

            latest_file = max(
                files,
                key=lambda x: datetime.strptime(
                    x.split("-", 1)[1].rsplit(".", 1)[0], "%Y-%m-%d-%H-%M-%S"
                ),
            )

            I(f"Latest file found: {latest_file}")
            return latest_file

        except botocore.exceptions.ClientError as e:
            W(f"An error occurred: {e}")
            return None

    def fetch_latest_price_changes(self, object_path):
        latest_file = self.get_latest_file(object_path)

        if latest_file is None:
            return None

        return self.fetch_data(latest_file)

    def store_partitioned_data(
        self, data: pd.DataFrame, schema_name: str, table_name: str
    ):
        data["race_year"] = data["race_time"].dt.year
        for year in data["race_year"].unique():
            s3_path = f"{schema_name}/{table_name}_{year}.parquet"
            year_data = data[data["race_year"] == year]
            I(f"Storing {year} data at path {s3_path}")
            self.store_data(year_data, s3_path)

    def store_data(self, data: pd.DataFrame, object_path: str):
        client = self._get_client()
        parquet_buffer = BytesIO()
        data.to_parquet(parquet_buffer, index=False)
        parquet_buffer.seek(0)

        try:
            client.put_object(
                Bucket=self.connection.bucket_name,
                Key=object_path,
                Body=parquet_buffer.getvalue(),
            )
            I(f"DataFrame uploaded to {self.connection.bucket_name}/{object_path}.")
            return True
        except Exception as e:
            W(
                f"Failed to upload DataFrame to {self.connection.bucket_name}/{object_path}. Error: {e}"
            )
            return False

    def fetch_data(self, object_path: str) -> pd.DataFrame:
        if object_path is None:
            W("Object path is None. Returning empty DataFrame.")
            return pd.DataFrame()
        client = self._get_client()
        try:
            parquet_object = client.get_object(
                Bucket=self.connection.bucket_name, Key=object_path
            )
            parquet_content = parquet_object["Body"].read()

            df = pd.read_parquet(BytesIO(parquet_content))
            I(f"DataFrame loaded from {self.connection.bucket_name}/{object_path}.")
            return df
        except Exception as e:
            empty_result_keywords = [
                "selections",
                "invalidated",
                "cashed_out",
                "fully_matched",
                "current_orders",
            ]
            if any(keyword in object_path for keyword in empty_result_keywords):
                return pd.DataFrame()
            else:
                W(
                    f"Failed to download DataFrame from {self.connection.bucket_name}/{object_path}. Error: {e}"
                )
                return pd.DataFrame()

    def delete_old_files(self, prefix: str, keep_count=2):
        """
        Deletes all but the most recent 'keep_count' files in the specified folder.

        :param folder_path: The path to the folder containing the files
        :param keep_count: The number of most recent files to keep (default is 2)
        """
        client = self._get_client()

        try:
            # List all objects in the folder
            response = client.list_objects_v2(
                Bucket=self.connection.bucket_name, Prefix=prefix
            )

            if "Contents" not in response:
                W(f"No files found in {prefix}")
                return

            # Filter for .parquet files and sort by last modified date
            files = sorted(
                [
                    obj
                    for obj in response["Contents"]
                    if obj["Key"].endswith(".parquet")
                ],
                key=lambda x: x["LastModified"],
                reverse=True,
            )

            files_to_delete = files[keep_count:]

            for file in files_to_delete:
                client.delete_object(
                    Bucket=self.connection.bucket_name, Key=file["Key"]
                )
                I(f"Deleted: {file['Key']}")

            I(
                f"Deleted {len(files_to_delete)} old files. Kept the {keep_count} most recent files."
            )

        except botocore.exceptions.ClientError as e:
            W(f"An error occurred while deleting old files: {e}")

    def write_date_to_txt(self, date_to_write: str, object_path: str):
        """
        Writes a date to a text file in the specified S3 object path.

        :param date_to_write: The datetime.date object to write.
        :param object_path: The S3 object path (including the filename, e.g., 'metadata/current_date.txt').
        :return: True if the date was written successfully, False otherwise.
        """
        client = self._get_client()
        date_str = date_to_write.encode("utf-8")

        try:
            client.put_object(
                Bucket=self.connection.bucket_name,
                Key=object_path,
                Body=date_str,
            )
            I(
                f"Date '{date_str}' written to {self.connection.bucket_name}/{object_path}."
            )
            return True
        except Exception as e:
            W(
                f"Failed to write date to {self.connection.bucket_name}/{object_path}. Error: {e}"
            )
            return False

    def read_date_from_txt(self, object_path: str) -> str:
        """
        Reads a date from a text file in the specified S3 object path.
        Assumes the file contains a single date in ISO format (YYYY-MM-DD).

        :param object_path: The S3 object path (including the filename, e.g., 'metadata/current_date.txt').
        :return: A datetime.date object if the read was successful and the content is a valid date, None otherwise.
        """
        client = self._get_client()
        try:
            response = client.get_object(
                Bucket=self.connection.bucket_name, Key=object_path
            )
            content = response["Body"].read().decode("utf-8").strip()
            return datetime.strptime(content, "%Y-%m-%d").date().strftime("%Y-%m-%d")
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                I(f"File not found: {self.connection.bucket_name}/{object_path}")
                return None
            else:
                W(
                    f"Error reading date from {self.connection.bucket_name}/{object_path}. Error: {e}"
                )
                return None
        except ValueError:
            W(
                f"Failed to parse date from content '{content}' in {self.connection.bucket_name}/{object_path}. Expected YYYY-MM-DD format."
            )
            return None
        except Exception as e:
            W(f"An unexpected error occurred while reading date: {e}")
            return None

    def store_with_timestamp(
        self,
        data: pd.DataFrame,
        base_path: str,
        file_prefix: str,
        file_name: str,
        keep_count=3,
        timestamp_format="%Y_%m_%d_%H_%M_%S",
    ):
        """
        Stores data with a timestamped filename, keeps track of the latest file,
        and automatically cleans up old files.

        :param data: DataFrame to store
        :param base_path: Base S3 path (e.g., 'today/2025_03_31')
        :param file_prefix: Prefix for the file (e.g., 'combine_price_data')
        :param file_name: Name of the file (e.g., 'combined_price_data')
        :param keep_count: Number of recent files to keep (default: 3)
        :param timestamp_format: Format for the timestamp (default: '%Y_%m_%d_%H_%M_%S')
        :return: Path to the newly created file
        """
        # Generate timestamp and full path
        timestamp = datetime.now().strftime(timestamp_format)
        filename = f"{file_prefix}_{timestamp}.parquet"
        object_path = f"{base_path}/{filename}"

        # Store the data
        success = self.store_data(data, object_path)
        if not success:
            W(f"Failed to store data at {object_path}")
            return None

        I(f"Successfully stored timestamped data at {object_path}")

        # Update a pointer file to the latest version (optional but useful)
        latest_pointer_path = f"{base_path}/{file_name}_latest.txt"
        try:
            client = self._get_client()
            client.put_object(
                Bucket=self.connection.bucket_name,
                Key=latest_pointer_path,
                Body=object_path.encode("utf-8"),
            )
            I(f"Updated latest file pointer at {latest_pointer_path}")
        except Exception as e:
            W(f"Failed to update latest file pointer: {e}")

        # Clean up old files if needed
        if keep_count > 0:
            try:
                # Get list of files with the same prefix
                response = client.list_objects_v2(
                    Bucket=self.connection.bucket_name,
                    Prefix=f"{base_path}/{file_prefix}",
                )

                if "Contents" in response:
                    # Find parquet files and sort by timestamp in filename
                    files = [
                        obj
                        for obj in response["Contents"]
                        if obj["Key"].endswith(".parquet") and file_prefix in obj["Key"]
                    ]

                    # Sort by last modified time (newest first)
                    files.sort(key=lambda x: x["LastModified"], reverse=True)

                    # Delete files beyond the keep count
                    for file in files[keep_count:]:
                        client.delete_object(
                            Bucket=self.connection.bucket_name, Key=file["Key"]
                        )
                        I(f"Deleted old file: {file['Key']}")

            except Exception as e:
                W(f"Error cleaning up old files: {e}")

        return object_path

    def get_latest_timestamped_file(
        self, base_path: str, file_prefix: str = None, file_name: str = None
    ):
        """
        Gets the path to the latest timestamped file in the specified path.

        :param base_path: The base S3 path to search in
        :param file_prefix: Optional prefix to filter files by
        :return: The S3 key of the latest file, or None if no files found
        """
        client = self._get_client()

        try:
            # First try to read from the pointer file if it exists
            pointer_path = f"{base_path}/{file_name}_latest.txt"
            try:
                response = client.get_object(
                    Bucket=self.connection.bucket_name, Key=pointer_path
                )
                latest_path = response["Body"].read().decode("utf-8").strip()
                I(f"Found latest file path from pointer: {latest_path}")
                return latest_path
            except botocore.exceptions.ClientError:
                # Pointer doesn't exist, continue with listing files
                pass

            # List objects in the path
            prefix = base_path
            if file_prefix:
                prefix = f"{base_path}/{file_prefix}"

            response = client.list_objects_v2(
                Bucket=self.connection.bucket_name, Prefix=prefix
            )

            if "Contents" not in response:
                I(f"No files found in {prefix}")
                return None

            # Filter for parquet files
            files = [
                obj for obj in response["Contents"] if obj["Key"].endswith(".parquet")
            ]

            if not files:
                W(f"No parquet files found in {prefix}")
                return None

            # Sort by LastModified timestamp (most recent first)
            latest_file = sorted(files, key=lambda x: x["LastModified"], reverse=True)[
                0
            ]["Key"]
            I(f"Latest file found: {latest_file}")
            return latest_file

        except Exception as e:
            W(f"Error finding latest file: {e}")
            return None
