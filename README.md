# VFS Global Italy Visa Slot Checker

Automated visa appointment slot checker for VFS Global Italy visa applications from Azerbaijan. This tool runs every hour via GitHub Actions and sends Telegram notifications when slots become available.

## Features

- Automated hourly slot checking via GitHub Actions
- Telegram notifications to both personal and group chats when slots are available
- Browser automation for secure login handling
- No notifications when slots are unavailable (quiet mode)
- Manual trigger support for immediate checks
- Support for multiple notification targets (personal + group)

## Setup Instructions

### 1. Get Your Telegram Bot Token and Chat IDs

#### Create a Telegram Bot:
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the **Bot Token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Get Your Personal Chat ID:
1. Send a message to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789}` - this is your **Personal Chat ID**
4. Personal chat IDs are positive numbers (e.g., `6192509415`)

#### Get Your Group Chat ID (Optional):
1. Add your bot to a Telegram group
2. Send a message in the group (mention the bot or just any message)
3. Visit the same URL: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-1001234567890}` - this is your **Group Chat ID**
5. Group chat IDs are negative numbers (e.g., `-1001234567890`)

### 2. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

| Secret Name | Description | Example | Required |
|-------------|-------------|---------|----------|
| `USER_EMAIL` | Your VFS Global account email | `your.email@gmail.com` | Yes |
| `USER_PASSWORD` | Your VFS Global account password | `YourPassword123` | Yes |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | `8343433594:AAF-wdSNA...` | Yes |
| `TELEGRAM_PERSONAL_CHAT_ID` | Your personal Telegram chat ID | `6192509415` | Yes |
| `TELEGRAM_GROUP_CHAT_ID` | Your group Telegram chat ID | `-1001234567890` | No (Optional) |

### 3. Enable GitHub Actions

1. Go to your repository → Actions tab
2. If workflows are disabled, click "I understand my workflows, go ahead and enable them"
3. The workflow will now run automatically every hour

### 4. Manual Trigger (Optional)

To check immediately without waiting for the scheduled run:

1. Go to Actions tab
2. Select "Check Visa Slots" workflow
3. Click "Run workflow" button
4. Click the green "Run workflow" button

## Local Testing

To test the script locally:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Create .env file with your credentials
cat > .env << EOF
USER_EMAIL=your.email@gmail.com
USER_PASSWORD=YourPassword123
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_PERSONAL_CHAT_ID=6192509415
TELEGRAM_GROUP_CHAT_ID=-1001234567890
EOF

# Run the script
python scripts/check_slots.py
```

## How It Works

1. **Authentication**: Uses Playwright browser automation to login to VFS Global, handling client-side encryption
2. **Slot Checking**: Calls the VFS Global API to check for available appointment slots
3. **Notification**: Sends a Telegram message only when slots are detected

### API Endpoints Used

- **Login**: `POST https://lift-api.vfsglobal.com/user/login`
- **Check Slots**: `POST https://lift-api.vfsglobal.com/appointment/CheckIsSlotAvailable`

### Slot Check Parameters

```json
{
  "countryCode": "AZE",
  "missionCode": "ita",
  "vacCode": "VACB",
  "visaCategoryCode": "SCS",
  "roleName": "Individual",
  "loginUser": "your.email@gmail.com",
  "payCode": ""
}
```

## Notification Format

When a slot is detected, you'll receive a Telegram message like:

```
🎉 VISA SLOT AVAILABLE! 🎉

📅 Earliest Date: 2026-03-15
🔢 Available Slots: 3
⏰ Detected At: 2026-02-07 14:30:00

🔗 Book Now: https://visa.vfsglobal.com/aze/en/ita/

⚡ Act fast! Slots may fill up quickly.
```

## Schedule

The GitHub Action runs:
- **Automatically**: Every hour at minute 0 (00:00, 01:00, 02:00, etc.)
- **Manually**: Via workflow_dispatch (Run workflow button)

To change the schedule, edit `.github/workflows/check_slots.yml`:

```yaml
schedule:
  - cron: '0 * * * *'  # Every hour
  # - cron: '*/30 * * * *'  # Every 30 minutes
  # - cron: '0 */2 * * *'  # Every 2 hours
```

Note: GitHub Actions cron jobs may experience delays of up to 15 minutes during high load.

## Troubleshooting

### No Telegram messages received

1. Verify your `TELEGRAM_PERSONAL_CHAT_ID` and/or `TELEGRAM_GROUP_CHAT_ID` are correct
2. Make sure you sent at least one message to your bot first (or added it to the group)
3. For group chats, ensure the bot has permission to send messages in the group
4. Check GitHub Actions logs for errors
5. Test locally first to verify the configuration works

### GitHub Action fails

1. Check the Actions tab for detailed error logs
2. Verify all secrets are configured correctly
3. Ensure no typos in secret names

### Login issues

1. Verify your VFS Global credentials are correct
2. Check if your account is active
3. Try logging in manually on the website first

### Playwright installation issues

The workflow automatically installs Playwright and its dependencies. If you encounter issues locally:

```bash
playwright install chromium
playwright install-deps chromium
```

## File Structure

```
.
├── .env                          # Local environment variables (not committed)
├── .github/
│   └── workflows/
│       └── check_slots.yml       # GitHub Actions workflow
├── scripts/
│   └── check_slots.py           # Main slot checker script
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Security Notes

- Never commit `.env` file or expose your credentials
- GitHub Secrets are encrypted and secure
- The script only reads data - it doesn't perform any bookings
- Browser automation runs in headless mode

## API Response Examples

### When slots are available:
```json
{
  "earliestDate": "2026-03-15",
  "earliestSlotLists": [
    {
      "date": "2026-03-15",
      "slots": ["09:00", "10:00", "11:00"]
    }
  ],
  "error": null
}
```

### When no slots available:
```json
{
  "earliestDate": null,
  "earliestSlotLists": [],
  "error": {
    "code": 4008,
    "description": "We are sorry, but no appointment slots are currently available. Please try again later.",
    "type": "Information"
  }
}
```

## Contributing

Feel free to open issues or submit pull requests for improvements.

## License

MIT License - feel free to use and modify as needed.

## Disclaimer

This tool is for personal use only. Use responsibly and in accordance with VFS Global's terms of service. The authors are not responsible for any misuse or consequences resulting from using this tool.
