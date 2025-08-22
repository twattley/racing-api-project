import random
import time

from api_helpers.config import Config
from api_helpers.helpers.logging_config import D, E, I
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from racing_etl.raw.interfaces.webriver_interface import IWebDriver

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 14_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/601.7.7 (KHTML, like Gecko) Version/9.1.2 Safari/601.7.7",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Linux; Android 9; SM-G960F Build/PPR1.180610.011) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 8.0.0; SM-N950F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.210 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (X11; CrOS x86_64 13729.56.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.95 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; ) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
    "Mozilla/5.0 (Windows NT 5.1; rv:88.0) Gecko/20100101 Firefox/88.0",
]


class WebDriver(IWebDriver):
    def __init__(self, config: Config, headless_mode: bool, website: str):
        self.config = config
        self.headless_mode = headless_mode
        self.website = website

    def create_session(self) -> webdriver.Chrome:
        options = Options()
        if self.headless_mode:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        options.add_experimental_option("prefs", prefs)
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

        D(f"Chrome options: {options}")
        D(f"Chrome chromedriver_path: {self.config.chromedriver_path}")

        service = Service(executable_path=self.config.chromedriver_path)

        driver = webdriver.Chrome(service=service, options=options)

        if self.website == "timeform":
            self.login_to_timeform(driver)

        I("Webdriver session created")

        return driver

    def wait_for_page_load(
        self, driver: webdriver.Chrome, items: list[tuple[str, str]]
    ) -> None:
        missing_elements = []
        for selector, name in items:
            try:
                D(f"Waiting for element: {name}")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            except TimeoutException:
                E(f"Missing element: {name}")
                missing_elements.append(name)
        if missing_elements:
            raise ValueError(f"Missing elements: {', '.join(missing_elements)}")

    def login_to_timeform(self, driver: webdriver.Chrome) -> None:
        I("Logging in to Timeform")
        driver.get(
            "https://www.timeform.com/horse-racing/account/sign-in?returnUrl=%2Fhorse-racing"
        )
        time.sleep(5)
        email = driver.find_element(by=By.NAME, value="EmailAddress")
        time.sleep(2)
        email.send_keys(self.config.tf_email)
        time.sleep(3)
        password = driver.find_element(by=By.NAME, value="Password")
        time.sleep(3)
        password.send_keys(self.config.tf_password)
        time.sleep(3)
        driver.find_element(by=By.CLASS_NAME, value="submit-section").click()
        time.sleep(3)
        I("Log in to Timeform success")
