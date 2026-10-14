"""
Taz's chart patterns, tested on every name, every day, 2016 -> now.
Discovery = 2016-2022. Holdout (never looked at while defining) = 2023 -> now.

DAILY patterns fire on a daily close; the trade is the NEXT session's open.
INTRADAY patterns fire on a 5-min / hourly close; the trade is that close.

Scoring (short side, so + = price went down):
  ret_Xd    open->close move over X sessions (short direction), in % and in ATRs
  win_1atr  fell 1 daily ATR before rising 1 ATR within 5 sessions (0.5 if neither)
  baseline  the same name's average over ALL days of the same year (daily patterns) or
            the same name / year / 5-min slot (intraday), so a pattern only scores if it beats
            just being short that name that year at that time of day.
t-stats are clustered by calendar week (many names firing the same week count once).
"""
import numpy as np, pandas as pd
from . import lib

SPLIT = pd.Timestamp("2023-01-01")


# =============== daily pattern detectors: return boolean Series on D.index ===============
def p_bear_flag(D, pole_atr=3.0, max_retrace=0.62, trigger="flag_low"):
    a, h, l, c = D.atr.values, D.h.values, D.l.values, D.c.values
    n = len(D)
    sig = np.zeros(n, bool)
    used_pole = set()
    hi20 = pd.Series(h).rolling(20).max().values
    for i in range(30, n):
        # pole: a 20-day high at day ia, then a low at day ib, ib - ia <= 7, ib in [i-12, i-3]
        for ib in range(i - 12, i - 2):
            ia0 = max(0, ib - 7)
            ia = ia0 + int(np.argmax(h[ia0:ib + 1]))
            if ia >= ib or h[ia] < hi20[ia] - 1e-9:
                continue
            ibl = ib  # low of the pole must be the lowest low from ia..ib
            if l[ibl] > l[ia:ib + 1].min() + 1e-9:
                continue
            pole = h[ia] - l[ibl]
            if pole < pole_atr * a[ibl] or (ia, ibl) in used_pole:
                continue
            flag = slice(ibl + 1, i)
            if i - ibl < 3:
                continue
            fh, fl = h[flag].max(), l[flag].min()
            if fh > l[ibl] + max_retrace * pole:      # bounced too much: not a flag
                continue
            if c[flag].max() < l[ibl] + 0.2 * pole:    # never bounced: not a flag either
                continue
            if trigger == "flag_low":
                ok = c[i] < fl
            else:  # prior day low
                ok = c[i] < l[i - 1]
            if ok:
                sig[i] = True
                used_pole.add((ia, ibl))
                break
    return pd.Series(sig, D.index)


def colors(D):
    return np.where(D.c.values > D.o.values, "G", "R")


def p_seq(D, seq, ctx=None):
    col = colors(D)
    k = len(seq)
    s = np.array(["".join(col[i - k + 1:i + 1]) if i >= k - 1 else "" for i in range(len(D))])
    out = pd.Series(s == seq, D.index)
    if ctx == "near_high":     # a 20-day high was made within the last 10 days
        hi = D.h.rolling(20).max()
        recent = (D.h >= hi).rolling(10).max().astype(bool)
        out &= recent
    if ctx == "below_20":
        out &= D.c < D.sma20
    return out


def p_falling_three(D, strict=True):
    b = (D.c - D.o) / D.atr
    o_, c_, h_, l_ = D.o.values, D.c.values, D.h.values, D.l.values
    bv = b.values
    sig = np.zeros(len(D), bool)
    for i in range(5, len(D)):
        if not (bv[i - 4] <= -0.8 and bv[i] <= -0.8):
            continue
        mid = range(i - 3, i)
        greens = sum(1 for j in mid if c_[j] > o_[j])
        if strict:
            ok = greens >= 2 and all(abs(bv[j]) < 0.6 for j in mid) and max(h_[j] for j in mid) <= h_[i - 4] \
                 and c_[i] < c_[i - 4]
        else:   # Taz's version: red, 3 greens, big red
            ok = greens == 3 and c_[i] < min(o_[j] for j in mid)
        sig[i] = ok
    return pd.Series(sig, D.index)


def p_sandwich(D, need_cross=False):
    b = ((D.c - D.o) / D.atr).values
    sig = np.zeros(len(D), bool)
    for i in range(2, len(D)):
        sig[i] = b[i - 2] <= -0.5 and 0 < b[i - 1] <= 0.4 and b[i] <= -1.0 and b[i] < b[i - 2]
    s = pd.Series(sig, D.index)
    if need_cross:
        s &= D.sma10 < D.sma20
    return s


def _pivots(x, k, kind):
    """Pivot indices confirmed k bars later: returns array conf[i] = list of pivots known at i."""
    v = x.values
    piv = []
    for i in range(k, len(v) - k):
        w = v[i - k:i + k + 1]
        if (kind == "h" and v[i] == w.max()) or (kind == "l" and v[i] == w.min()):
            piv.append(i)
    return piv


def p_head_shoulders(D, k=3):
    h, l, c, a = D.h.values, D.l.values, D.c.values, D.atr.values
    ph = _pivots(D.h, k, "h")
    sig = np.zeros(len(D), bool)
    fired = set()
    for n in range(2, len(ph)):
        i1, i2, i3 = ph[n - 2], ph[n - 1], ph[n]
        if i3 - i1 > 60:
            continue
        A = a[i3]
        if not (h[i2] - max(h[i1], h[i3]) >= 1.0 * A and abs(h[i1] - h[i3]) <= 1.0 * A):
            continue
        neck = (l[i1:i2 + 1].min() + l[i2:i3 + 1].min()) / 2
        for i in range(i3 + k, min(len(D), i3 + k + 20)):
            if h[i] > h[i3]:
                break
            if c[i] < neck:
                if (i1, i2, i3) not in fired:
                    sig[i] = True; fired.add((i1, i2, i3))
                break
    return pd.Series(sig, D.index)


def p_double_top(D, k=3, early=False):
    h, l, c, o, a = D.h.values, D.l.values, D.c.values, D.o.values, D.atr.values
    ph = _pivots(D.h, k, "h")
    sig = np.zeros(len(D), bool)
    if early:
        # anticipation, no peeking: a confirmed first top A; since then price came back up to within 0.5 ATR
        # of A's high (second top, day iB), after a trough >= 1.5 ATR below; today is a red day closing under
        # the second top's day low. One signal per first top.
        done = set()
        phs = np.array(ph)
        for i in range(10, len(D)):
            known = phs[phs + k <= i - 1]
            if not len(known):
                continue
            iA = known[-1]
            if iA in done or i - iA > 60 or i - iA < 6:
                continue
            seg = h[iA + 1:i]
            iB = iA + 1 + int(np.argmax(seg))
            A = a[i - 1]
            if iB - iA < 5 or abs(h[iB] - h[iA]) > 0.5 * A or h[iB] > h[iA] + 0.5 * A:
                continue
            trough = l[iA:iB + 1].min()
            if min(h[iA], h[iB]) - trough < 1.5 * A:
                continue
            if i - iB > 5:
                continue
            if c[i] < o[i] and c[i] < l[iB] and h[i] <= max(h[iA], h[iB]):
                sig[i] = True; done.add(iA)
        return pd.Series(sig, D.index)
    for n in range(1, len(ph)):
        iA, iB = ph[n - 1], ph[n]
        if not (5 <= iB - iA <= 60):
            continue
        A = a[iB]
        if abs(h[iA] - h[iB]) > 0.5 * A:
            continue
        trough = l[iA:iB + 1].min()
        if min(h[iA], h[iB]) - trough < 1.5 * A:
            continue
        top = max(h[iA], h[iB])
        if early:
            # anticipation: first red day closing under the second top's day low, still within 1 ATR of the top
            for i in range(iB + 1, min(len(D), iB + 6)):
                if h[i] > top:
                    break
                if c[i] < o[i] and c[i] < l[iB] and top - c[i] <= 1.5 * A:
                    sig[i] = True; break
        else:
            for i in range(iB + k, min(len(D), iB + 20)):
                if h[i] > top:
                    break
                if c[i] < trough:
                    sig[i] = True; break
    return pd.Series(sig, D.index)


def p_cross_10_50(D, retest=False):
    cross = (D.sma10 < D.sma50) & (D.sma10.shift() >= D.sma50.shift())
    if not retest:
        return cross.fillna(False)
    sig = np.zeros(len(D), bool)
    cv = cross.fillna(False).values
    h, c, s10, s50 = D.h.values, D.c.values, D.sma10.values, D.sma50.values
    for i in np.where(cv)[0]:
        for j in range(i + 1, min(len(D), i + 16)):
            if s10[j] >= s50[j]:
                break
            if h[j] >= s10[j] and c[j] < s10[j]:
                sig[j] = True; break
    return pd.Series(sig, D.index)


DAILY = {
    "bear flag (break of flag low)": lambda D: p_bear_flag(D),
    "bear flag (break of prior day low)": lambda D: p_bear_flag(D, trigger="pdl"),
    "bear flag, deep pole 4 ATR": lambda D: p_bear_flag(D, pole_atr=4.0),
    "red-green-green-red": lambda D: p_seq(D, "RGGR"),
    "red-green-green-red after 20-day high": lambda D: p_seq(D, "RGGR", "near_high"),
    "red-green-green-red under 20 SMA": lambda D: p_seq(D, "RGGR", "below_20"),
    "falling three (textbook)": lambda D: p_falling_three(D, True),
    "falling three (red, 3 greens, big red)": lambda D: p_falling_three(D, False),
    "sandwich (red, small green, big red)": lambda D: p_sandwich(D),
    "sandwich + 10 SMA under 20 SMA": lambda D: p_sandwich(D, True),
    "head and shoulders (neckline break)": lambda D: p_head_shoulders(D),
    "double top (break of middle low)": lambda D: p_double_top(D),
    "double top (early: red day off 2nd top)": lambda D: p_double_top(D, early=True),
    "daily 10 SMA crosses under 50 SMA": lambda D: p_cross_10_50(D),
    "daily 10/50 cross, first retest of 10 SMA": lambda D: p_cross_10_50(D, retest=True),
}


# =============== daily scoring ===============
def daily_outcomes(D, m5=None):
    """Per day i: outcomes of shorting at the NEXT session's open."""
    o, h, l, c, a = D.o.values, D.h.values, D.l.values, D.c.values, D.atr.values
    n = len(D)
    R = {}
    for k in (1, 3, 5, 10):
        r = np.full(n, np.nan)
        r[:n - k] = (o[1:n - k + 1] - c[k:n]) / o[1:n - k + 1] * 100
        R[f"ret_{k}d"] = r
        ra = np.full(n, np.nan)
        ra[:n - k] = (o[1:n - k + 1] - c[k:n]) / a[:n - k]
        R[f"atr_{k}d"] = ra
    win = np.full(n, np.nan)
    for i in range(n - 6):
        e, A = o[i + 1], a[i]
        res = 0.5
        for j in range(i + 1, i + 6):
            up, dn = h[j] >= e + A, l[j] <= e - A
            if up and dn:
                res = 0.0 if j == i + 1 else 0.5   # both in one day: unknown order, call it a loss on day 1
                break
            if dn:
                res = 1.0; break
            if up:
                res = 0.0; break
        win[i] = res
    R["win_1atr"] = win
    return pd.DataFrame(R, index=D.index)


def score(sig_rows, cols=("ret_1d", "ret_3d", "ret_5d", "ret_10d", "atr_3d", "atr_5d", "win_1atr")):
    """sig_rows: DataFrame with outcome columns + matching base_<col> columns + 'week'.
    Returns stats of (signal - baseline), clustered by week."""
    out = {"n": len(sig_rows), "names": sig_rows.sym.nunique() if "sym" in sig_rows else np.nan}
    for col in cols:
        x = (sig_rows[col] - sig_rows["base_" + col]).dropna()
        if len(x) < 5:
            out[col] = np.nan; out[col + "_t"] = np.nan; continue
        wk = sig_rows.loc[x.index, "week"]
        cl = x.groupby(wk).mean()
        se = cl.std(ddof=1) / np.sqrt(len(cl)) if len(cl) > 2 else np.nan
        out[col] = x.mean()
        out[col + "_t"] = cl.mean() / se if se and se > 0 else np.nan
        out[col + "_raw"] = sig_rows[col].mean()
    return out
