# Telegram Auto Forward Bot (Google Sheets–Driven)

A **Telethon-based Telegram bot** that automatically monitors source channels or groups and performs **native message forwarding** to target groups or supergroups (including **Forum Topics**) using a **dynamic Google Sheets configuration**.

This bot is designed for **crypto research, news monitoring, and controlled content distribution** across multiple Telegram communities in a scalable and maintainable way.

---

## Key Features

- **Native Telegram forwarding** ("Forwarded From" label is preserved)
- Full support for **Forum Topics (top_msg_id)**
- **Real-time configuration** via Google Sheets
- Multi-source to multi-target routing
- Automatic config refresh every 10 minutes
- Secure authentication using **Google Service Account**
- Telegram session stored in **Base64 format**

---

## High-Level Workflow

1. Bot authenticates using a **Telegram String Session**
2. Configuration is loaded from Google Sheets
3. Incoming messages are matched against active sources
4. Messages are forwarded **natively** to configured targets/topics
5. Configuration updates apply automatically without restarting the bot

---

## Google Sheets Structure

Default sheet tab name: `Research`

| Source Channel | Target Group ID | Topic ID | Status |
|---------------|----------------|----------|--------|
| @channelA     | -1001234567890 | 45       | Aktif  |
| @channelB     | -1009876543210 |          | Aktif  |

### Column Description

- **Source Channel**  
  Channel username (`@xxx`), `t.me/xxx` link, or numeric chat ID

- **Target Group ID**  
  Telegram Supergroup ID (usually starts with `-100`)

- **Topic ID**  
  Optional. Required only when forwarding to a forum topic

- **Status**  
  Use `Aktif` to enable forwarding

---

## Environment Variables

Create a `.env` file with the following values:

```env
API_ID=123456
API_HASH=your_api_hash_here
TELEGRAM_SESSION_BASE64=base64_encoded_string_session

GOOGLE_CREDENTIALS_BASE64=base64_encoded_service_account_json
GOOGLE_SHEET_ID=your_google_sheet_id
SHEET_TAB_NAME=Research
```

### Notes

- `TELEGRAM_SESSION_BASE64` must contain a **Telethon StringSession** encoded in Base64
- `GOOGLE_CREDENTIALS_BASE64` must contain a **Google Service Account JSON** encoded in Base64

---

## Dependencies

Install all required dependencies:

```bash
pip install telethon gspread google-auth python-dotenv
```

---

## Running the Bot

```bash
python bot.py
```

If successful, the bot will log the connection status and the number of active sources being monitored.

---

## Forwarding Implementation Details

The bot uses the following Telethon method:

- `functions.messages.ForwardMessagesRequest`

Advantages of this approach:

- Original caption is fully preserved
- "Forwarded From" metadata remains intact
- Most stable method for forwarding into forum topics

---

## Common Use Cases

- Crypto news aggregation
- Research channel monitoring
- Alpha / signal distribution
- Internal DAO or team communication
- Media and intelligence monitoring

---

## Security Notes

- Never commit the `.env` file
- Do not expose Base64-encoded credentials
- Strongly recommended to use a dedicated Telegram account for the bot

---

## License

Private / Internal Use
Modify and extend according to operational needs.

