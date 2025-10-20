import time, json, os, requests
from datetime import datetime, timezone, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
KNOWN = os.path.join(DATA_DIR, "known_symbols.json")
SYMBOLS = os.path.join(DATA_DIR, "symbols.json")
FAPI = os.getenv("BINANCE_REST_URL", "https://fapi.binance.com")

def load_known():
    if os.path.exists(KNOWN):
        return json.load(open(KNOWN))
    return {}

def save_known(d):
    json.dump(d, open(KNOWN, "w"), indent=2)

def save_symbols(lst):
    json.dump({"symbols": lst, "updated_at": datetime.now(timezone.utc).isoformat()}, open(SYMBOLS, "w"), indent=2)

def get_all_futures_symbols():
    try:
        r = requests.get(FAPI + "/fapi/v1/exchangeInfo", timeout=10)
        r.raise_for_status()
        data = r.json()
        syms = [s['symbol'] for s in data.get('symbols', []) if s.get('status') == 'TRADING' and s.get('symbol', '').endswith('USDT')]
        return syms
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch futures symbols: {e}")
        return ["BTCUSDT"]  # Fallback ke BTCUSDT kalau gagal

def get_top_volume(limit=20):
    try:
        r = requests.get(FAPI + "/fapi/v1/ticker/24hr", timeout=10)
        r.raise_for_status()
        data = r.json()
        usdt = [d for d in data if d.get('symbol', '').endswith('USDT')]
        usdt_sorted = sorted(usdt, key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        return [d['symbol'] for d in usdt_sorted[:limit]]
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch top volume: {e}")
        return ["BTCUSDT"]  # Fallback

def refresh_symbols_periodic(top_limit=20, window_days=7, interval=3600):
    while True:
        try:
            now = datetime.now(timezone.utc)
            all_syms = get_all_futures_symbols()
            known = load_known()
            for s in all_syms:
                if s not in known:
                    known[s] = now.isoformat()
            save_known(known)
            cutoff = now - timedelta(days=window_days)
            new_listing = [s for s, iso in known.items() if datetime.fromisoformat(iso) >= cutoff]
            top = get_top_volume(top_limit)
            combined = list(dict.fromkeys(top + new_listing))
            save_symbols(combined)
            print("Refreshed symbols:", len(combined))
        except Exception as e:
            print("coin_manager error", e)
        time.sleep(interval)