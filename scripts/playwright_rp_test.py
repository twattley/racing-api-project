"""
Standalone Playwright test script for Racing Post scraping.

This is a proof-of-concept to verify Playwright can bypass Racing Post's
bot detection that was blocking Selenium.

Run with: python scripts/playwright_rp_test.py
         python scripts/playwright_rp_test.py --login   # to test login flow

What this does:
1. Launches a browser (visible, so you can watch)
2. Navigates to Racing Post racecards
3. Extracts all race links for today
4. Prints them out for manual verification

Compare the output to what you see on the actual site to verify it works.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

# Path to save login session
AUTH_FILE = Path(__file__).parent / "rp_auth.json"


def login_and_save_session():
    """
    Logs in using RP_USER and RP_PWD env vars, saves session for reuse.
    """
    username = os.environ.get("RP_USER")
    password = os.environ.get("RP_PWD")

    if not username or not password:
        raise ValueError("Set RP_USER and RP_PWD environment variables")

    print("=" * 60)
    print("RACING POST LOGIN")
    print("=" * 60)
    print(f"Logging in as: {username}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        page = context.new_page()
        page.goto(
            "https://www.racingpost.com/auth/login/", wait_until="domcontentloaded"
        )

        # Wait for login form to appear
        page.wait_for_selector("input[name='username']", timeout=15000)

        print("📝 Filling login form...")

        # Fill credentials
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)

        print("🔐 Submitting...")

        # Click submit button - try common patterns
        # Update this selector once you tell me what the button looks like
        page.click("button[type='submit']")

        # Wait for redirect after login (should go to homepage or racecards)
        page.wait_for_url("https://www.racingpost.com/**", timeout=30000)

        print("✅ Logged in successfully!")

        # Save the session (cookies, localStorage, etc.)
        context.storage_state(path=str(AUTH_FILE))
        print(f"💾 Session saved to {AUTH_FILE}")

        browser.close()


def get_todays_racecard_links(
    headless: bool = False, use_auth: bool = False
) -> list[str]:
    """
    Scrape today's racecard links from Racing Post using Playwright.

    Args:
        headless: If True, run browser without visible window
        use_auth: If True, use saved login session

    Returns a sorted list of race URLs.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    base_url = "https://www.racingpost.com/racecards"

    print(f"🏇 Scraping Racing Post racecards for {today}")
    print(f"🌐 Navigating to {base_url}")
    print(f"👻 Headless mode: {headless}")
    print(f"🔐 Using saved auth: {use_auth}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)

        # Load saved session if available and requested
        if use_auth and AUTH_FILE.exists():
            print(f"📂 Loading session from {AUTH_FILE}")
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                storage_state=str(AUTH_FILE),
            )
        else:
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

        page = context.new_page()
        page.goto(base_url, wait_until="domcontentloaded", timeout=60000)

        print("✅ DOM loaded, waiting for race links to appear...")

        page.wait_for_selector("a[href*='/racecards/']", timeout=30000)
        page.wait_for_timeout(2000)

        hrefs = page.eval_on_selector_all(
            "a[href]", "elements => elements.map(el => el.href)"
        )

        print(f"📊 Found {len(hrefs)} total links on page")

        racecard_links = [
            href.rstrip("/") for href in hrefs if href and "racecards" in href
        ]

        print(f"🏁 Found {len(racecard_links)} racecard-related links")

        pattern = rf"https://www\.racingpost\.com/racecards/\d+/[\w-]+/{today}/\d+$"

        todays_races = sorted(
            set(href for href in racecard_links if re.match(pattern, href))
        )

        print(f"🎯 Found {len(todays_races)} races for today ({today})")

        browser.close()

    return todays_races


def main():
    # If --login flag, do login flow
    if "--login" in sys.argv:
        login_and_save_session()
        return

    print("=" * 60)
    print("PLAYWRIGHT RACING POST TEST")
    print("=" * 60)
    print()

    # Use auth if session file exists
    use_auth = AUTH_FILE.exists()
    headless = False

    print(f"Testing with headless={headless}")
    print()

    try:
        links = get_todays_racecard_links(headless=headless, use_auth=use_auth)

        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)

        if links:
            print(f"\n✅ SUCCESS! Found {len(links)} race links:\n")
            for i, link in enumerate(links, 1):
                print(f"  {i:3}. {link}")

            print()
            print("🔍 VERIFICATION:")
            print("   1. Open https://www.racingpost.com/racecards in your browser")
            print("   2. Count the races listed for today")
            print("   3. Compare with the count above")
        else:
            print("\n⚠️  No races found for today.")
            print("   This might be normal if there's no racing today,")
            print("   or it could indicate the scraper needs adjustment.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n   If this is a timeout or detection error,")
        print("   we may need to add stealth techniques.")
        raise


if __name__ == "__main__":
    main()
