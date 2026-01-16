import asyncio
import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from telethon import TelegramClient, events, functions
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
            source = str(row.get("Source Channel", "")).strip()
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
        print("✖ [ERROR] Gagal decode Session Base64", flush=True)
        return

    # Inisialisasi Akun User
    client = TelegramClient(StringSession(decoded_session), API_ID, API_HASH)
    
    print("📡 [DEBUG] Mencoba login ke Akun Telegram...", flush=True)
    await client.start()
    me = await client.get_me()
    print(f"✅ [DEBUG] Berhasil login sebagai User: {me.first_name} (@{me.username or 'NoUsername'})", flush=True)

    async def update_sources():
        global source_configs
        while True:
            print("\n🔄 [DEBUG] Menyinkronkan daftar channel dari Google Sheet...", flush=True)
            source_configs = get_config_from_sheet()
            print(f"📊 [DEBUG] Memantau {len(source_configs)} sumber aktif.", flush=True)
            
            # Debug log untuk memastikan apa yang dipantau
            for s in source_configs.keys():
                print(f"   🔎 Memantau source: {s}", flush=True)
                
            await asyncio.sleep(600) # Cek sheet tiap 10 menit

    asyncio.create_task(update_sources())

    # Listener untuk mendeteksi pesan baru
    @client.on(events.NewMessage())
    async def handler(event):
        chat = await event.get_chat()
        chat_id = str(event.chat_id)
        chat_title = getattr(chat, 'title', 'Chat Pribadi')
        username = f"@{chat.username}" if getattr(chat, 'username', None) else None
        
        # LOG INI PENTING: Untuk membuktikan akun Anda "mendengar" pesan
        print(f"\n📩 [LOG] Ada pesan masuk di: {chat_title} (ID: {chat_id} | Username: {username})", flush=True)
        
        # Cari kecocokan rute
        chat_link = f"https://t.me/{chat.username}" if username else ""
        
        targets = None
        # Coba cocokkan dengan Username, ID, atau Link yang ada di Sheet
        for key in [username, chat_id, chat_link]:
            if key and key in source_configs:
                targets = source_configs[key]
                print(f"   🎯 [MATCH] Rute ditemukan untuk {key}!", flush=True)
                break
        
        if targets:
            for t_config in targets:
                try:
                    print(f"   📤 [SENDING] Meneruskan ke Target ID: {t_config['target']}...", flush=True)
                    # Menggunakan forward_messages (Akun User punya limitasi, tapi forward biasanya aman)
                    await client.forward_messages(
                        t_config['target'],
                        event.message,
                        top_msg_id=t_config['topic']
                    )
                    print(f"   ✅ [SUCCESS] Berhasil diteruskan!", flush=True)
                except Exception as e:
                    print(f"   ✖ [ERROR] Gagal meneruskan: {e}", flush=True)
        else:
            # Jika pesan masuk tapi tidak ada di list
            print(f"   ℹ [SKIP] Pesan diabaikan karena source tidak terdaftar atau nonaktif di Sheet.", flush=True)

    print("🟢 Akun aktif dan sedang memantau pesan... Silakan kirim pesan tes di channel sumber.", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
