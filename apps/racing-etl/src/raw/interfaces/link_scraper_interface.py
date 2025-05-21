from typing import Protocol

import pandas as pd
from selenium import webdriver


class ILinkScraper(Protocol):
    def scrape_links(self, driver: webdriver.Chrome, date: str) -> pd.DataFrame: ...
