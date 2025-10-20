import time
import json
import os
import requests
from datetime import datetime, timezone, timedelta

# ==========================
# KONFIGURASI DASAR
# ==========================
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

KNOWN = os.path.join(DATA_DIR, "known_symbols.json")
SYMBOLS = os.path.join(DATA_DIR, "symbols.json")
FAPI = os.getenv("BINANCE_REST_URL", "https://fapi.binance.com")

# Koin yang selalu dipantau (whitelist manual)
WHITELIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "TONUSDT", "LINKUSDT", "AVAXUSDT",
    # tambahkan koin baru di sini jika perlu
]

# ==========================
# FUNGSI UTILITAS
# ==========================
def load_known():
    if os.path.exists(KNOWN):
        return json.load(open(KNOWN))
    return {}

def save_known(data):
    json.dump(data, open(KNOWN, "w"), indent=2)

def save_symbols(symbols):
    json.dump(
        {"symbols": symbols, "updated_at": datetime.now(timezone.utc).isoformat()},
        open(SYMBOLS, "w"),
        indent=2,
    )

# ==========================
# FETCH DATA DARI BINANCE
# ==========================
def get_all_futures_symbols():
    """Ambil semua simbol futures aktif di Binance"""
    try:
        r = requests.get(f"{FAPI}/fapi/v1/exchangeInfo", timeout=10)
        r.raise_for_status()
        data = r.json()
        syms = [
            s["symbol"]
            for s in data.get("symbols", [])
            if s.get("status") == "TRADING" and s["symbol"].endswith("USDT")
        ]
        return syms
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Gagal ambil semua simbol futures: {e}")
        return ["BTCUSDT"]  # fallback aman

def get_top_volume(limit=40):
    """Ambil simbol berdasarkan volume 24 jam tertinggi"""
    try:
        r = requests.get(f"{FAPI}/fapi/v1/ticker/24hr", timeout=10)
        r.raise_for_status()
        data = r.json()
        usdt = [d for d in data if d.get("symbol", "").endswith("USDT")]
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
        return [d["symbol"] for d in usdt_sorted[:limit]]
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Gagal ambil data top volume: {e}")
        return ["BTCUSDT"]

# ==========================
# REFRESH SYMBOLS PERIODIK
# ==========================
def refresh_symbols_periodic(top_limit=40, window_days=7, interval=3600):
    """Perbarui daftar simbol aktif setiap jam"""
    while True:
        try:
            now = datetime.now(timezone.utc)

            # Ambil semua futures aktif
            all_syms = get_all_futures_symbols()

            # Muat daftar simbol yang sudah dikenal
            known = load_known()

            # Tambahkan simbol baru (new listing)
            for s in all_syms:
                if s not in known:
                    known[s] = now.isoformat()
            save_known(known)

            # Hitung cutoff untuk new listing
            cutoff = now - timedelta(days=window_days)
            new_listing = [
                s for s, iso in known.items() if datetime.fromisoformat(iso) >= cutoff
            ]

            # Ambil top volume
            top = get_top_volume(top_limit)

            # Gabungkan semua simbol unik (prioritaskan whitelist & aktif)
            combined = list(dict.fromkeys(WHITELIST + new_listing + top))

            # Batasi maksimum (default 60)
            combined = combined[:60]
            save_symbols(combined)

            print(f"✅ Refreshed {len(combined)} symbols at {now.isoformat()}")
            print(f"Top volume: {len(top)} | New listing: {len(new_listing)} | Whitelist: {len(WHITELIST)}")

        except Exception as e:
            print(f"❌ coin_manager error: {e}")

        time.sleep(interval)
