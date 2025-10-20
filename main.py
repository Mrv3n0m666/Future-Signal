import asyncio, os, json, time
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.telegram_utils import make_bot, send_message_async
from coin_manager import refresh_symbols_periodic
from gm_signal_bot import start_signal_monitor
from tracker import start_tracker

# Buat direktori data jika belum ada
os.makedirs("data", exist_ok=True)

# Muat variabel lingkungan
load_dotenv()

# Ambil variabel dari environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_heartbeat():
    """Mengirim pesan heartbeat tiap 1 jam agar kita tahu bot masih aktif."""
    bot = make_bot(TELEGRAM_TOKEN)
    while True:
        msg = f"🕒 Bot Heartbeat: Still running at {datetime.now(timezone.utc).isoformat()}"
        try:
            await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
            print(f"Sent heartbeat at {datetime.now(timezone.utc).isoformat()}")
        except Exception as e:
            print(f"⚠️ Failed to send heartbeat: {e}")
        await asyncio.sleep(3600)  # kirim tiap jam

async def test_signal():
    """Kirim sinyal uji saat startup."""
    bot = make_bot(TELEGRAM_TOKEN)
    msg = f"🚨 TEST SIGNAL — BOT IS ALIVE\nTime: {datetime.now(timezone.utc).isoformat()}"
    try:
        await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
        print("✅ Sent test signal to Telegram successfully")
    except Exception as e:
        print(f"❌ Failed to send test signal: {e}")

async def main():
    bot = make_bot(TELEGRAM_TOKEN)
    print(f"🚀 Mulai bot dengan CHAT_ID: {TELEGRAM_CHAT_ID}")
    
    # Kirim pesan awal ke Telegram
    await test_signal()

    # Jalankan semua task background
    asyncio.create_task(refresh_symbols_periodic())
    asyncio.create_task(start_tracker())
    asyncio.create_task(send_heartbeat())
    asyncio.create_task(start_signal_monitor())

    print("✅ Semua task background dimulai — bot sekarang aktif penuh.")

    # Loop utama agar container tidak mati
    while True:
        await asyncio.sleep(300)  # per 5 menit cek ulang bahwa loop masih hidup
        print(f"[{datetime.now(timezone.utc).isoformat()}] Bot main loop masih berjalan...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot dihentikan manual.")
