from typing import Protocol, Union

import pandas as pd
from playwright.sync_api import Page
from selenium import webdriver


class IDataScraper(Protocol):
    def scrape_data(
        self, driver: Union[webdriver.Chrome, Page], url: str
    ) -> pd.DataFrame: ...
