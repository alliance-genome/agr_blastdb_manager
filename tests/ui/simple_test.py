#!/usr/bin/env python3
"""
Simple test to verify BLAST UI is accessible.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def test_simple_access(url: str = "http://127.0.0.1:4569/blast/WB/WS297"):
    """Test if we can simply access the BLAST service."""
    # Set PLAYWRIGHT_CHANNEL=chrome to use an installed Chrome instead of
    # Playwright's own Chromium (`uv run playwright install chromium`).
    channel = os.environ.get("PLAYWRIGHT_CHANNEL") or None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, channel=channel)
            try:
                page = browser.new_page()

                # Try to access the BLAST service
                print(f"Testing URL: {url}")
                page.goto(url)
                print(f"Page title: {page.title()}")

                # Take a screenshot
                screenshot_path = Path("simple_test_screenshot.png")
                page.screenshot(path=str(screenshot_path))
                print(f"Screenshot saved: {screenshot_path}")
            finally:
                browser.close()

        print("✅ Simple test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Simple test failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_simple_access()
