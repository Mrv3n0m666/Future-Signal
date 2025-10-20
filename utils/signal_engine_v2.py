# utils/signal_engine_v2.py
import numpy as np
import pandas as pd
from datetime import datetime, timezone, time as dtime
from .indicators import atr as compute_atr

# Config parameters (ubah lewat env nanti jika perlu)
EMA_FAST = 8
EMA_MED = 21
EMA_LONG = 55
EMA_TREND = 200

RSI_PERIOD = 14
MFI_PERIOD = 14
VOL_MULT = 1.5
ATR_PCT_MIN = 0.002  # minimal ATR relative to price (0.2%)
ACTIVE_HOUR_START = 8   # UTC
ACTIVE_HOUR_END = 22    # UTC

# Candle pattern helpers
def body_size(o, c):
    return abs(c - o)

def is_bullish(row): return float(row["close"]) > float(row["open"])
def is_bearish(row): return float(row["close"]) < float(row["open"])

def detect_bullish_engulfing(df):
    # check last two candles
    if len(df) < 2: return False
    a = df.iloc[-2]
    b = df.iloc[-1]
    if is_bearish(a) and is_bullish(b):
        body_a = body_size(a["open"], a["close"])
        body_b = body_size(b["open"], b["close"])
        return body_b >= 1.5 * body_a and b["open"] < a["close"] and b["close"] > a["open"]
    return False

def detect_bearish_engulfing(df):
    if len(df) < 2: return False
    a = df.iloc[-2]
    b = df.iloc[-1]
    if is_bullish(a) and is_bearish(b):
        body_a = body_size(a["open"], a["close"])
        body_b = body_size(b["open"], b["close"])
        return body_b >= 1.5 * body_a and b["open"] > a["close"] and b["close"] < a["open"]
    return False

def detect_hammer(df):
    if len(df) < 1: return False
    b = df.iloc[-1]
    o, h, l, c = float(b["open"]), float(b["high"]), float(b["low"]), float(b["close"])
    body = abs(c - o)
    lower_shadow = min(o, c) - l
    upper_shadow = h - max(o, c)
    return lower_shadow >= 2 * body and upper_shadow <= body

def detect_shooting_star(df):
    if len(df) < 1: return False
    b = df.iloc[-1]
    o, h, l, c = float(b["open"]), float(b["high"]), float(b["low"]), float(b["close"])
    body = abs(c - o)
    upper_shadow = h - max(o, c)
    lower_shadow = min(o, c) - l
    return upper_shadow >= 2 * body and lower_shadow <= body

# RSI
def compute_rsi(series: pd.Series, period=RSI_PERIOD):
    delta = series.diff()
    up = delta.clip(lower=0).rolling(period).mean()
    down = -delta.clip(upper=0).rolling(period).mean()
    rs = up / down.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

# MFI
def compute_mfi(df: pd.DataFrame, period=MFI_PERIOD):
    typical = (df["high"] + df["low"] + df["close"]) / 3
    money = typical * df["volume"]
    direction = typical.diff().fillna(0)
    up = money.where(direction > 0, 0).rolling(period).sum()
    down = money.where(direction < 0, 0).abs().rolling(period).sum()
    mfr = up / down.replace(0, np.nan)
    mfi = 100 - (100 / (1 + mfr))
    return mfi.fillna(50)

def time_ok():
    now = datetime.now(timezone.utc).time()
    return dtime(ACTIVE_HOUR_START, 0) <= now <= dtime(ACTIVE_HOUR_END, 0)

def detect_signal(df: pd.DataFrame):
    """
    df: DataFrame with columns open, high, low, close, volume (ordered oldest..newest)
    returns dict if signal found:
      {"side":"buy"/"short", "price":..., "confidence":.., "reason": "...", "atr":..., "vol":...}
    otherwise None
    """
    if df is None or len(df) < max(EMA_TREND, MFI_PERIOD, RSI_PERIOD, 20) // 1:
        return None

    # Time filter
    if not time_ok():
        return None

    closes = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    vols = df["volume"].astype(float)

    # EMAs
    ema_fast = closes.ewm(span=EMA_FAST, adjust=False).mean()
    ema_med = closes.ewm(span=EMA_MED, adjust=False).mean()
    ema_long = closes.ewm(span=EMA_LONG, adjust=False).mean()
    ema_trend = closes.ewm(span=EMA_TREND, adjust=False).mean()

    ema_fast_now = ema_fast.iloc[-1]
    ema_med_now = ema_med.iloc[-1]
    ema_long_now = ema_long.iloc[-1]
    ema_trend_now = ema_trend.iloc[-1]

    ema_fast_prev = ema_fast.iloc[-2]
    ema_med_prev = ema_med.iloc[-2]

    # Momentum
    rsi = compute_rsi(closes)
    mfi = compute_mfi(df)

    rsi_now = rsi.iloc[-1]
    mfi_now = mfi.iloc[-1]

    # Volume
    vol_ma20 = vols.rolling(20).mean().iloc[-1]
    vol_now = vols.iloc[-1]
    vol_ok = vol_now >= VOL_MULT * (vol_ma20 if vol_ma20>0 else 1)

    # ATR for TP/SL and filter
    atr_s = compute_atr(highs, lows, closes)
    atr_now = atr_s.iloc[-1]
    price_now = float(closes.iloc[-1])
    if atr_now / price_now < ATR_PCT_MIN:
        # volatility too low
        return None

    # Candle patterns
    bull_eng = detect_bullish_engulfing(df)
    bear_eng = detect_bearish_engulfing(df)
    hammer = detect_hammer(df)
    shoot = detect_shooting_star(df)
    breakout = body_size(df.iloc[-1]["open"], df.iloc[-1]["close"]) >= 1.8 * df["close"].pct_change().abs().rolling(20).mean().fillna(0).iloc[-1] if len(df)>20 else False

    # Trend alignment
    long_trend = (ema_fast_prev <= ema_med_prev) and (ema_fast_now > ema_med_now) and (ema_fast_now > ema_long_now) and (price_now > ema_trend_now)
    short_trend = (ema_fast_prev >= ema_med_prev) and (ema_fast_now < ema_med_now) and (ema_fast_now < ema_long_now) and (price_now < ema_trend_now)

    # Compose conditions
    buy_cond = long_trend and (rsi_now > 55) and (mfi_now > 55) and vol_ok and (bull_eng or hammer or breakout)
    short_cond = short_trend and (rsi_now < 45) and (mfi_now < 45) and vol_ok and (bear_eng or shoot or breakout)

    if buy_cond:
        confidence = 80
        # add confidence bumps
        if bull_eng: confidence += 6
        if vol_now > 2 * (vol_ma20 if vol_ma20>0 else 1): confidence += 6
        if rsi_now > 65 and mfi_now > 65: confidence += 6
        return {
            "side": "buy",
            "price": price_now,
            "atr": float(atr_now),
            "vol": float(vol_now),
            "confidence": min(confidence, 98),
            "reason": "EMA+RSI+MFI+Volume+Candle"
        }
    if short_cond:
        confidence = 80
        if bear_eng: confidence += 6
        if vol_now > 2 * (vol_ma20 if vol_ma20>0 else 1): confidence += 6
        if rsi_now < 35 and mfi_now < 35: confidence += 6
        return {
            "side": "short",
            "price": price_now,
            "atr": float(atr_now),
            "vol": float(vol_now),
            "confidence": min(confidence, 98),
            "reason": "EMA+RSI+MFI+Volume+Candle"
        }

    return None
