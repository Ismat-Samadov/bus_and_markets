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
        from playwright.sync_api import sync_playwright

        print("🔐 Logging in with Playwright...")

        with sync_playwright() as p:
            # Use chromium browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            # Intercept API responses to capture the access token
            access_token = None

            def handle_response(response):
                nonlocal access_token
                if "user/login" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        if data.get('accessToken'):
                            access_token = data['accessToken']
                    except:
                        pass

            page.on("response", handle_response)

            # Navigate to VFS Global visa page
            page.goto("https://visa.vfsglobal.com/aze/en/ita/login")
            page.wait_for_load_state("networkidle")

            # Fill in login credentials
            page.fill('input[type="email"]', USER_EMAIL)
            page.fill('input[type="password"]', USER_PASSWORD)

            # Click login button
            page.click('button[type="submit"]')

            # Wait for login to complete
            page.wait_for_timeout(5000)

            browser.close()

            if access_token:
                print("✅ Login successful - Access token obtained")
                return access_token
            else:
                print("❌ Failed to obtain access token")
                return None

    except ImportError:
        print("⚠️  Playwright not available, trying direct API login...")
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
        'USER_PASSWORD': USER_PASSWORD,
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
