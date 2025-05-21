from typing import Protocol

from api_helpers.interfaces.storage_client_interface import IStorageClient


class IEntityMatching(Protocol):
    """
    source: Literal["rp", "tf"]
    storage_client: IStorageClient

    class to dynamically get the course ids and names for a given source
    from the database to be used in the results link scraper
    """

    def __init__(self, storage_client: IStorageClient) -> None: ...

    def run_matching(self): ...

    def fetch_data(self): ...

    def match_data(self): ...

    def store_data(self): ...

    def create_entity_data(self): ...
