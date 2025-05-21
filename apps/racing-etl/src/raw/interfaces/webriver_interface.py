from typing import Protocol

from selenium import webdriver


class IWebDriver(Protocol):
    def create_session(self, login: bool = False) -> webdriver.Chrome: ...
