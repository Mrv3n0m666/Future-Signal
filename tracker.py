
import time, os, json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.data_store import load_json, save_json, append_history
from utils.stats_manager import record_result
from telegram import Bot

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FAPI = os.getenv("BINANCE_REST_URL","https://fapi.binance.com")
POLL = int(os.getenv("CHECK_PRICE_INTERVAL","20"))

bot = Bot(token=TELEGRAM_TOKEN)

def get_price(sym):
    try:
        r = requests.get(FAPI + "/fapi/v1/ticker/price", params={"symbol":sym}, timeout=8)
        r.raise_for_status()
        return float(r.json().get("price",0))
    except:
        return None

def send_msg(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        print("tg error", e)

def load_active():
    p = os.path.join(os.path.dirname(__file__),"data","signals_active.json")
    if not os.path.exists(p):
        return {}
    return json.load(open(p))

def save_active(d):
    p = os.path.join(os.path.dirname(__file__),"data","signals_active.json")
    json.dump(d, open(p,"w"), indent=2, default=str)

def check_signals():
    active = load_active()
    changed = False
    now = datetime.now(timezone.utc).isoformat()
    for uid, s in list(active.items()):
        if s.get("status") != "OPEN": continue
        sym = s["symbol"]
        price = get_price(sym)
        if price is None: continue
        side = s["side"]
        entry = s["entry"]
        tp1, tp2, tp3, sl = s["tp1"], s["tp2"], s["tp3"], s["sl"]
        hit = None
        if side=="buy":
            if price >= tp3: hit=("TP3", tp3)
            elif price >= tp2: hit=("TP2", tp2)
            elif price >= tp1: hit=("TP1", tp1)
            elif price <= sl: hit=("SL", sl)
        else:
            if price <= tp3: hit=("TP3", tp3)
            elif price <= tp2: hit=("TP2", tp2)
            elif price <= tp1: hit=("TP1", tp1)
            elif price >= sl: hit=("SL", sl)
        if hit:
            tag, level = hit
            s["status"]="CLOSED"
            s["closed_at"]=now
            s["closed_by"]=tag
            s["closed_price"]=price
            # compute profit percent approx
            profit = (level - entry) / entry * 100 if side=='buy' else (entry - level)/entry*100
            rec = {"symbol":sym,"timeframe":s.get("tf"),"side":side,"entry":entry,"exit":level,"result":tag,"profit_percent":profit,"timestamp":now}
            append_history(rec)
            record_result(rec)
            del active[uid]
            save_active(active)
            send_msg(f"✅ {sym} ({s.get('tf')}) | {tag} Hit @ {level:.8f}\nPnL: {profit:.4f}%")
            changed = True
    return changed

def start_tracker():
    print("Tracker started")
    while True:
        try:
            check_signals()
        except Exception as e:
            print("tracker error", e)
        time.sleep(POLL)

async def start_tracker_async():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, start_tracker)
