# gm_signal_bot.py  (replace existing file)
import asyncio, json, os, time
from collections import deque, defaultdict
import pandas as pd
import websockets
from datetime import datetime, timezone
from dotenv import load_dotenv

from utils.telegram_utils import make_bot, send_message_async, send_photo_async
from utils.data_store import load_json, save_json
from utils.signal_engine_v2 import detect_signal

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FSTREAM = os.getenv("BINANCE_FAPI_URL", "wss://fstream.binance.com") + "/stream?streams="

TIMEFRAMES = [tf.strip() for tf in os.getenv("TIMEFRAMES","1m,3m,5m").split(",")]
ALERT_COOLDOWN_SEC = int(os.getenv("COOLDOWN_SECONDS","90"))
HISTORY_LEN = int(os.getenv("HISTORY_LEN","300"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SIGNALS_ACTIVE = os.path.join(DATA_DIR, "signals_active.json")
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(SIGNALS_ACTIVE):
    save_json(SIGNALS_ACTIVE, {})

def save_active(d):
    with open(SIGNALS_ACTIVE, "w") as f:
        json.dump(d, f, indent=2, default=str)

def load_active():
    if not os.path.exists(SIGNALS_ACTIVE):
        return {}
    return json.load(open(SIGNALS_ACTIVE))

async def monitor_chunk(symbols):
    history = {s.upper(): {tf: {"open_time": deque(maxlen=HISTORY_LEN), "open": deque(maxlen=HISTORY_LEN),
                               "high": deque(maxlen=HISTORY_LEN),"low": deque(maxlen=HISTORY_LEN),
                               "close": deque(maxlen=HISTORY_LEN),"volume": deque(maxlen=HISTORY_LEN)} for tf in TIMEFRAMES} for s in symbols}
    bot = make_bot(TELEGRAM_TOKEN)
    last_alert = defaultdict(lambda: 0.0)
    streams = "/".join(f"{s}@kline_{tf}" for s in symbols for tf in TIMEFRAMES)
    ws_url = FSTREAM + streams
    reconnect = 5
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10, max_queue=None) as ws:
                async for raw in ws:
                    try:
                        parsed = json.loads(raw)
                        data = parsed.get("data",{})
                        k = data.get("k",{})
                        if not k or not k.get("x", False):
                            continue
                        sym = k.get("s","").upper()
                        tf = k.get("i","")
                        if sym not in history: continue
                        h = history[sym][tf]
                        h["open_time"].append(int(k.get("t",0)))
                        h["open"].append(float(k.get("o",0)))
                        h["high"].append(float(k.get("h",0)))
                        h["low"].append(float(k.get("l",0)))
                        h["close"].append(float(k.get("c",0)))
                        h["volume"].append(float(k.get("v",0)))

                        # build df for this timeframe
                        df = pd.DataFrame({
                            "open_time": list(h["open_time"]),
                            "open": list(h["open"]),
                            "high": list(h["high"]),
                            "low": list(h["low"]),
                            "close": list(h["close"]),
                            "volume": list(h["volume"]),
                        })
                        # require enough candles
                        if len(df) < 60:
                            continue

                        # detect using signal engine v2
                        sig = detect_signal(df)
                        if not sig:
                            continue

                        key = f"{sym}|{tf}"
                        now_ts = time.time()
                        if now_ts - last_alert[key] < ALERT_COOLDOWN_SEC:
                            continue
                        last_alert[key] = now_ts

                        # compute TP/SL using ATR
                        atr = sig.get("atr", 0.0)
                        price = sig["price"]
                        if sig["side"] == "buy":
                            tp1 = price + 0.5 * atr
                            tp2 = price + 1.0 * atr
                            tp3 = price + 1.5 * atr
                            sl  = price - 0.8 * atr
                        else:
                            tp1 = price - 0.5 * atr
                            tp2 = price - 1.0 * atr
                            tp3 = price - 1.5 * atr
                            sl  = price + 0.8 * atr

                        # create entry and save
                        signals = load_active()
                        uid = f"{sym}_{tf}_{int(time.time())}"
                        tstamp = datetime.now(timezone.utc).isoformat()
                        entry = {
                            "id": uid, "symbol": sym, "tf": tf, "side": sig["side"],
                            "entry": price, "tp1": tp1, "tp2": tp2, "tp3": tp3, "sl": sl,
                            "confidence": sig.get("confidence", 0), "reason": sig.get("reason",""),
                            "atr": atr, "vol": sig.get("vol", 0), "status": "OPEN", "time": tstamp
                        }
                        signals[uid] = entry
                        save_active(signals)

                        # send telegram message
                        msg = (
                            f"🔥 *GOLDEN MOMENT* — {sym}\n"
                            f"TF: *{tf}*  |  Side: *{sig['side'].upper()}*  |  Confidence: *{entry['confidence']}%*\n\n"
                            f"Entry: `{price:.8f}`\n"
                            f"TP1: `{tp1:.8f}`  TP2: `{tp2:.8f}`  TP3: `{tp3:.8f}`\n"
                            f"SL: `{sl:.8f}`\n\n"
                            f"Reason: {entry['reason']}\n"
                            f"Time: {tstamp}"
                        )
                        await send_message_async(bot, TELEGRAM_CHAT_ID, msg)
                        print(f"Sent signal {sym} {tf} {sig['side']} confidence {entry['confidence']} at {tstamp}")

                    except Exception as e:
                        print("processing error:", e)
                        continue
        except Exception as e:
            print("WS error:", e)
            await asyncio.sleep(reconnect)
            reconnect = min(60, reconnect*2)
