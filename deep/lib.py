"""
Shared tools for the deep analysis: load the data branch, build every timeframe the way
TradingView does (regular hours, bars anchored at 9:30), indicators, levels.
"""
import os
import numpy as np, pandas as pd

DATA = os.environ.get("DEEP_DATA", "deepdata")


# ---------------- loading ----------------
def load_daily(sym):
    p = f"{DATA}/daily/{sym}.parquet"
    if not os.path.exists(p):
        return None
    d = pd.read_parquet(p)
    d["t"] = pd.to_datetime(d.t).dt.normalize()
    return d.drop_duplicates("t").set_index("t").sort_index()


def load_m5(sym):
    p = f"{DATA}/m5/{sym}.parquet"
    if not os.path.exists(p):
        return None
    m = pd.read_parquet(p)
    m["t"] = pd.to_datetime(m.t)
    for c in "ohlcv":
        m[c] = m[c].astype("float64")
    return m.drop_duplicates("t").set_index("t").sort_index()


def load_vix():
    p = f"{DATA}/vix.parquet"
    if not os.path.exists(p):
        return None
    v = pd.read_parquet(p)
    v["t"] = pd.to_datetime(v.t).dt.normalize()
    return v.set_index("t").vix


# ---------------- timeframes ----------------
def resample_intraday(m5, minutes):
    """Regular-hours bars anchored at 9:30 (TradingView style). minutes=240 gives 9:30-13:30 and 13:30-16:00.
    Index = bar END time (the moment the bar is complete)."""
    tod = m5.index.hour * 60 + m5.index.minute - 570
    day = m5.index.normalize()
    slot = tod // minutes
    g = m5.groupby([day, slot])
    out = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(), "v": g.v.sum()})
    days = out.index.get_level_values(0)
    slots = out.index.get_level_values(1)
    end_min = np.minimum((slots + 1) * minutes, 390) + 570
    out.index = days + pd.to_timedelta(end_min, unit="m")
    return out


def resample_clock(m5, minutes, anchor=0):
    """Extended-hours bars the way thinkorswim builds them with pre/after-market ON: buckets on the clock.
    minutes=60 -> 9:00-10:00, 10:00-11:00 ...; minutes=240, anchor=60 -> 5-9, 9-13, 13-17, 17-21 (futures-day
    anchoring, cut at the 5 PM futures maintenance hour). Index = bar END time (nominal)."""
    tod = m5.index.hour * 60 + m5.index.minute
    day = m5.index.normalize()
    slot = (tod - anchor) // minutes
    g = m5.groupby([day, slot])
    out = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(), "v": g.v.sum()})
    days = out.index.get_level_values(0)
    slots = out.index.get_level_values(1)
    out.index = days + pd.to_timedelta(anchor + (slots + 1) * minutes, unit="m")
    return out


def rth_mask(idx_end):
    """True for bars that END inside regular hours (9:35 .. 16:00): the only times an option order can fill."""
    tod = idx_end.hour * 60 + idx_end.minute
    return (tod > 570) & (tod <= 960)


def m5_end_index(m5):
    """5-min bars are stamped at their START; this returns a copy stamped at their END."""
    x = m5.copy()
    x.index = x.index + pd.Timedelta(minutes=5)
    return x


def weekly(daily):
    w = daily.resample("W-FRI").agg({"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}).dropna()
    return w


# ---------------- indicators ----------------
def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df, n=14):
    pc = df.c.shift()
    tr = pd.concat([df.h - df.l, (df.h - pc).abs(), (df.l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def add_ind(df, smas=(10, 20, 50, 200)):
    """Adds SMAs, RSI14 + its 14 SMA (TradingView default), MACD 12/26/9, ATR14."""
    df = df.copy()
    for n in smas:
        df[f"sma{n}"] = sma(df.c, n)
    df["rsi"] = rsi(df.c)
    df["rsi_ma"] = sma(df.rsi, 14)
    df["macd"] = ema(df.c, 12) - ema(df.c, 26)
    df["macd_sig"] = ema(df.macd, 9)
    df["hist"] = df.macd - df.macd_sig
    df["atr"] = atr(df)
    return df


def pivots_high(h, k=2):
    """Swing high at bar i if it's the highest of i-k..i+k. Known only k bars later (no peeking)."""
    roll = h.rolling(2 * k + 1, center=True).max()
    return h[(h == roll)]


def pivots_low(l, k=2):
    roll = l.rolling(2 * k + 1, center=True).min()
    return l[(l == roll)]


# ---------------- levels below price (for shorts) ----------------
def volume_profile(m5_days, bins=60):
    """POC / VAH / VAL (70%) from 5-min bars of the given sessions (typical price weighting)."""
    if m5_days is None or len(m5_days) < 10:
        return np.nan, np.nan, np.nan
    tp = (m5_days.h + m5_days.l + m5_days.c) / 3
    lo, hi = m5_days.l.min(), m5_days.h.max()
    if hi <= lo:
        return np.nan, np.nan, np.nan
    edges = np.linspace(lo, hi, bins + 1)
    idx = np.clip(np.digitize(tp, edges) - 1, 0, bins - 1)
    vol = np.bincount(idx, weights=m5_days.v.values, minlength=bins)
    mid = (edges[:-1] + edges[1:]) / 2
    poc = int(vol.argmax())
    tot, acc, a, b = vol.sum(), vol[poc], poc, poc
    while acc < 0.7 * tot and (a > 0 or b < bins - 1):
        va = vol[a - 1] if a > 0 else -1
        vb = vol[b + 1] if b < bins - 1 else -1
        if va >= vb:
            a -= 1; acc += vol[a]
        else:
            b += 1; acc += vol[b]
    return mid[poc], mid[b], mid[a]


def levels_below(price, day, daily_ind, m5, h1_ind, min_gap=0.0):
    """Support levels under `price` known at the start of session `day` (only past data).
    Returns sorted list (nearest first) of (price, name)."""
    D = daily_ind[daily_ind.index < day]
    if len(D) < 30:
        return []
    lv = []
    last = D.iloc[-1]
    lv.append((last.l, "prior day low"))
    wk = D[D.index >= (day - pd.Timedelta(days=day.weekday() + 7))]
    wk = wk[wk.index < (day - pd.Timedelta(days=day.weekday()))]
    if len(wk):
        lv.append((wk.l.min(), "prior week low"))
    for n in (10, 20, 50, 200):
        v = last.get(f"sma{n}")
        if pd.notna(v):
            lv.append((v, f"daily {n} SMA"))
    # unfilled gaps (gap up whose bottom = prior day's high, never traded back into since)
    tail = D.iloc[-120:]
    hs, ls = tail.h.values, tail.l.values
    for i in range(1, len(tail)):
        if ls[i] > hs[i - 1]:
            top = hs[i - 1]
            if ls[i + 1:].size == 0 or ls[i + 1:].min() > top:
                lv.append((top, "unfilled gap"))
    # daily swing lows (last 60 days)
    pl = pivots_low(D.l.iloc[-62:], 2)
    for v in pl.values[-6:]:
        lv.append((v, "daily swing low"))
    # hourly swing lows (last 10 days)
    if h1_ind is not None:
        H = h1_ind[(h1_ind.index < day) & (h1_ind.index >= day - pd.Timedelta(days=14))]
        if len(H) > 5:
            for v in pivots_low(H.l, 2).values[-8:]:
                lv.append((v, "hourly swing low"))
    # volume profile of prior 5 sessions
    if m5 is not None:
        prev_days = D.index[-5:]
        mm = m5[(m5.index >= prev_days[0]) & (m5.index < day)]
        poc, vah, val = volume_profile(mm)
        for v, nm in ((poc, "5-day volume POC"), (val, "5-day value area low"), (vah, "5-day value area high")):
            if pd.notna(v):
                lv.append((v, nm))
    out = sorted([(float(p), n) for p, n in lv if pd.notna(p) and p < price * 0.999 and price - p >= min_gap],
                 key=lambda x: -x[0])
    # merge levels within 0.15% of each other
    merged = []
    for p, n in out:
        if merged and abs(merged[-1][0] - p) / p < 0.0015:
            if n not in merged[-1][1]:
                merged[-1] = (merged[-1][0], merged[-1][1] + " + " + n)
        else:
            merged.append((p, n))
    return merged


def levels_above(price, day, daily_ind, m5, h1_ind):
    """Resistance levels above price (for stops)."""
    D = daily_ind[daily_ind.index < day]
    if len(D) < 30:
        return []
    last = D.iloc[-1]
    lv = [(last.h, "prior day high")]
    for n in (10, 20, 50, 200):
        v = last.get(f"sma{n}")
        if pd.notna(v):
            lv.append((v, f"daily {n} SMA"))
    for v in pivots_high(D.h.iloc[-62:], 2).values[-6:]:
        lv.append((v, "daily swing high"))
    if h1_ind is not None:
        H = h1_ind[(h1_ind.index < day) & (h1_ind.index >= day - pd.Timedelta(days=14))]
        if len(H) > 5:
            for v in pivots_high(H.h, 2).values[-8:]:
                lv.append((v, "hourly swing high"))
    return sorted([(float(p), n) for p, n in lv if pd.notna(p) and p > price * 1.001], key=lambda x: x[0])
