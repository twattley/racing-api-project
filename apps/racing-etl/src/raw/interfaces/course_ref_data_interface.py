from typing import Protocol, Literal

from api_helpers.interfaces.storage_client_interface import IStorageClient


class ICourseRefData(Protocol):
    """
    source: Literal["rp", "tf"]
    storage_client: IStorageClient

    class to dynamically get the course ids and names for a given source
    from the database to be used in the results link scraper
    """

    def __init__(
        self, source: Literal["rp", "tf"], storage_client: IStorageClient
    ) -> None: ...

    def get_uk_ire_course_ids(self) -> dict[str, str]:
        """
        Get the UK and Ireland course ids and names for a given source

        Returns:
            dict[str, str]: A dictionary with the course id as the key and the course name as the value

            {
                "course_id": "course_name"
                ...
            }
        """
        ...

    def get_world_course_ids(self) -> dict[str, str]:
        """
        Get the world course ids and names for a given source

        Returns:
            dict[str, str]: A dictionary with the course id as the key and the course name as the value

            {
                "course_id": "course_name"
                ...
            }
        """
        ...

    def get_uk_ire_course_names(self) -> set[str]:
        """
        Get the UK and Ireland course names for a given source

        Returns:
            set[str]: A set of the course names

            {
                "course_name"
                ...
            }
        """
        ...

    def get_world_course_names(self) -> set[str]:
        """
        Get the world course names for a given source

        Returns:
            set[str]: A set of the world course names

            {
                "course_name"
                ...
            }
        """
        ...
