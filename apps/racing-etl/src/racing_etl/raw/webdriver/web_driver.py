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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    NoSuchElementException,
    WebDriverException,
)
import time

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
        """
        Resilient login function for Timeform with cookie consent handling
        """
        I("Logging in to Timeform")

        try:
            # Navigate to login page
            driver.get(
                "https://www.timeform.com/horse-racing/account/sign-in?returnUrl=%2Fhorse-racing"
            )

            # Wait for page to load
            wait = WebDriverWait(driver, 10)

            # Handle cookie consent banner if present
            self._handle_cookie_consent(driver, wait)

            # Fill in email
            email_element = wait.until(
                EC.element_to_be_clickable((By.NAME, "EmailAddress"))
            )
            email_element.clear()
            email_element.send_keys(self.config.tf_email)

            # Fill in password
            password_element = wait.until(
                EC.element_to_be_clickable((By.NAME, "Password"))
            )
            password_element.clear()
            password_element.send_keys(self.config.tf_password)

            # Submit the form with retry logic
            self._submit_login_form(driver, wait)

            # Wait for successful login (adjust selector based on post-login page)
            wait.until(EC.url_contains("horse-racing"))

            I("Log in to Timeform success")

        except TimeoutException as e:
            raise Exception(f"Timeout during login process: {e}")
        except WebDriverException as e:
            raise Exception(f"WebDriver error during login: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error during login: {e}")

    def _handle_cookie_consent(
        self, driver: webdriver.Chrome, wait: WebDriverWait
    ) -> None:
        """
        Handle cookie consent banner if present
        """
        try:
            # Common selectors for cookie consent buttons
            cookie_selectors = [
                "#onetrust-accept-btn-handler",  # OneTrust accept button
                "[id*='accept']",  # Generic accept button
                "[class*='accept']",  # Generic accept class
                ".ot-sdk-show-settings",  # OneTrust settings
            ]

            for selector in cookie_selectors:
                try:
                    cookie_button = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if cookie_button.is_displayed():
                        # Scroll to cookie button to ensure it's clickable
                        driver.execute_script(
                            "arguments[0].scrollIntoView(true);", cookie_button
                        )
                        cookie_button.click()
                        I(f"Clicked cookie consent button: {selector}")
                        time.sleep(1)  # Brief pause after cookie consent
                        break
                except (TimeoutException, NoSuchElementException):
                    continue

        except Exception as e:
            I(f"Cookie consent handling failed (continuing anyway): {e}")

    def _submit_login_form(
        self, driver: webdriver.Chrome, wait: WebDriverWait, max_retries: int = 3
    ) -> None:
        """
        Submit login form with retry logic for click interception
        """
        submit_selectors = [
            ".submit-section",  # Original selector
            "[type='submit']",  # Generic submit button
            "button[type='submit']",  # Submit button element
            ".login-form button",  # Form-specific button
            ".sign-in-form button",  # Alternative form button
        ]

        for attempt in range(max_retries):
            try:
                I(f"Attempting to submit form (attempt {attempt + 1}/{max_retries})")

                # Try different submit button selectors
                submit_button = None
                for selector in submit_selectors:
                    try:
                        submit_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue

                if not submit_button:
                    raise Exception(
                        "Could not find submit button with any known selector"
                    )

                # Scroll to button to ensure it's in view
                driver.execute_script(
                    "arguments[0].scrollIntoView(true);", submit_button
                )
                time.sleep(0.5)

                # Try regular click first
                try:
                    submit_button.click()
                    I("Form submitted successfully")
                    return
                except ElementClickInterceptedException:
                    I("Regular click intercepted, trying JavaScript click")
                    # If regular click is intercepted, try JavaScript click
                    driver.execute_script("arguments[0].click();", submit_button)
                    I("Form submitted via JavaScript click")
                    return

            except ElementClickInterceptedException as e:
                if attempt < max_retries - 1:
                    I(f"Click intercepted on attempt {attempt + 1}, retrying...")
                    # Wait a bit longer and try to dismiss any overlays
                    time.sleep(2)
                    self._dismiss_overlays(driver)
                else:
                    raise Exception(
                        f"Failed to submit form after {max_retries} attempts: {e}"
                    )

            except Exception as e:
                if attempt < max_retries - 1:
                    I(f"Submit attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(2)
                else:
                    raise Exception(
                        f"Failed to submit form after {max_retries} attempts: {e}"
                    )

    def _dismiss_overlays(self, driver: webdriver.Chrome) -> None:
        """
        Try to dismiss any overlays that might be blocking the submit button
        """
        try:
            # Try to close common overlay elements
            overlay_selectors = [
                ".ot-sdk-container button",  # OneTrust overlay buttons
                "[id*='close']",  # Generic close buttons
                "[class*='close']",  # Generic close classes
                ".modal-close",  # Modal close buttons
                ".popup-close",  # Popup close buttons
            ]

            for selector in overlay_selectors:
                try:
                    overlay_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in overlay_elements:
                        if element.is_displayed():
                            element.click()
                            I(f"Dismissed overlay element: {selector}")
                            time.sleep(0.5)
                except Exception:
                    continue

        except Exception as e:
            I(f"Overlay dismissal failed (continuing anyway): {e}")
