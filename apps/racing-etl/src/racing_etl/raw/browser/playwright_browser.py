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
from pathlib import Path
from typing import Literal

from api_helpers.helpers.logging_config import D, E, I
from playwright.sync_api import Page, sync_playwright

# Auth file locations - in scripts/ at repo root
AUTH_DIR = Path(__file__).parents[6] / "scripts"
RP_AUTH_FILE = AUTH_DIR / "rp_auth.json"
TF_AUTH_FILE = AUTH_DIR / "tf_auth.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


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
        self._browser = self._playwright.chromium.launch(headless=self.headless)

        # Determine auth file
        auth_file = RP_AUTH_FILE if website == "racingpost" else TF_AUTH_FILE

        # Create context with realistic settings
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": random.choice(USER_AGENTS),
        }

        # Load saved session if available
        if auth_file.exists():
            D(f"Loading saved auth from {auth_file}")
            context_options["storage_state"] = str(auth_file)

        self._context = self._browser.new_context(**context_options)
        self._page = self._context.new_page()

        # Login if needed and no saved session
        if not auth_file.exists():
            if website == "racingpost":
                self._login_to_racingpost()
            elif website == "timeform":
                self._login_to_timeform()

        I("Playwright session created")
        return self._page

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
            self._page.goto(
                "https://www.racingpost.com/auth/login/",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # Wait for and fill login form
            self._page.wait_for_selector("input[name='username']", timeout=15000)
            self._page.fill("input[name='username']", username)
            self._page.fill("input[name='password']", password)

            # Submit
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

        try:
            self._page.goto(
                "https://www.timeform.com/horse-racing/account/sign-in?returnUrl=%2Fhorse-racing",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            # Handle cookie consent if present
            self._handle_cookie_consent()

            # Wait for and fill login form
            self._page.wait_for_selector("input[name='EmailAddress']", timeout=15000)
            self._page.fill("input[name='EmailAddress']", email)
            self._page.fill("input[name='Password']", password)

            # Submit
            self._page.click("button[type='submit'], .submit-section")

            # Wait for redirect
            self._page.wait_for_url("**/horse-racing**", timeout=30000)

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
