import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USER_EMAIL = os.getenv('USER_EMAIL')
USER_PASSWORD = os.getenv('USER_PASSWORD')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_PERSONAL_CHAT_ID = os.getenv('TELEGRAM_PERSONAL_CHAT_ID')
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')

# API Configuration
BASE_URL = "https://lift-api.vfsglobal.com"
LOGIN_URL = f"{BASE_URL}/user/login"
SLOT_CHECK_URL = f"{BASE_URL}/appointment/CheckIsSlotAvailable"

# Request Configuration
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://visa.vfsglobal.com",
    "referer": "https://visa.vfsglobal.com/",
    "route": "aze/en/ita",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
}

def send_telegram_message(message):
    """Send a message via Telegram bot to both personal and group chats"""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  Telegram bot token not configured")
        return False

    # Collect all chat IDs
    chat_ids = []
    if TELEGRAM_PERSONAL_CHAT_ID:
        chat_ids.append(('personal', TELEGRAM_PERSONAL_CHAT_ID))
    if TELEGRAM_GROUP_CHAT_ID:
        chat_ids.append(('group', TELEGRAM_GROUP_CHAT_ID))

    if not chat_ids:
        print("⚠️  No Telegram chat IDs configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    success_count = 0

    for chat_type, chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"✅ Telegram message sent successfully to {chat_type} chat")
                success_count += 1
            else:
                print(f"❌ Failed to send Telegram message to {chat_type} chat: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending Telegram message to {chat_type} chat: {e}")

    return success_count > 0

def login_with_playwright():
    """Login using Playwright to handle client-side encryption"""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
        import os.path

        print("🔐 Logging in with Playwright...")

        STORAGE_FILE = "browser_state.json"
        TOKEN_FILE = "access_token.txt"
        use_saved_session = os.path.exists(STORAGE_FILE)

        # Try to load saved access token
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                saved_token = f.read().strip()
                if saved_token:
                    access_token = saved_token
                    print(f"📦 Loaded saved access token from {TOKEN_FILE}")

        if use_saved_session:
            print(f"📦 Using saved session from {STORAGE_FILE}")

        with sync_playwright() as p:
            # Launch Firefox (better for avoiding detection than Chrome)
            browser = p.firefox.launch(
                headless=True,
                firefox_user_prefs={
                    "dom.webdriver.enabled": False,
                    "useAutomationExtension": False
                }
            )

            # Load saved session if available
            context_options = {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
                "viewport": {'width': 1920, 'height': 1080},
                "locale": 'en-US',
                "timezone_id": 'Europe/Rome',
                "permissions": ['geolocation'],
                "extra_http_headers": {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            }

            if use_saved_session:
                context_options["storage_state"] = STORAGE_FILE

            context = browser.new_context(**context_options)

            page = context.new_page()
            page.set_default_timeout(60000)

            # Stealth: Remove webdriver property
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # Intercept API responses to capture the access token
            access_token = None

            def handle_response(response):
                nonlocal access_token
                if "user/login" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        if data.get('accessToken'):
                            access_token = data['accessToken']
                            print("✅ Access token captured from API response")
                    except:
                        pass

            page.on("response", handle_response)

            if use_saved_session:
                # With saved session, visit dashboard to trigger authentication
                print("📄 Loading dashboard with saved session...")
                try:
                    # Go to dashboard - should work with valid session
                    page.goto("https://visa.vfsglobal.com/aze/en/ita/dashboard", wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(5000)

                    current_url = page.url

                    # Check if we got redirected to login (session expired)
                    if "login" in current_url:
                        print("⚠️  Session expired - please run setup_session.py again")
                        browser.close()
                        return None

                    print("✅ Session still valid - on dashboard")

                    # Try to extract token from all possible storage locations
                    if not access_token:
                        print("🔍 Searching for access token in browser storage...")
                        access_token = page.evaluate("""
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
                                    if (val) return val;
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

                                return null;
                            }
                        """)

                        if access_token:
                            print(f"✅ Token found in storage (length: {len(access_token)})")
                        else:
                            print("⚠️  Token not in storage, refreshing session...")
                            # Try refreshing by visiting login again
                            page.goto("https://visa.vfsglobal.com/aze/en/ita/login")
                            page.wait_for_timeout(5000)

                except Exception as e:
                    print(f"⚠️  Session check failed: {e}")

            else:
                # No saved session - try automated login (may fail due to bot protection)
                print("⚠️  No saved session found!")
                print("📝 Please run: python scripts/setup_session.py")
                print("   This is a ONE-TIME setup that takes 30 seconds.")
                browser.close()
                return None

            browser.close()

            if access_token:
                print("✅ Login successful - Access token obtained")
                return access_token
            else:
                print("❌ Failed to obtain access token")
                return None

    except ImportError:
        print("⚠️  Playwright not available")
        return None
    except Exception as e:
        print(f"❌ Playwright login error: {e}")
        return None

def check_slots(access_token):
    """Check for available visa appointment slots"""
    print("🔍 Checking for available slots...")

    headers = HEADERS.copy()
    headers["authorize"] = access_token

    payload = {
        "countryCode": "aze",
        "missionCode": "ita",
        "vacCode": "VACB",
        "visaCategoryCode": "SCS",
        "roleName": "Individual",
        "loginUser": USER_EMAIL,
        "payCode": ""
    }

    try:
        response = requests.post(SLOT_CHECK_URL, json=payload, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()

            # Check if slots are available
            if data.get('earliestDate') or data.get('earliestSlotLists'):
                return {
                    'available': True,
                    'earliest_date': data.get('earliestDate'),
                    'slots': data.get('earliestSlotLists', [])
                }
            else:
                error = data.get('error', {})
                if error.get('code') == 4008:
                    print("ℹ️  No slots available")
                    return {'available': False}
                else:
                    print(f"⚠️  Unexpected response: {data}")
                    return {'available': False}
        else:
            print(f"❌ API request failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error checking slots: {e}")
        return None

def main():
    """Main execution function"""
    print("=" * 60)
    print("🇮🇹 VFS Global Italy Visa Slot Checker")
    print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Validate all required environment variables
    required_vars = {
        'USER_EMAIL': USER_EMAIL,
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'TELEGRAM_PERSONAL_CHAT_ID': TELEGRAM_PERSONAL_CHAT_ID
    }

    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]

    if missing_vars:
        print(f"❌ Error: The following environment variables must be set: {', '.join(missing_vars)}")
        sys.exit(1)

    # Step 1: Login to get access token
    access_token = login_with_playwright()

    if not access_token:
        print("❌ Failed to login - cannot check slots")
        sys.exit(1)

    # Step 2: Check for available slots
    result = check_slots(access_token)

    if result is None:
        print("❌ Failed to check slots")
        sys.exit(1)

    # Step 3: Send notification if slots are available
    if result['available']:
        earliest_date = result.get('earliest_date', 'Unknown')
        slots_count = len(result.get('slots', []))

        message = f"""
🎉 <b>VISA SLOT AVAILABLE!</b> 🎉

📅 <b>Earliest Date:</b> {earliest_date}
🔢 <b>Available Slots:</b> {slots_count}
⏰ <b>Detected At:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 <b>Book Now:</b> https://visa.vfsglobal.com/aze/en/ita/

⚡ Act fast! Slots may fill up quickly.
        """.strip()

        print("\n🎉 SLOTS AVAILABLE!")
        print(f"📅 Earliest Date: {earliest_date}")
        print(f"🔢 Slots Count: {slots_count}")

        send_telegram_message(message)
    else:
        print("\n❌ No slots currently available")
        # Don't send Telegram message when no slots

    print("\n" + "=" * 60)
    print("✅ Check completed successfully")
    print("=" * 60)

if __name__ == "__main__":
    main()
