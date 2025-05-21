from typing import Protocol


class DataStore(Protocol):
    def get_data(self, *args, **kwargs): ...

    def store_data(self, *args, **kwargs): ...


class InMemoryDataStore(DataStore):
    def get_data(self, *args, **kwargs):
        print(args)

    def store_data(self, *args, **kwargs):
        print(args)
