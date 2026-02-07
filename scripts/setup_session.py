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

    # Intercept both requests and responses to capture access token
    access_token = [None]  # Use list to avoid nonlocal issues

    def handle_request(request):
        # Try to capture authorization header from outgoing requests
        if "lift-api.vfsglobal.com" in request.url or "litf-api.vfsglobal.com" in request.url:
            print(f"🔍 Inspecting request to: {request.url}")
            headers = request.headers
            print(f"   Headers: {list(headers.keys())}")

            auth_header = headers.get('authorize') or headers.get('authorization') or headers.get('Authorize') or headers.get('Authorization')
            if auth_header:
                if not access_token[0]:
                    access_token[0] = auth_header.replace('Bearer ', '').strip()
                    print(f"🔑 Access token captured from request header! (length: {len(access_token[0])})")
            else:
                print(f"   ⚠️  No authorization header found")

    def handle_response(response):
        # Log all API responses for debugging
        if "lift-api" in response.url or "litf-api" in response.url:
            print(f"📡 API Response: {response.url} - Status: {response.status}")

        if "user/login" in response.url:
            print(f"🔍 Login API detected: {response.url} - Status: {response.status}")
            if response.status == 200:
                try:
                    data = response.json()
                    print(f"📦 Login response data keys: {list(data.keys())}")
                    if data.get('accessToken'):
                        access_token[0] = data['accessToken']
                        print(f"\n✅ Access token captured from login response! (length: {len(access_token[0])})")
                    else:
                        print(f"⚠️  No 'accessToken' key in response. Full data: {data}")
                except Exception as e:
                    print(f"⚠️  Error parsing login response: {e}")

    page.on("request", handle_request)
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

        # Navigate to dashboard to trigger API calls
        if not access_token[0]:
            print("🔄 Navigating to dashboard to trigger API calls...")
            try:
                page.goto("https://visa.vfsglobal.com/aze/en/ita/dashboard", wait_until="domcontentloaded", timeout=30000)
                time.sleep(5)  # Wait for API calls to complete
            except Exception as e:
                print(f"⚠️  Dashboard navigation: {e}")

        # Try to extract token from browser storage if not captured from API
        if not access_token[0]:
            print("🔍 Token not captured from API, searching browser storage...")
            token_from_storage = page.evaluate("""
                () => {
                    // Check all storage locations
                    const locations = [
                        localStorage.getItem('accessToken'),
                        localStorage.getItem('token'),
                        localStorage.getItem('authToken'),
                        localStorage.getItem('auth_token'),
                        localStorage.getItem('lift_token'),
                        sessionStorage.getItem('accessToken'),
                        sessionStorage.getItem('token'),
                        sessionStorage.getItem('authToken')
                    ];

                    // Return first non-null value
                    for (let val of locations) {
                        if (val) {
                            console.log('Found token in standard location');
                            return val;
                        }
                    }

                    // Try to find in all localStorage keys
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        if (key && key.toLowerCase().includes('token')) {
                            const value = localStorage.getItem(key);
                            if (value && value.length > 50) {  // Tokens are usually long
                                console.log('Found token in key:', key);
                                return value;
                            }
                        }
                    }

                    // Try to find in all sessionStorage keys
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        if (key && key.toLowerCase().includes('token')) {
                            const value = sessionStorage.getItem(key);
                            if (value && value.length > 50) {
                                console.log('Found token in session key:', key);
                                return value;
                            }
                        }
                    }

                    return null;
                }
            """)

            if token_from_storage:
                access_token[0] = token_from_storage
                print(f"✅ Token extracted from browser storage (length: {len(access_token[0])})")
            else:
                print("⚠️  Token not found in browser storage either")

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
