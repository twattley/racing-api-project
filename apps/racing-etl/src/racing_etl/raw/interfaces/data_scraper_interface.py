from typing import Protocol

import pandas as pd
from selenium import webdriver


class IDataScraper(Protocol):
    def scrape_data(self, driver: webdriver.Chrome, url: str) -> pd.DataFrame: ...
