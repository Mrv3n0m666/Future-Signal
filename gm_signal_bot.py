
import asyncio, json, os, time
from collections import deque, defaultdict
import pandas as pd, numpy as np
import websockets
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.indicators import ema, rsi, atr
from utils.telegram_utils import make_bot, send_message_async, send_photo_async
from utils.data_store import save_json, load_json
from utils.data_store import _path as ds_path
from utils.data_store import save_json as save_ds_json
from utils.data_store import load_json as load_ds_json
from utils.stats_manager import record_result
from utils.telegram_utils import make_bot
from utils import logger

load_dotenv()
log = logger.get_logger("gm_signal_bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FSTREAM = os.getenv("BINANCE_FAPI_URL", "wss://fstream.binance.com") + "/stream?streams="

TIMEFRAMES = [tf.strip() for tf in os.getenv("TIMEFRAMES","1m,3m,5m").split(",")]
EMA_FAST = int(os.getenv("EMA_FAST","7"))
EMA_MED = int(os.getenv("EMA_SLOW","25"))
EMA_LONG = int(os.getenv("EMA_TREND","99"))
RSI_FAST = int(os.getenv("RSI_FAST","6"))
RSI_SLOW = int(os.getenv("RSI_SLOW","24"))
VOLUME_MULTIPLIER = float(os.getenv("VOLUME_MULTIPLIER","1.3"))
ALERT_COOLDOWN_SEC = int(os.getenv("COOLDOWN_SECONDS","90"))
HISTORY_LEN = int(os.getenv("HISTORY_LEN","300"))

from utils.data_store import load_json, save_json

# re-use previous simple logic in a lightweight form
async def monitor_chunk(symbols):
    # history per symbol per tf
    history = {s.upper(): {tf: {"open_time": deque(maxlen=HISTORY_LEN), "open": deque(maxlen=HISTORY_LEN),
                               "high": deque(maxlen=HISTORY_LEN),"low": deque(maxlen=HISTORY_LEN),
                               "close": deque(maxlen=HISTORY_LEN),"volume": deque(maxlen=HISTORY_LEN)} for tf in TIMEFRAMES} for s in symbols}
    bot = make_bot(TELEGRAM_TOKEN)
    last_alert = defaultdict(lambda: 0.0)
    streams = "/".join(f"{s}@kline_{tf}" for s in symbols for tf in TIMEFRAMES)
    ws_url = FSTREAM + streams
    reconnect = 5
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
                h = history[sym][tf]
                h["open_time"].append(int(k.get("t",0)))
                h["open"].append(float(k.get("o",0)))
                h["high"].append(float(k.get("h",0)))
                h["low"].append(float(k.get("l",0)))
                h["close"].append(float(k.get("c",0)))
                h["volume"].append(float(k.get("v",0)))
                # basic indicators and checks:
                df = pd.DataFrame({"open_time": list(h["open_time"]), "open": list(h["open"]), "high": list(h["high"]),
                                   "low": list(h["low"]), "close": list(h["close"]), "volume": list(h["volume"])})
                if len(df) < 120:
                    continue
                closes = df["close"].astype(float)
                highs = df["high"].astype(float)
                lows = df["low"].astype(float)
                vols = df["volume"].astype(float)
                ema_fast = closes.ewm(span=EMA_FAST, adjust=False).mean()
                ema_med = closes.ewm(span=EMA_MED, adjust=False).mean()
                ema_long = closes.ewm(span=EMA_LONG, adjust=False).mean()
                ema_fast_now = ema_fast.iloc[-1]; ema_fast_prev = ema_fast.iloc[-2]
                ema_med_now = ema_med.iloc[-1]; ema_med_prev = ema_med.iloc[-2]
                rsi6 = rsi(closes, RSI_FAST).iloc[-1]
                rsi24 = rsi(closes, RSI_SLOW).iloc[-1]
                vol_ma = vols.rolling(20).mean().iloc[-1]
                vol_now = vols.iloc[-1]
                atr_now = atr(highs, lows, closes).iloc[-1]
                price = float(closes.iloc[-1])
                crossed_up = (ema_fast_prev <= ema_med_prev) and (ema_fast_now > ema_med_now)
                crossed_dn = (ema_fast_prev >= ema_med_prev) and (ema_fast_now < ema_med_now)
                vol_ok = vol_now > (vol_ma * VOLUME_MULTIPLIER)
                side = None
                if crossed_up and rsi6>50 and rsi24>50 and price>ema_long and vol_ok:
                    side = "buy"
                elif crossed_dn and rsi6<50 and rsi24<50 and price<ema_long and vol_ok:
                    side = "short"
                if not side:
                    continue
                key = f"{sym}|{tf}"
                now_ts = time.time()
                if now_ts - last_alert[key] < ALERT_COOLDOWN_SEC:
                    continue
                last_alert[key] = now_ts
                # compute tp/sl
                def compute_tp_sl(side, price, atr):
                    if atr<=0: atr = max(price*0.001, 1e-6)
                    if side=="buy":
                        return {"tp1":price+0.5*atr,"tp2":price+1.0*atr,"tp3":price+1.5*atr,"sl":price-0.8*atr}
                    else:
                        return {"tp1":price-0.5*atr,"tp2":price-1.0*atr,"tp3":price-1.5*atr,"sl":price+0.8*atr}
                tp_sl = compute_tp_sl(side, price, atr_now)
                # save active signal
                signals = load_json(os.path.join(os.path.dirname(__file__),"..","data","signals_active.json"))
                uid = f"{sym}_{tf}_{int(time.time())}"
                entry = {"id":uid,"symbol":sym,"tf":tf,"side":side,"entry":price,"tp1":tp_sl["tp1"],"tp2":tp_sl["tp2"],"tp3":tp_sl["tp3"],"sl":tp_sl["sl"],"status":"OPEN","time":datetime.now(timezone.utc).isoformat()}
                signals[uid]=entry
                save_json(os.path.join(os.path.dirname(__file__),"..","data","signals_active.json"), signals)
                # send telegram message (text only to keep it light)
                msg = f"🚨 GOLDEN MOMENT — {sym}\nTF: {tf}\nSide: {side.upper()}\nEntry: {price:.8f}\nTP1: {tp_sl['tp1']:.8f} TP2: {tp_sl['tp2']:.8f} TP3: {tp_sl['tp3']:.8f}\nSL: {tp_sl['sl']:.8f}"
                await send_message_async(make_bot(TELEGRAM_TOKEN), TELEGRAM_CHAT_ID, msg)
            except Exception as e:
                print("processing error",e)
                continue

async def start_signal_monitor():
    # read symbols from data/symbols.json if exists; else default to BTCUSDT
    syms_file = os.path.join(os.path.dirname(__file__),"..","data","symbols.json")
    if os.path.exists(syms_file):
        s = json.load(open(syms_file))
        syms = s.get("symbols", ["BTCUSDT"])[:60]
    else:
        syms = ["BTCUSDT"]
    # chunk into groups of 20 symbols (each group spawns one websocket)
    chunks = [syms[i:i+20] for i in range(0, len(syms), 20)]
    tasks = [asyncio.create_task(monitor_chunk(chunk)) for chunk in chunks]
    await asyncio.gather(*tasks)
