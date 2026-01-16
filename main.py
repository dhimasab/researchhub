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

# Konfigurasi Utama
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION_BASE64")
GOOGLE_CREDS_BASE64 = os.getenv("GOOGLE_CREDENTIALS_BASE64")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEET_TAB_NAME = os.getenv("SHEET_TAB_NAME", "Research")

# Global variable untuk menyimpan rute forward
source_configs = {}

def get_config_from_sheet():
    """Mengambil data rute forward dari Google Sheet tab spesifik"""
    try:
        print(f"🔍 [DEBUG] Mencoba mengakses Google Sheet ID: {SHEET_ID}...", flush=True)
        
        # Decode Credentials
        creds_info = json.loads(base64.b64decode(GOOGLE_CREDS_BASE64).decode("utf-8"))
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client_gs = gspread.authorize(creds)
        
        # Buka Sheet dan Tab
        sheet_full = client_gs.open_by_key(SHEET_ID)
        sheet = sheet_full.worksheet(SHEET_TAB_NAME)
        records = sheet.get_all_records()
        
        print(f"📊 [DEBUG] Berhasil membaca {len(records)} baris dari tab '{SHEET_TAB_NAME}'", flush=True)
        
        new_config = {}
        active_count = 0
        
        for index, row in enumerate(records, start=2): # start=2 karena baris 1 adalah header
            source = str(row.get("Source Channel", "")).strip()
            target = str(row.get("Target Group ID", "")).strip()
            topic_id = str(row.get("Topic ID", "")).strip()
            status = str(row.get("Status", "")).strip().lower()
            
            if status == "aktif":
                if source and target:
                    active_count += 1
                    # Bersihkan format target
                    target_final = int(target) if target.replace('-', '').isdigit() else target
                    
                    if source not in new_config:
                        new_config[source] = []
                    
                    new_config[source].append({
                        "target": target_final,
                        "topic": int(topic_id) if topic_id.isdigit() else None
                    })
                    print(f"✅ [DEBUG] Baris {index}: Source {source} AKTIF -> Target {target} (Topic {topic_id})", flush=True)
                else:
                    print(f"⚠️ [DEBUG] Baris {index}: Status Aktif tapi Source/Target kosong!", flush=True)
            
        print(f"🚀 [DEBUG] Total sumber aktif yang akan dipantau: {active_count}", flush=True)
        return new_config
    except Exception as e:
        print(f"✖ [ERROR] Gagal baca Sheet: {e}", flush=True)
        return {}

async def main():
    global source_configs
    
    if not SESSION_STR:
        print("✖ [ERROR] TELEGRAM_SESSION_BASE64 tidak ditemukan di .env!", flush=True)
        return

    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    
    print("📡 [DEBUG] Menghubungkan ke Telegram...", flush=True)
    await client.start()
    
    me = await client.get_me()
    print(f"👤 [DEBUG] Login berhasil sebagai: {me.first_name} (@{me.username})", flush=True)

    async def update_sources():
        """Background Task: Cek Sheet tiap 10 menit & Auto Join"""
        global source_configs
        while True:
            print("\n🔄 [DEBUG] Memulai sinkronisasi rutin dengan Google Sheet...", flush=True)
            source_configs = get_config_from_sheet()
            
            if not source_configs:
                print("⚠️ [DEBUG] Tidak ada konfigurasi aktif. Pastikan kolom 'Status' diisi 'Aktif'.", flush=True)
            
            for source in source_configs.keys():
                try:
                    if isinstance(source, str) and (source.startswith('@') or 't.me' in source):
                        print(f"🔗 [DEBUG] Mencoba join ke: {source}", flush=True)
                        await client(functions.channels.JoinChannelRequest(channel=source))
                except Exception as e:
                    # Seringkali error karena sudah join, jadi kita diamkan saja
                    pass 
            
            print("⏳ [DEBUG] Sinkronisasi selesai. Menunggu 10 menit untuk refresh berikutnya...\n", flush=True)
            await asyncio.sleep(600) 

    # Jalankan background task
    asyncio.create_task(update_sources())

    @client.on(events.NewMessage())
    async def handler(event):
        chat = await event.get_chat()
        
        # Identifikasi sumber pesan untuk debug
        username = f"@{chat.username}" if getattr(chat, 'username', None) else None
        chat_id = str(event.chat_id)
        chat_title = getattr(chat, 'title', 'Private Chat')
        
        # Cari target di config
        targets = None
        # Cek berdasarkan link lengkap, username, atau ID
        chat_link = f"https://t.me/{chat.username}" if username else None
        
        for key in [username, chat_id, chat_link, f"https://t.me/{chat.username}"]:
            if key and key in source_configs:
                targets = source_configs[key]
                break
            
        if targets:
            print(f"📩 [NEW] Pesan masuk dari: {chat_title} ({username or chat_id})", flush=True)
            for t_config in targets:
                try:
                    await client.forward_messages(
                        t_config['target'],
                        event.message,
                        top_msg_id=t_config['topic']
                    )
                    print(f"📤 [SUCCESS] Forwarded ke {t_config['target']} | Topic: {t_config['topic']}", flush=True)
                except Exception as e:
                    print(f"✖ [ERROR] Gagal forward: {e}", flush=True)

    print("🟢 Bot sedang berjalan. Menunggu pesan masuk...", flush=True)
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())