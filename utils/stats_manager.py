
import json, os
from datetime import datetime, timezone

from .data_store import load_json, save_json, append_history

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def record_result(entry):
    # entry must contain: symbol, tf, side, entry, exit, result, profit_percent, timestamp
    append_history(entry)
    # update daily
    daily = load_json("daily_stats.json") or {}
    d = entry.get("timestamp", datetime.now(timezone.utc).isoformat())[:10]
    rec = daily.get(d, {"total":0,"wins":0,"losses":0,"pnl":0.0})
    rec["total"] += 1
    if entry["profit_percent"] >= 0:
        rec["wins"] += 1
    else:
        rec["losses"] += 1
    rec["pnl"] += entry["profit_percent"]
    daily[d] = rec
    save_json("daily_stats.json", daily)
    # update monthly
    monthly = load_json("monthly_stats.json") or {}
    m = d[:7]
    rec2 = monthly.get(m, {"total":0,"wins":0,"losses":0,"pnl":0.0})
    rec2["total"] += 1
    if entry["profit_percent"] >= 0:
        rec2["wins"] += 1
    else:
        rec2["losses"] += 1
    rec2["pnl"] += entry["profit_percent"]
    monthly[m] = rec2
    save_json("monthly_stats.json", monthly)

def generate_daily_report(date_str):
    daily = load_json("daily_stats.json") or {}
    rec = daily.get(date_str)
    if not rec:
        return f"No data for {date_str}"
    total = rec["total"]
    wins = rec["wins"]
    losses = rec["losses"]
    win_rate = wins/total*100 if total>0 else 0.0
    avg = rec["pnl"]/total if total>0 else 0.0
    return f"""📅 Daily Report — {date_str}
Total: {total}
Wins: {wins} ({win_rate:.1f}%)
Losses: {losses}
Avg PnL: {avg:.4f}%"""
