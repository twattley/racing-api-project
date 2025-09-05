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

        # Handle pandas Timestamp specifically (if you use them)
        if hasattr(v, "isnull") and v.isnull():
            return None

        return v

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, **kwargs):
        """Create models from DataFrame with automatic NaN handling"""
        records = df.to_dict("records")
        return [cls(**record, **kwargs) for record in records]
