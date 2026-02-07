#!/usr/bin/env python3
"""
One-time setup script to create a browser session.
Run this once, login manually, and it will save your session for automation.
"""
import sys
import time
from playwright.sync_api import sync_playwright

STORAGE_FILE = "browser_state.json"

print("=" * 60)
print("🔧 One-Time Session Setup")
print("=" * 60)
print("\nThis script will:")
print("1. Open a browser window")
print("2. You login manually")
print("3. Save your session for automation")
print("\nYou only need to do this ONCE (lasts 2-4 weeks)!")
print("=" * 60)
print("\n🚀 Starting in 3 seconds...")
time.sleep(3)

with sync_playwright() as p:
    # Launch browser in headed mode (visible)
    print("\n📖 Opening Firefox browser...")
    browser = p.firefox.launch(headless=False)

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        viewport={'width': 1920, 'height': 1080}
    )

    page = context.new_page()

    # Intercept login API to capture access token
    access_token = [None]  # Use list to avoid nonlocal issues

    def handle_response(response):
        if "user/login" in response.url and response.status == 200:
            try:
                data = response.json()
                if data.get('accessToken'):
                    access_token[0] = data['accessToken']
                    print(f"\n✅ Access token captured! (length: {len(access_token[0])})")
            except:
                pass

    page.on("response", handle_response)

    # Navigate to login page
    print("📄 Loading VFS Global login page...")
    page.goto("https://visa.vfsglobal.com/aze/en/ita/login")

    print("\n" + "=" * 60)
    print("✋ PLEASE LOGIN IN THE BROWSER WINDOW")
    print("=" * 60)
    print("1. Accept cookies if prompted")
    print("2. Enter your email and password")
    print("3. Click 'Log In'")
    print("4. Wait until you see your dashboard")
    print("\n⏳ Waiting for you to login...")
    print("   (This script will detect when you're logged in)")

    # Wait for dashboard or successful login indicator
    try:
        # Wait for either dashboard or any page that's not login
        page.wait_for_function(
            "window.location.href.includes('dashboard') || !window.location.href.includes('login')",
            timeout=300000  # 5 minutes
        )
        print("\n✅ Login detected!")
        time.sleep(3)  # Give it a moment to settle
    except:
        print("\n⚠️  Timeout - please make sure you logged in")

    # Save the storage state (cookies, local storage, etc.)
    context.storage_state(path=STORAGE_FILE)

    # Save the access token separately if captured
    if access_token[0]:
        with open("access_token.txt", "w") as f:
            f.write(access_token[0])
        print(f"✅ Access token saved to access_token.txt")
    else:
        print("⚠️  Access token not captured during login")

    print(f"✅ Session saved to {STORAGE_FILE}")

    browser.close()

print("\n" + "=" * 60)
print("🎉 SETUP COMPLETE!")
print("=" * 60)
print("\n📋 Next steps:")
print("1. Test locally: python scripts/check_slots.py")
print("2. For GitHub Actions:")
print("   - Run: base64 browser_state.json | pbcopy")
print("   - Go to GitHub repo → Settings → Secrets")
print("   - Add secret: BROWSER_STATE_BASE64")
print("   - Paste the copied value")
print("=" * 60)
