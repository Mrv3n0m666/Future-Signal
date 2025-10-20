import asyncio
import os
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

from gm_signal_bot import monitor_chunk
from coin_manager import refresh_symbols_periodic

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

    # Refresh daftar simbol secara berkala di background
    asyncio.create_task(refresh_symbols_periodic())

    # Ambil daftar simbol
    symbols = get_symbols_list()
    print(f"🧠 Monitoring {len(symbols)} symbols...")

    # Jalankan deteksi signal
    await monitor_chunk(symbols)


# =============== ENTRY POINT ===============
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot dihentikan manual oleh pengguna.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
