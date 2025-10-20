import asyncio, os, json, time
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.telegram_utils import make_bot, send_message_async
from coin_manager import refresh_symbols_periodic
from gm_signal_bot import start_signal_monitor
from tracker import start_tracker

os.makedirs("data", exist_ok=True)
load_dotenv()

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
    await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
    print("Sent test signal to Telegram")

async def main():
    bot = make_bot(TELEGRAM_TOKEN)
    await test_signal()  # Kirim test sinyal sekali saat start
    asyncio.create_task(refresh_symbols_periodic())
    asyncio.create_task(start_tracker())
    asyncio.create_task(send_heartbeat())  # Jalankan heartbeat
    await start_signal_monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping")