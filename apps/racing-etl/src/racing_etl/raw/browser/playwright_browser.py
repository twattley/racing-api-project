"""
Base Playwright browser class for web scraping.

This replaces the Selenium WebDriver with Playwright for better bot detection evasion.
Can be used by both Racing Post and Timeform scrapers.

Usage:
    browser = PlaywrightBrowser(headless=True)
    page = browser.create_session(website="racingpost")

    # Use the page...
    page.goto("https://www.racingpost.com/racecards")


    # When done
    browser.close()
"""

import os
import random
import time
from pathlib import Path
from typing import Literal

from api_helpers.helpers.logging_config import D, E, I
from playwright.sync_api import Page, sync_playwright

# Auth file locations - in scripts/ at repo root
AUTH_DIR = Path(__file__).parents[6] / "scripts"
RP_AUTH_FILE = AUTH_DIR / "rp_auth.json"
TF_AUTH_FILE = AUTH_DIR / "tf_auth.json"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
]


def human_delay(min_ms: int = 50, max_ms: int = 150) -> float:
    """Return a random human-like delay in seconds."""
    return random.randint(min_ms, max_ms) / 1000


class PlaywrightBrowser:
    """
    Playwright-based browser for web scraping.

    Replaces Selenium WebDriver with better bot detection evasion.
    Supports login session persistence for Racing Post and Timeform.
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the browser.

        Args:
            headless: Run browser without visible window (default True for production)
        """
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def create_session(
        self, website: Literal["racingpost", "timeform"] = "racingpost"
    ) -> Page:
        """
        Create a new browser session, optionally with saved auth.

        Args:
            website: Which website to create session for (determines auth file)

        Returns:
            Playwright Page object
        """
        I(f"Creating Playwright session for {website} (headless={self.headless})")

        self._playwright = sync_playwright().start()

        # Use Chromium with stealth settings
        self._browser = self._playwright.chromium.launch(headless=self.headless)

        # Determine auth file
        auth_file = RP_AUTH_FILE if website == "racingpost" else TF_AUTH_FILE

        # Create context with realistic settings
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": random.choice(USER_AGENTS),
            "locale": "en-GB",
            "timezone_id": "Europe/London",
        }

        # For Racing Post, try to use saved session if available
        if website == "racingpost" and auth_file.exists():
            D(f"Loading saved auth from {auth_file}")
            context_options["storage_state"] = str(auth_file)

        self._context = self._browser.new_context(**context_options)
        self._page = self._context.new_page()

        # Always login fresh for Timeform (session management is unreliable)
        if website == "timeform":
            self._login_to_timeform()
        elif website == "racingpost":
            if not auth_file.exists():
                self._login_to_racingpost()

        I("Playwright session created")
        return self._page

    def _type_like_human(self, selector: str, text: str) -> None:
        """Type text character by character with human-like delays."""
        element = self._page.locator(selector)
        element.click()
        time.sleep(human_delay(200, 400))

        for char in text:
            element.press_sequentially(char, delay=random.randint(50, 150))
            time.sleep(human_delay(30, 80))

    def _login_to_racingpost(self) -> None:
        """
        Login to Racing Post using environment credentials.
        Saves session for future use.
        """
        username = os.environ.get("RP_USER")
        password = os.environ.get("RP_PWD")

        if not username or not password:
            I("RP_USER/RP_PWD not set - skipping login (will scrape as anonymous)")
            return

        I("Logging in to Racing Post...")

        try:
            # First visit homepage to establish cookies
            self._page.goto(
                "https://www.racingpost.com/",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            time.sleep(random.uniform(2, 4))

            # Handle cookie consent if present
            self._handle_cookie_consent()
            time.sleep(random.uniform(1, 2))

            # Now go to login page
            self._page.goto(
                "https://www.racingpost.com/auth/login/",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            time.sleep(random.uniform(2, 3))

            # Wait for and fill login form with human-like typing
            self._page.wait_for_selector("input[name='username']", timeout=15000)
            time.sleep(random.uniform(0.5, 1))

            # Type username slowly
            self._type_like_human("input[name='username']", username)
            time.sleep(random.uniform(0.3, 0.7))

            # Type password slowly
            self._type_like_human("input[name='password']", password)
            time.sleep(random.uniform(0.5, 1))

            # Submit with a slight delay
            self._page.click("button[type='submit']")

            # Wait for redirect (indicates successful login)
            self._page.wait_for_timeout(5000)

            if "login" not in self._page.url.lower():
                I("Racing Post login successful")
                self._save_session(RP_AUTH_FILE)
            else:
                E("Racing Post login may have failed - still on login page")

        except Exception as e:
            E(f"Racing Post login failed: {e}")
            # Continue anyway - some scraping works without login

    def _login_to_timeform(self) -> None:
        """
        Login to Timeform using environment credentials.
        Saves session for future use.
        """
        email = os.environ.get("TF_EMAIL")
        password = os.environ.get("TF_PASSWORD")

        if not email or not password:
            E("TF_EMAIL/TF_PASSWORD not set - Timeform requires login")
            raise ValueError("Timeform credentials required")

        I("Logging in to Timeform...")

        # Delete old auth file if it exists (it's stale)
        if TF_AUTH_FILE.exists():
            D(f"Removing stale auth file: {TF_AUTH_FILE}")
            TF_AUTH_FILE.unlink()

        try:
            self._page.goto(
                "https://www.timeform.com/horse-racing/account/sign-in?returnUrl=%2Fhorse-racing",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            time.sleep(random.uniform(2, 3))

            # Handle cookie consent if present
            self._handle_cookie_consent()
            time.sleep(random.uniform(1, 2))

            # Wait for and fill login form with human-like typing
            self._page.wait_for_selector("input[name='EmailAddress']", timeout=15000)
            time.sleep(random.uniform(0.5, 1))

            # Type email slowly
            self._type_like_human("input[name='EmailAddress']", email)
            time.sleep(random.uniform(0.3, 0.7))

            # Type password slowly
            self._type_like_human("input[name='Password']", password)
            time.sleep(random.uniform(0.5, 1))

            # Submit with a slight delay
            self._page.click("button[type='submit'], .submit-section")

            # Wait for redirect (indicates successful login)
            try:
                self._page.wait_for_url("**/horse-racing**", timeout=30000)
            except Exception:
                # URL might not change exactly as expected, check for login success differently
                self._page.wait_for_timeout(5000)

            # Verify login was successful
            if "sign-in" in self._page.url.lower():
                E("Timeform login failed - still on sign-in page")
                raise ValueError("Timeform login failed - check credentials")

            I("Timeform login successful")
            self._save_session(TF_AUTH_FILE)

        except Exception as e:
            E(f"Timeform login failed: {e}")
            raise

    def _handle_cookie_consent(self) -> None:
        """Handle cookie consent banners."""
        try:
            # Try common cookie consent selectors
            selectors = [
                "#onetrust-accept-btn-handler",
                "[id*='accept']",
                "button:has-text('Accept')",
            ]

            for selector in selectors:
                try:
                    button = self._page.locator(selector).first
                    if button.is_visible(timeout=2000):
                        button.click()
                        I(f"Clicked cookie consent: {selector}")
                        self._page.wait_for_timeout(1000)
                        return
                except Exception:
                    continue

        except Exception as e:
            D(f"Cookie consent handling skipped: {e}")

    def _save_session(self, auth_file: Path) -> None:
        """Save current session state to file."""
        try:
            self._context.storage_state(path=str(auth_file))
            I(f"Session saved to {auth_file}")
        except Exception as e:
            E(f"Failed to save session: {e}")

    def close(self) -> None:
        """Close browser and cleanup resources."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            I("Browser closed")
        except Exception as e:
            E(f"Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures browser is closed."""
        self.close()
        return False
