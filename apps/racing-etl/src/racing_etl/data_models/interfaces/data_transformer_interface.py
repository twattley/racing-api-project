from typing import Protocol

import pandas as pd


class IDataTransformer(Protocol):
    def transform_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the input DataFrame.
        """
        ...
