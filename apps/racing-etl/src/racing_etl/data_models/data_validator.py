import pandas as pd

from ..data_models.interfaces.data_validator_interface import IDataValidator
from ..data_models.interfaces.schema_model_interface import ISchemaModel

validated_data = tuple[pd.DataFrame, pd.DataFrame]


class DataValidator(IDataValidator):
    def validate_columns(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> validated_data:
        missing_columns = set(schema_model.columns) - set(data.columns)
        if missing_columns:
            raise ValueError(
                f"Data contains missing columns: {', '.join(missing_columns)}"
            )

    def validate_field_lengths(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> validated_data:
        original_columns = list(data.columns)
        errors = []
        for column, max_length in schema_model.character_lengths.items():
            if column == "unique_id":
                continue
            if data[column].isnull().all():
                continue
            if not [i for i in data[column] if i]:
                continue
            if column in data.columns:
                sub_data = data.copy()
                sub_data[f"{column}_string_length"] = (
                    sub_data[column].astype(str).str[: int(max_length)]
                )
                sub_data[f"{column}_string_length_amount"] = (
                    sub_data[f"{column}_string_length"].str.len()
                    - data[column].str.len()
                )
                greater_than_zero: pd.DataFrame = sub_data[
                    sub_data[f"{column}_string_length_amount"] < 0
                ][
                    [
                        "unique_id",
                        column,
                        f"{column}_string_length",
                        f"{column}_string_length_amount",
                    ]
                ]
                if not greater_than_zero.empty:
                    for i, v in greater_than_zero.iterrows():
                        errors.append(
                            {
                                "unique_id": v["unique_id"],
                                "column": column,
                                "error_value": v[column],
                            }
                        )
        if not errors:
            return data, pd.DataFrame(
                columns=original_columns + ["column", "error_value"]
            )

        error_data = pd.DataFrame(errors)

        data = data.merge(error_data, on="unique_id", how="left", indicator=True)
        data["is_valid"] = data["_merge"] == "left_only"

        accepted_df = data[data["is_valid"]][original_columns]
        rejected_df = data[~data["is_valid"]].drop(columns=["_merge", "is_valid"])

        return accepted_df, rejected_df

    def validate_non_null_columns(
        self, data: pd.DataFrame, schema_model: ISchemaModel
    ) -> validated_data:
        original_columns = list(data.columns)
        errors = []

        for column in schema_model.non_null_columns:
            if column == "created_at":
                continue
            null_rows = data[data[column].isnull()]
            for _, row in null_rows.iterrows():
                errors.append(
                    {
                        "unique_id": row["unique_id"],
                        "column": column,
                        "error_value": "null",
                    }
                )

        error_data = pd.DataFrame(errors)

        if error_data.empty:
            return data, pd.DataFrame(
                columns=original_columns + ["column", "error_value"]
            )

        data = data.merge(error_data, on="unique_id", how="left", indicator=True)
        data["is_valid"] = data["_merge"] == "left_only"

        accepted_df = data[data["is_valid"]][original_columns]
        rejected_df = data[~data["is_valid"]].drop(columns=["_merge", "is_valid"])

        return accepted_df, rejected_df[original_columns + ["column", "error_value"]]
