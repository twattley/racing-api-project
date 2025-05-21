from typing import Any, Dict, Protocol


class IDataModel(Protocol):
    def validate_columns(self, data: Dict[str, Any]) -> bool:
        """
        Ensure all required columns are present in the data.
        """

    def validate_field_lengths(self, data: Dict[str, Any]) -> bool:
        """
        Check if the lengths of string fields in the data match the defined lengths.
        """

    def get_field_lengths(self) -> Dict[str, int]:
        """
        Return a dictionary of field names and their maximum lengths.
        """
