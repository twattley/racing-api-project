from typing import Protocol

import pandas as pd
from playwright.sync_api import Page


class IDataScraper(Protocol):
    def scrape_data(
        self, page: Page, url: str
    ) -> pd.DataFrame: ...
