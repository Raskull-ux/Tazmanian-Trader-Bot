"""
Intraday patterns (Taz's day): death-cross retests and the 'dump to 10, chop up 10-12, dump the rest' day.
Grid = day x 78 five-minute slots (regular hours). Signal on a bar close; short from that close.
"""
import numpy as np, pandas as pd
from . import lib

SLOTS = 78


def grid(m5, D):
    """Builds aligned arrays (days x 78) for o,h,l,c and indicators computed on the continuous 5-min series."""
    m = m5.copy()
    m["sma20"] = lib.sma(m.c, 20)
    m["sma200"] = lib.sma(m.c, 200)
    tod = (m.index.hour * 60 + m.index.minute - 570) // 5
    day = m.index.normalize()
    days = pd.Index(sorted(day.unique()))
    di = days.get_indexer(day)
    G = {}
    for col in ("o", "h", "l", "c", "sma20", "sma200"):
        a = np.full((len(days), SLOTS), np.nan)
        a[di, tod] = m[col].values
        G[col] = a
    # forward-fill missing bars inside a day (thin names)
    for col in ("c", "sma20", "sma200"):
        G[col] = pd.DataFrame(G[col]).ffill(axis=1).values
    for col in ("o", "h", "l"):
        G[col] = np.where(np.isnan(G[col]), G["c"], G[col])
    atr = D.atr.shift().reindex(days).values   # yesterday's daily ATR (known at the open)
    G["atr"] = atr
    G["days"] = days
    # hourly bars from the grid (9:30-10:30 ... 15:30-16:00), with 20/50 SMAs on the continuous hourly series
    H = lib.add_ind(lib.resample_intraday(m5, 60), smas=(20, 50))
    G["H"] = H
    return G


def outcomes(G):
    """Per (day, slot): short from that bar's close -> day close, -> next day close, and
    target-first +-0.5 ATR by the day close."""
    c, h, l, atr = G["c"], G["h"], G["l"], G["atr"]
    nd = c.shape[0]
    close = c[:, -1]
    ret_close = (c - close[:, None]) / c * 100
    nxt = np.append(close[1:], np.nan)
    ret_next = (c - nxt[:, None]) / c * 100
    atr_close = (c - close[:, None]) / atr[:, None]
    win = np.full(c.shape, np.nan)
    for d in range(nd):
        A = atr[d]
        if not np.isfinite(A):
            continue
        e = c[d]                                      # entry at each slot's close
        # bars after slot s: s+1..77
        H = h[d][None, :].repeat(SLOTS, 0)
        L = l[d][None, :].repeat(SLOTS, 0)
        mask = np.triu(np.ones((SLOTS, SLOTS), bool), 1)
        up = (H >= (e + 0.5 * A)[:, None]) & mask
        dn = (L <= (e - 0.5 * A)[:, None]) & mask
        fu = np.where(up.any(1), up.argmax(1), 999)
        fd = np.where(dn.any(1), dn.argmax(1), 999)
        w = np.where(fd < fu, 1.0, np.where(fu < fd, 0.0, 0.5))
        w[(fd == fu) & (fd < 999)] = 0.0
        win[d] = w
    return {"ret_close": ret_close, "ret_next": ret_next, "atr_close": atr_close, "win_half_atr": win}


def first_per_day(sig):
    out = np.zeros_like(sig)
    has = sig.any(1)
    out[np.where(has)[0], sig[has].argmax(1)] = True
    return out


def signals(G):
    c, h, l, o, s200, s20, atr = G["c"], G["h"], G["l"], G["o"], G["sma200"], G["sma20"], G["atr"]
    nd = c.shape[0]
    slot = np.arange(SLOTS)[None, :].repeat(nd, 0)
    S = {}
    # --- 5-min 200 SMA rejection: a high at/above the 200 in the last 6 bars, then a close back under it
    touch = h >= s200
    touch6 = pd.DataFrame(touch.T).rolling(6, min_periods=1).max().values.T.astype(bool)
    prev_above = np.concatenate([np.zeros((nd, 1), bool), c[:, :-1] >= s200[:, :-1]], 1)
    rej = touch6 & (c < s200) & (prev_above | touch)
    t_ok = (slot >= 5) & (slot <= 65)                              # bar closes 10:00 .. 15:00
    S["5m 200 SMA rejection (10:00-15:00)"] = first_per_day(rej & t_ok)
    # wedge: rising lows over the last 12 bars and a narrowing range into the touch
    L = pd.DataFrame(l.T)
    x = np.arange(12) - 5.5
    slope = np.full(l.shape, np.nan)
    acc = np.zeros((nd, SLOTS - 11))
    for j in range(12):
        acc += x[j] * l[:, j:SLOTS - 11 + j]
    slope[:, 11:] = acc / np.dot(x, x)
    Hd = pd.DataFrame(h.T)
    rng_now = (Hd.rolling(6).max() - L.rolling(6).min()).values.T
    rng_prev = (Hd.shift(6).rolling(6).max() - L.shift(6).rolling(6).min()).values.T
    wedge = (slope > 0) & (rng_now < rng_prev)
    wedge6 = pd.DataFrame(wedge.T).rolling(6, min_periods=1).max().values.T.astype(bool)
    S["rising wedge into 5m 200 SMA, close under"] = first_per_day(rej & t_ok & wedge6)
    # the ideal day: dumped by 10:00, chopped up 10-12 into the 200, rejected
    lo_am = np.nanmin(l[:, :6], 1)
    dump = (o[:, 0] - lo_am) >= 0.3 * atr
    t_mid = (slot >= 6) & (slot <= 36)                             # 10:05 .. 12:35
    S["dump by 10, chop up into 5m 200, rejected"] = first_per_day(rej & t_mid & dump[:, None])
    S["dump by 10 + wedge into 5m 200, rejected"] = first_per_day(rej & t_mid & dump[:, None] & wedge6)
    # ideal day without the 200: dump >= 0.4 ATR by 10:00, retrace >= 40% by 12:00 without taking the open,
    # first 5-min close under the 5-min 20 SMA after 12:00
    drop = o[:, 0] - lo_am
    hi_mid = np.nanmax(h[:, 6:30], 1)
    retr = (hi_mid - lo_am) >= 0.4 * drop
    under_open = hi_mid < o[:, 0]
    day_ok = (drop >= 0.4 * atr) & retr & under_open
    after12 = (slot >= 30) & (slot <= 60)
    cross20 = (c < s20) & np.concatenate([np.zeros((nd, 1), bool), c[:, :-1] >= s20[:, :-1]], 1)
    S["dump to 10, bounce 10-12, lose 5m 20 after 12"] = first_per_day(cross20 & after12 & day_ok[:, None])
    # --- hourly: 20 SMA under 50 SMA (death cross) and a retest of the 20, close back under
    H = G["H"]
    days = G["days"]
    hd = H.index.normalize()
    hslot = ((H.index.hour * 60 + H.index.minute - 570) // 5 - 1).astype(int)   # 5-min slot of the bar's last 5 min
    hslot = np.minimum(hslot, SLOTS - 1)
    di = days.get_indexer(hd)
    ok = (di >= 0)
    retest = ((H.sma20 < H.sma50) & (H.h >= H.sma20) & (H.c < H.sma20)).values & ok
    cross = ((H.sma20 < H.sma50) & (H.sma20.shift() >= H.sma50.shift())).values & ok
    for name, cond in (("hourly 20/50 death cross, retest of the 20", retest),
                       ("hourly 20 SMA crosses under 50 SMA", cross)):
        a = np.zeros((nd, SLOTS), bool)
        sel = cond & (hslot >= 11) & (hslot <= 71)                      # bars ending 10:30 .. 15:30
        a[di[sel], hslot[sel]] = True
        S[name] = first_per_day(a)
    return S


def baselines(OUTC, days):
    """name-year-slot means of each outcome."""
    yrs = days.year.values
    B = {}
    for k, v in OUTC.items():
        b = np.full_like(v, np.nan)
        for y in np.unique(yrs):
            r = yrs == y
            b[r] = np.nanmean(v[r], 0)[None, :]
        B[k] = b
    return B
