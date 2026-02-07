#!/usr/bin/env python3
"""
Local slot checker - Run manually when needed
Performs fresh login + slot check in one browser session
"""
import os
import sys
import time
import requests
import threading
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

USER_EMAIL = os.getenv('USER_EMAIL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_PERSONAL_CHAT_ID = os.getenv('TELEGRAM_PERSONAL_CHAT_ID')
TELEGRAM_GROUP_CHAT_ID = os.getenv('TELEGRAM_GROUP_CHAT_ID')

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

def main():
    """Main execution function"""
    print("=" * 60)
    print("🇮🇹 VFS Global Italy Visa Slot Checker (Local)")
    print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Validate required environment variables
    required_vars = {
        'USER_EMAIL': USER_EMAIL,
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'TELEGRAM_PERSONAL_CHAT_ID': TELEGRAM_PERSONAL_CHAT_ID
    }

    missing_vars = [var_name for var_name, var_value in required_vars.items() if not var_value]

    if missing_vars:
        print(f"❌ Error: The following environment variables must be set: {', '.join(missing_vars)}")
        sys.exit(1)

    print("🔐 Opening browser for manual login...")
    print("=" * 60)
    print("ℹ️  You will need to login manually each time")
    print("   (Sessions expire in 1-2 minutes on VFS)")
    print("=" * 60)

    with sync_playwright() as p:
        # Launch Firefox in VISIBLE mode for manual login
        browser = p.firefox.launch(
            headless=False,
            firefox_user_prefs={
                "dom.webdriver.enabled": False,
                "useAutomationExtension": False
            }
        )

        # Load saved session to bypass Cloudflare
        STORAGE_FILE = "browser_state.json"
        context_options = {
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
            "viewport": {'width': 1920, 'height': 1080}
        }

        if os.path.exists(STORAGE_FILE):
            context_options["storage_state"] = STORAGE_FILE
            print("📦 Using saved session cookies to bypass Cloudflare...")

        context = browser.new_context(**context_options)

        page = context.new_page()
        page.set_default_timeout(60000)

        # Remove webdriver property
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Set up token capture with threading event
        access_token = [None]
        token_event = threading.Event()

        def handle_response(response):
            if "user/login" in response.url and response.status == 200:
                try:
                    data = response.json()
                    if data.get('accessToken'):
                        access_token[0] = data['accessToken']
                        print(f"\n✅ Login successful! Token captured (length: {len(access_token[0])})")
                        token_event.set()  # Signal that token was captured
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

        # Wait for the token with timeout (2 minutes)
        if token_event.wait(timeout=120):
            print("✅ Token received, proceeding to check slots...")
        else:
            print("\n❌ Login timeout - no token received within 2 minutes")
            print("⚠️  Please make sure you logged in successfully")
            try:
                browser.close()
            except:
                pass
            sys.exit(1)

        if not access_token[0]:
            print("\n❌ Token capture failed")
            browser.close()
            sys.exit(1)

        # Now check slots using the browser context
        print("🔍 Checking for available slots...")

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
            # Check if browser/page is still alive
            if page.is_closed():
                print("⚠️  Browser was closed - cannot check slots within browser")
                print("   Using direct API call instead...")

                # Fall back to direct API call (may be blocked by Cloudflare)
                import requests
                headers = {
                    "accept": "application/json, text/plain, */*",
                    "content-type": "application/json;charset=UTF-8",
                    "authorize": access_token[0],
                    "route": "aze/en/ita",
                    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
                }
                response = requests.post(
                    'https://lift-api.vfsglobal.com/appointment/CheckIsSlotAvailable',
                    json=payload,
                    headers=headers,
                    timeout=15
                )
                result = {
                    'status': response.status_code,
                    'data': response.json() if response.status_code == 200 else {}
                }
            else:
                # Make API call from within browser context
                result = page.evaluate("""
                    async (args) => {
                        const response = await fetch('https://lift-api.vfsglobal.com/appointment/CheckIsSlotAvailable', {
                            method: 'POST',
                            headers: {
                                'accept': 'application/json, text/plain, */*',
                                'content-type': 'application/json;charset=UTF-8',
                                'authorize': args.token,
                                'route': 'aze/en/ita'
                            },
                            body: JSON.stringify(args.payload)
                        });

                        const data = await response.json();
                        return {
                            status: response.status,
                            data: data
                        };
                    }
                """, {"token": access_token[0], "payload": payload})

                browser.close()

            if result['status'] == 200:
                data = result['data']

                # Check if slots are available
                if data.get('earliestDate') or data.get('earliestSlotLists'):
                    earliest_date = data.get('earliestDate', 'Unknown')
                    slots_count = len(data.get('earliestSlotLists', []))

                    message = f"""
🎉 <b>VISA SLOT AVAILABLE!</b> 🎉

📅 <b>Earliest Date:</b> {earliest_date}
🔢 <b>Available Slots:</b> {slots_count}
⏰ <b>Detected At:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 <b>Book Now:</b> https://visa.vfsglobal.com/aze/en/ita/

⚡ Act fast! Slots may fill up quickly.
                    """.strip()

                    print("\n" + "=" * 60)
                    print("🎉 SLOTS AVAILABLE!")
                    print(f"📅 Earliest Date: {earliest_date}")
                    print(f"🔢 Slots Count: {slots_count}")
                    print("=" * 60)

                    send_telegram_message(message)
                else:
                    error = data.get('error', {})
                    if error.get('code') == 4008:
                        print("\n❌ No slots currently available")
                    else:
                        print(f"\n⚠️  Unexpected response: {data}")
            else:
                print(f"❌ API request failed: {result['status']}")
                print(f"   Response: {result.get('data', {})}")

        except Exception as e:
            print(f"❌ Error checking slots: {e}")
            browser.close()
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Check completed successfully")
    print("=" * 60)

if __name__ == "__main__":
    main()
