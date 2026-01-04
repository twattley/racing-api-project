import math

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator


class BaseRaceModel(BaseModel):
    """Base model with NaN handling and common configuration for all race-related models"""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        # Add any other common config here
    )

    @field_validator("*", mode="before")
    @classmethod
    def handle_nan_values(cls, v):
        """Convert various NaN representations to None"""
        if v is None:
            return None

        # Skip validation for lists, tuples, and other complex types
        if isinstance(v, (list, tuple, dict)):
            return v

        # Handle numeric NaN/inf
        if isinstance(v, (float, int)):
            if math.isnan(v) or math.isinf(v):
                return None

        # Handle pandas/numpy types
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass

        # Handle empty strings
        if isinstance(v, str) and v.strip() == "":
            return None

        # Rely on pandas.isna above to handle pandas/numpy NA/NaT cases

        return v

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, **kwargs):
        """Create models from DataFrame with automatic NaN handling"""
        records = df.to_dict("records")
        # Ensure keys are strings for safe model construction
        return [
            cls(**{str(k): v for k, v in record.items()}, **kwargs)
            for record in records
        ]

    # -------- Convenience helpers: model(s) -> DataFrame --------
    def to_dataframe(
        self,
        by_alias: bool = True,
        exclude_none: bool = False,
    ) -> pd.DataFrame:
        """Convert a single model instance to a one-row DataFrame.

        Args:
            by_alias: Use field aliases if defined.
            exclude_none: Drop keys with None values if True.
        """
        data = self.model_dump(
            mode="python", by_alias=by_alias, exclude_none=exclude_none
        )
        return pd.DataFrame([data])

    @classmethod
    def list_to_dataframe(
        cls,
        items: list["BaseRaceModel"],
        by_alias: bool = True,
        exclude_none: bool = False,
    ) -> pd.DataFrame:
        """Convert a list of model instances to a DataFrame.

        Args:
            items: List of BaseRaceModel (or subclasses) instances.
            by_alias: Use field aliases if defined.
            exclude_none: Drop keys with None values if True.
        """
        rows = [
            item.model_dump(mode="python", by_alias=by_alias, exclude_none=exclude_none)
            for item in items
        ]
        return pd.DataFrame(rows)
