import asyncio
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

from gm_signal_bot import monitor_chunk
from coin_manager import refresh_symbols_periodic
from utils.telegram_utils import make_bot, send_message_async

# =============== LOAD ENV ===============
load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SYMBOL_FILE = os.path.join(DATA_DIR, "symbols.json")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# =============== AMBIL DAFTAR SYMBOL ===============
def get_symbols_list():
    """Ambil list symbol dari file symbols.json, fallback ke default"""
    if os.path.exists(SYMBOL_FILE):
        try:
            with open(SYMBOL_FILE) as f:
                data = json.load(f)
                if "symbols" in data:
                    return data["symbols"]
        except Exception as e:
            print(f"⚠️ Gagal baca {SYMBOL_FILE}: {e}")

    # fallback kalau tidak ada file
    print("⚠️ File symbols.json tidak ditemukan, pakai default list.")
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "DOGEUSDT"]


# =============== MAIN LOOP ===============
async def main():
    print("🚀 Starting Future-Signal Golden Moment v2")
    print(f"🕒 {datetime.now(timezone.utc).isoformat()} UTC")

    # 🔔 Kirim test message ke Telegram untuk konfirmasi bot aktif
    try:
        bot = make_bot(TELEGRAM_TOKEN)
        msg = (
            "✅ *Future-Signal Golden Moment v2 aktif!*\n\n"
            "Bot berhasil dijalankan di server Railway 🚀\n"
            "Sekarang sistem sedang memantau pair dan menunggu sinyal momentum ⚡"
        )
        await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
        print("✅ Sent startup test message to Telegram successfully.")
    except Exception as e:
        print(f"⚠️ Failed to send startup message: {e}")

    # Jalankan background refresh symbol task
    try:
        asyncio.create_task(refresh_symbols_periodic())
    except TypeError:
        print("⚠️ Fungsi refresh_symbols_periodic bukan async, ubah ke async def di coin_manager.py")
        return

    # Ambil daftar simbol
    symbols = get_symbols_list()
    print(f"🧠 Monitoring {len(symbols)} symbols...")

    # Jalankan deteksi signal utama
    await monitor_chunk(symbols)


# =============== ENTRY POINT ===============
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot dihentikan manual oleh pengguna.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
