from typing import Protocol, Union

import pandas as pd
from playwright.sync_api import Page
from selenium import webdriver


class ILinkScraper(Protocol):
    def scrape_links(
        self, driver: Union[webdriver.Chrome, Page], date: str
    ) -> pd.DataFrame: ...
