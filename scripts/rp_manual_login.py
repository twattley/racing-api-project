"""
Racing Post Session Capture - Login manually, save session for automation.

This approach avoids bot detection by:
1. Launching a REAL Chrome browser (not Playwright's Chromium)
2. You login manually like a normal user
3. Script captures your cookies/session for later automation

Run: python scripts/playwright_rp_stealth.py
"""

import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

AUTH_FILE = Path(__file__).parent / "rp_auth.json"
CHROME_DEBUG_PORT = 9222


def find_chrome_path() -> str:
    """Find Chrome executable on macOS."""
    paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None


def capture_session_from_manual_login():
    """
    Launch Chrome for manual login, then capture the session.
    """
    print("=" * 60)
    print("RACING POST - MANUAL LOGIN SESSION CAPTURE")
    print("=" * 60)
    print()
    print("⚠️  FIRST: Close ALL Chrome windows!")
    print()
    input("Press Enter when Chrome is completely closed...")

    chrome_path = find_chrome_path()
    if not chrome_path:
        print("❌ Chrome not found. Install Google Chrome.")
        return False

    print()
    print("🚀 Launching Chrome with debugging enabled...")
    print("   A Chrome window will open.")
    print()
    print("📝 YOUR TASK:")
    print("   1. Go to https://www.racingpost.com")
    print("   2. Click 'Log in'")
    print("   3. Login with your credentials")
    print("   4. Solve any CAPTCHA they show")
    print("   5. Make sure you're logged in (see your name in top right)")
    print("   6. Come back here and press Enter")
    print()

    # Launch Chrome with remote debugging
    chrome_process = subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={CHROME_DEBUG_PORT}",
            "--user-data-dir=/tmp/rp_chrome_profile",
            "--no-first-run",
            "--no-default-browser-check",
            "https://www.racingpost.com",
        ]
    )

    print("✅ Chrome launched. Complete the login, then come back here.")
    print()
    input("Press Enter AFTER you've logged in successfully...")

    print()
    print("🔄 Connecting to Chrome to capture session...")

    try:
        with sync_playwright() as p:
            # Connect to the running Chrome instance
            browser = p.chromium.connect_over_cdp(
                f"http://localhost:{CHROME_DEBUG_PORT}"
            )

            # Get the default context (your logged-in session)
            context = browser.contexts[0]

            # Save the session state (cookies, localStorage, etc.)
            context.storage_state(path=str(AUTH_FILE))

            print(f"✅ Session saved to {AUTH_FILE}")
            print()
            print("🎉 SUCCESS! You can now close Chrome.")
            print()
            print("To use this session in your scraper, it will automatically")
            print("load from the saved file.")

            browser.close()

    except Exception as e:
        print(f"❌ Error capturing session: {e}")
        print()
        print("Make sure you completed login and are on racingpost.com")
        return False

    # Kill the Chrome process
    chrome_process.terminate()

    return True


def test_saved_session():
    """
    Test that the saved session works.
    """
    if not AUTH_FILE.exists():
        print("❌ No saved session. Run capture first.")
        return False

    print()
    print("🧪 Testing saved session...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        # Go to a page that requires login
        page.goto(
            "https://www.racingpost.com/my-racing-post", wait_until="domcontentloaded"
        )
        time.sleep(3)

        # Check if we're logged in
        if "login" in page.url.lower():
            print("❌ Session expired or invalid - need to login again")
            browser.close()
            return False
        else:
            print("✅ Session is valid! You're logged in.")
            print(f"   Current URL: {page.url}")

            # Try getting racecards
            page.goto(
                "https://www.racingpost.com/racecards", wait_until="domcontentloaded"
            )
            time.sleep(2)
            print(f"   Racecards page: {page.url}")

            print()
            print("🎉 Everything works! Close browser when ready.")
            input("Press Enter to close...")
            browser.close()
            return True


def main():
    print()
    if AUTH_FILE.exists():
        print(f"📁 Found existing session: {AUTH_FILE}")
        print()
        print("Options:")
        print("  1. Test existing session")
        print("  2. Capture new session (login again)")
        print("  3. Delete session and exit")
        print()
        choice = input("Choose (1/2/3): ").strip()

        if choice == "1":
            test_saved_session()
        elif choice == "2":
            if capture_session_from_manual_login():
                test_saved_session()
        elif choice == "3":
            AUTH_FILE.unlink()
            print("🗑️  Session deleted")
        else:
            print("Invalid choice")
    else:
        print("📁 No saved session found")
        print()
        if capture_session_from_manual_login():
            test_saved_session()


if __name__ == "__main__":
    main()
