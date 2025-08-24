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

        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None

        # Only check pandas NaN for scalar values, not arrays/lists
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            # If pd.isna fails (e.g., for complex objects), just continue
            pass

        if isinstance(v, str) and v.strip() == "":
            return None
        return v
