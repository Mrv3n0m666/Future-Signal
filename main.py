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
    bot = make_bot(TELEGRAM_TOKEN)
    while True:
        msg = f"🕒 Bot Heartbeat: Still running at {datetime.now(timezone.utc).isoformat()}"
        await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
        print(f"Sent heartbeat at {datetime.now(timezone.utc).isoformat()}")
        await asyncio.sleep(3600)  # Kirim tiap jam

async def test_signal():
    bot = make_bot(TELEGRAM_TOKEN)
    msg = f"🚨 TEST SIGNAL — BOT IS ALIVE\nTime: {datetime.now(timezone.utc).isoformat()}"
    try:
        await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
        print("Sent test signal to Telegram successfully")
    except Exception as e:
        print(f"Failed to send test signal: {e}")

async def main():
    bot = make_bot(TELEGRAM_TOKEN)
    print(f"Mulai bot dengan CHAT_ID: {TELEGRAM_CHAT_ID}")
    await test_signal()
    print("Selesai test signal")
    asyncio.create_task(refresh_symbols_periodic())
    asyncio.create_task(start_tracker())
    asyncio.create_task(send_heartbeat())
    print("Memulai signal monitor")
    await start_signal_monitor()
    print("Signal monitor selesai")
    # Tes manual
    try:
        await send_message_async(bot, TELEGRAM_CHAT_ID, "Tes Manual dari Railway pada " + datetime.now(timezone.utc).isoformat())
        print("Terkirim tes manual ke Telegram successfully")
    except Exception as e:
        print(f"Failed to send manual test: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping")