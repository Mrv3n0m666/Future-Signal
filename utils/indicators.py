
import numpy as np
import pandas as pd

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def rsi(series, period):
    delta = series.diff()
    up = delta.clip(lower=0).rolling(period).mean()
    down = -delta.clip(upper=0).rolling(period).mean()
    rs = up / down.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def atr(high, low, close, period=14):
    h = high.astype(float); l = low.astype(float); c = close.astype(float)
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    a = tr.rolling(period).mean()
    return a.fillna(method="bfill")
