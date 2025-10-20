import asyncio, json, os, time
import pandas as pd
import websockets
from collections import deque, defaultdict
from datetime import datetime, timezone
from dotenv import load_dotenv

from utils.telegram_utils import make_bot, send_message_async
from utils.data_store import load_json, save_json
from utils.signal_engine_v2 import detect_signal, recommend_leverage

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FSTREAM = os.getenv("BINANCE_FAPI_URL", "wss://fstream.binance.com") + "/stream?streams="
TIMEFRAMES = [tf.strip() for tf in os.getenv("TIMEFRAMES", "1m,3m,5m").split(",")]
ALERT_COOLDOWN_SEC = int(os.getenv("COOLDOWN_SECONDS", "90"))
HISTORY_LEN = int(os.getenv("HISTORY_LEN", "300"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SIGNALS_ACTIVE = os.path.join(DATA_DIR, "signals_active.json")
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(SIGNALS_ACTIVE): save_json(SIGNALS_ACTIVE, {})

def save_active(d): json.dump(d, open(SIGNALS_ACTIVE, "w"), indent=2, default=str)
def load_active(): return json.load(open(SIGNALS_ACTIVE)) if os.path.exists(SIGNALS_ACTIVE) else {}

async def monitor_chunk(symbols):
    history = {s: {tf: {k: deque(maxlen=HISTORY_LEN) for k in ["open_time","open","high","low","close","volume"]} for tf in TIMEFRAMES} for s in symbols}
    bot = make_bot(TELEGRAM_TOKEN)
    last_alert = defaultdict(lambda: 0.0)
    ws_url = FSTREAM + "/".join(f"{s.lower()}@kline_{tf}" for s in symbols for tf in TIMEFRAMES)

    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                async for raw in ws:
                    data = json.loads(raw).get("data", {})
                    k = data.get("k", {})
                    if not k or not k.get("x", False): continue
                    sym, tf = k["s"], k["i"]
                    if sym not in history: continue
                    h = history[sym][tf]
                    for key in ["open_time","open","high","low","close","volume"]:
                        h[key].append(float(k[key[0]] if key != "open_time" else k["t"]))

                    df = pd.DataFrame(h)
                    if len(df) < 100: continue
                    sig = detect_signal(df)
                    if not sig: continue

                    key = f"{sym}|{tf}"
                    if time.time() - last_alert[key] < ALERT_COOLDOWN_SEC: continue
                    last_alert[key] = time.time()

                    atr, price = sig["atr"], sig["price"]
                    tp1 = price + (0.5 * atr if sig["side"]=="buy" else -0.5 * atr)
                    tp2 = price + (1.0 * atr if sig["side"]=="buy" else -1.0 * atr)
                    tp3 = price + (1.5 * atr if sig["side"]=="buy" else -1.5 * atr)
                    sl  = price - (0.8 * atr if sig["side"]=="buy" else -0.8 * atr)

                    leverage = recommend_leverage(sig["confidence"], sig["atr_pct"])
                    tstamp = datetime.now(timezone.utc).isoformat()

                    msg = (
                        "🚀 *VIP GOLDEN SIGNAL* 🚀\n\n"
                        f"💎 Pair: *{sym}*\n"
                        f"🕒 TF: *{tf}*\n"
                        f"📈 Side: *{sig['side'].upper()}*\n"
                        f"💰 Entry: `{price:.6f}`\n"
                        f"🎯 Targets:\n"
                        f"• TP1: `{tp1:.6f}`\n• TP2: `{tp2:.6f}`\n• TP3: `{tp3:.6f}`\n"
                        f"🛑 Stoploss: `{sl:.6f}`\n\n"
                        f"⚙️ Confidence: *{sig['confidence']}%*\n"
                        f"🔧 Leverage Suggestion: *{leverage}*\n\n"
                        f"📖 Reason: {sig['reason']}\n"
                        f"📆 Time: {tstamp}"
                    )

                    await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
                    print(f"Sent signal {sym} {tf} {sig['side']} conf {sig['confidence']} lev {leverage}")
        except Exception as e:
            print("WS error:", e)
            await asyncio.sleep(5)
