import asyncio
import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_BASE64")
GOOGLE_CREDS_BASE64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_TAB_NAME = os.getenv("SHEET_TAB_NAME", "Research")

source_configs = {}

def clean_source_name(name):
    name = str(name).strip()
    if not name: return ""
    if "t.me/" in name:
        name = name.split("t.me/")[-1].replace("/", "")
    if not name.startswith('@') and not name.replace('-', '').isdigit():
        name = f"@{name}"
    return name

def get_config_from_sheet():
    try:
        creds_info = json.loads(base64.b64decode(GOOGLE_CREDS_BASE64).decode("utf-8"))
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client_gs = gspread.authorize(creds)
        sheet_full = client_gs.open_by_key(SHEET_ID)
        sheet = sheet_full.worksheet(SHEET_TAB_NAME)
        records = sheet.get_all_records(expected_headers=['Source Channel', 'Target Group ID', 'Topic ID', 'Status'])
        
        new_config = {}
        for row in records:
            source = clean_source_name(row.get("Source Channel", ""))
            target = str(row.get("Target Group ID", "")).strip()
            topic_id = str(row.get("Topic ID", "")).strip()
            status = str(row.get("Status", "")).strip().lower()
            
            if status == "aktif" and source and target:
                target_final = int(target) if target.replace('-', '').isdigit() else target
                if source not in new_config:
                    new_config[source] = []
                new_config[source].append({
                    "target": target_final,
                    "topic": int(topic_id) if topic_id.isdigit() else None
                })
        return new_config
    except Exception as e:
        print(f"✖ [ERROR] Gagal baca Sheet: {e}", flush=True)
        return {}

async def main():
    global source_configs
    try:
        decoded_session = base64.b64decode(SESSION_STR).decode('utf-8')
    except:
        return

    client = TelegramClient(StringSession(decoded_session), API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"✅ [DEBUG] Terhubung sebagai {me.first_name}", flush=True)

    async def update_sources():
        global source_configs
        while True:
            source_configs = get_config_from_sheet()
            print(f"📊 [DEBUG] Memantau {len(source_configs)} sumber aktif.", flush=True)
            await asyncio.sleep(600)

    asyncio.create_task(update_sources())

    @client.on(events.NewMessage())
    async def handler(event):
        chat = await event.get_chat()
        chat_id = str(event.chat_id)
        username = f"@{chat.username}" if getattr(chat, 'username', None) else None
        
        targets = None
        for key in [username, chat_id]:
            if key and key in source_configs:
                targets = source_configs[key]
                print(f"📩 [MATCH] Pesan dari {key} -> Forwarding...", flush=True)
                break
        
        if targets:
            for t_config in targets:
                try:
                    # CARA PALING STABIL: Menggunakan Invoke untuk Forward Murni ke Topic
                    # Ini akan menjamin Tag 'Forwarded From' muncul dan Caption 100% utuh
                    input_peer = await client.get_input_entity(t_config['target'])
                    
                    forward_standar = functions.messages.ForwardMessagesRequest(
                        from_peer=await event.get_input_chat(),
                        id=[event.id],
                        to_peer=input_peer,
                        top_msg_id=t_config['topic'] if t_config['topic'] else None
                    )
                    
                    await client(forward_standar)
                    print(f"✅ [SUCCESS] Forward murni berhasil ke Topic {t_config['topic']}", flush=True)
                except Exception as e:
                    print(f"✖ [ERROR] Gagal: {e}", flush=True)

    print("🟢 Bot Running... Menunggu pesan masuk.", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
