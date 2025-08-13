#!/usr/bin/env python3
"""
Simple test to verify BLAST UI is accessible.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pathlib import Path

def test_simple_access():
    """Test if we can simply access the BLAST service."""
    
    # Minimal Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.binary_location = '/usr/bin/google-chrome-stable'
    
    try:
        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=options)
        
        # Try to access the BLAST service
        url = "http://127.0.0.1:4569/blast/WB/WS297"
        print(f"Testing URL: {url}")
        
        browser.get(url)
        title = browser.title
        print(f"Page title: {title}")
        
        # Take a screenshot
        screenshot_path = Path("simple_test_screenshot.png")
        browser.save_screenshot(str(screenshot_path))
        print(f"Screenshot saved: {screenshot_path}")
        
        browser.quit()
        print("✅ Simple test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Simple test failed: {str(e)}")
        if 'browser' in locals():
            try:
                browser.quit()
            except:
                pass
        return False

if __name__ == "__main__":
    test_simple_access()