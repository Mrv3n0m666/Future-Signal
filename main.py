
import asyncio, os, json, time
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.telegram_utils import make_bot, send_message_async
from coin_manager import refresh_symbols_periodic
from gm_signal_bot import start_signal_monitor
from tracker import start_tracker
import os
os.makedirs("data", exist_ok=True)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def main():
    bot = make_bot(TELEGRAM_TOKEN)
    # start coin manager refresher
    asyncio.create_task(refresh_symbols_periodic())
    # start tracker
    asyncio.create_task(start_tracker())
    # start signal monitor (will spawn websocket workers)
    await start_signal_monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopping")
