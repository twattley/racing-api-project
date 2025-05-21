from typing import Protocol

import pandas as pd
from selenium import webdriver


class IDataScraper(Protocol):
    def scrape_data(self, url: str, driver: webdriver.Chrome) -> pd.DataFrame: ...
