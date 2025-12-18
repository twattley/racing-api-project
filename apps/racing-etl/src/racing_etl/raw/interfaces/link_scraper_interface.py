from typing import Protocol

import pandas as pd
from playwright.sync_api import Page


class ILinkScraper(Protocol):
    def scrape_links(
        self, page: Page, date: str
    ) -> pd.DataFrame: ...
