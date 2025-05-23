import pandas as pd
import pytest
from src.data_models.data_validator import DataValidator
from src.data_models.interfaces.data_validator_interface import IDataValidator
from tests.test_helpers import assert_df_data_equal


class TestSchemaModel:
    columns = ["unique_id", "name", "email", "age"]
    non_null_columns = ["unique_id", "name"]
    character_lengths = {"unique_id": "10", "name": "50", "email": "100"}


@pytest.fixture
def data_validator() -> IDataValidator:
    return DataValidator()


@pytest.mark.parametrize(
    "input_df, expected_accepted, expected_rejected",
    [
        # Test case 1: All valid data
        (
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", "Jane Smith", "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com",
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", "Jane Smith", "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com",
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                columns=["unique_id", "name", "email", "age", "column", "error_value"]
            ),
        ),
        # Test case 2: One row with email exceeding max length
        (
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", "Jane Smith", "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@" + "x" * 100,
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["1", "2"],
                    "name": ["John Doe", "Jane Smith"],
                    "email": ["john@example.com", "jane@example.com"],
                    "age": [30, 25],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["3"],
                    "name": ["Bob Johnson"],
                    "email": ["bob@" + "x" * 100],
                    "age": [35],
                    "column": ["email"],
                    "error_value": ["bob@" + "x" * 100],
                }
            ),
        ),
        # Test case 3: Multiple columns exceeding max length
        (
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", "Jane Smith" * 10, "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com" * 10,
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "name": ["John Doe"],
                    "email": ["john@example.com"],
                    "age": [30],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["2", "3"],
                    "name": ["Jane Smith" * 10, "Bob Johnson"],
                    "email": ["jane@example.com", "bob@example.com" * 10],
                    "age": [25, 35],
                    "column": ["name", "email"],
                    "error_value": ["Jane Smith" * 10, "bob@example.com" * 10],
                }
            ),
        ),
    ],
)
def test_validate_field_lengths(
    data_validator: IDataValidator,
    input_df: pd.DataFrame,
    expected_accepted: pd.DataFrame,
    expected_rejected: pd.DataFrame,
):
    accepted_df, rejected_df = data_validator.validate_field_lengths(
        input_df, TestSchemaModel
    )

    assert_df_data_equal(accepted_df, expected_accepted)
    assert_df_data_equal(rejected_df, expected_rejected)


@pytest.mark.parametrize(
    "input_df, expected_accepted, expected_rejected",
    [
        # Test case 1: All valid data
        (
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", "Jane Smith", "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com",
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", "Jane Smith", "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com",
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                columns=["unique_id", "name", "email", "age", "column", "error_value"]
            ),
        ),
        # Test case 2: One row with null in non-null column
        (
            pd.DataFrame(
                {
                    "unique_id": ["1", "2", "3"],
                    "name": ["John Doe", None, "Bob Johnson"],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com",
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["1", "3"],
                    "name": ["John Doe", "Bob Johnson"],
                    "email": ["john@example.com", "bob@example.com"],
                    "age": [30, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["2"],
                    "name": [None],
                    "email": ["jane@example.com"],
                    "age": [25],
                    "column": ["name"],
                    "error_value": ["null"],
                }
            ),
        ),
        # Test case 3: Multiple rows with nulls in non-null columns
        (
            pd.DataFrame(
                {
                    "unique_id": ["1", None, "3"],
                    "name": ["John Doe", "Jane Smith", None],
                    "email": [
                        "john@example.com",
                        "jane@example.com",
                        "bob@example.com",
                    ],
                    "age": [30, 25, 35],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": ["1"],
                    "name": ["John Doe"],
                    "email": ["john@example.com"],
                    "age": [30],
                }
            ),
            pd.DataFrame(
                {
                    "unique_id": [None, "3"],
                    "name": ["Jane Smith", None],
                    "email": ["jane@example.com", "bob@example.com"],
                    "age": [25, 35],
                    "column": ["unique_id", "name"],
                    "error_value": ["null", "null"],
                }
            ),
        ),
    ],
)
def test_validate_non_null_columns(
    data_validator: IDataValidator,
    input_df: pd.DataFrame,
    expected_accepted: pd.DataFrame,
    expected_rejected: pd.DataFrame,
):
    accepted_df, rejected_df = data_validator.validate_non_null_columns(
        input_df, TestSchemaModel
    )

    assert_df_data_equal(accepted_df, expected_accepted)
    assert_df_data_equal(rejected_df, expected_rejected)
