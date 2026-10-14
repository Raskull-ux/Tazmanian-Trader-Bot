"""Entry variants (fix being early) and exit rules (where to take it off / swing it to), for SHORT (put) trades.
Everything is in stock R: 1R = distance from entry to the technical stop."""
import numpy as np, pandas as pd
from . import lib

# ---------------- entries ----------------
ENTRIES = ["at_call", "reject_5m200", "hourly_20_retest", "hourly_20_50_cross", "break_prior_day_low",
           "m15_macd_cross", "failed_breakout", "next_open", "after_red_day"]


def find_entry(S, kind, t0, p0, window_sessions=3):
    """Returns (t_entry, p_entry) for the first time `kind` triggers after the call, within the window."""
    if kind == "at_call":
        return t0, p0
    s0 = S.session_of(t0 - pd.Timedelta(minutes=1)) or t0.normalize()
    i0 = S.sessions.searchsorted(s0)
    if i0 + window_sessions - 1 >= len(S.sessions):
        return None
    t_end = S.sessions[i0 + window_sessions - 1] + pd.Timedelta(hours=16)
    m5 = S.tf["m5"]
    W = m5[(m5.index > t0) & (m5.index <= t_end)]
    if len(W) == 0:
        return None
    if kind == "reject_5m200":
        # tested the 5-min 200 SMA (a high at/above it in the last 6 bars) then a 5-min close back under it
        X = m5[(m5.index > t0 - pd.Timedelta(hours=1)) & (m5.index <= t_end)]
        touch = (X.h >= X.sma200).rolling(6, min_periods=1).max().astype(bool)
        sig = touch & (X.c < X.sma200) & (X.index > t0)
        sig = sig & (X.c.shift() >= X.sma200.shift()) | (sig & (X.h >= X.sma200))
        k = np.where(sig.values)[0]
        return (X.index[k[0]], float(X.c.iloc[k[0]])) if len(k) else None
    if kind == "hourly_20_retest":
        H = S.tf["h1"]
        X = H[(H.index > t0) & (H.index <= t_end)]
        sig = (X.sma20 < X.sma50) & (X.h >= X.sma20) & (X.c < X.sma20)
        k = np.where(sig.values)[0]
        return (X.index[k[0]], float(X.c.iloc[k[0]])) if len(k) else None
    if kind == "hourly_20_50_cross":
        H = S.tf["h1"]
        X = H[(H.index > t0 - pd.Timedelta(hours=2)) & (H.index <= t_end)]
        sig = (X.sma20 < X.sma50) & (X.sma20.shift() >= X.sma50.shift()) & (X.index > t0)
        k = np.where(sig.values)[0]
        return (X.index[k[0]], float(X.c.iloc[k[0]])) if len(k) else None
    if kind == "break_prior_day_low":
        days = W.index.normalize()
        pdl = S.D.l.shift().reindex(days).values
        sig = W.c.values < pdl
        k = np.where(sig)[0]
        return (W.index[k[0]], float(W.c.iloc[k[0]])) if len(k) else None
    if kind == "m15_macd_cross":
        M = S.tf["m15"]
        X = M[(M.index > t0 - pd.Timedelta(minutes=30)) & (M.index <= t_end)]
        sig = (X.macd < X.macd_sig) & (X.macd.shift() >= X.macd_sig.shift()) & (X.index > t0)
        k = np.where(sig.values)[0]
        return (X.index[k[0]], float(X.c.iloc[k[0]])) if len(k) else None
    if kind == "failed_breakout":
        # price pushes above the call price, then closes back under it on the 5-min
        above = (W.h > p0 * 1.001).cummax()
        sig = above & (W.c < p0)
        k = np.where(sig.values)[0]
        return (W.index[k[0]], float(W.c.iloc[k[0]])) if len(k) else None
    if kind == "next_open":
        s1 = S.sessions[i0 + 1]
        X = S.m5[S.m5.index >= s1 + pd.Timedelta(minutes=570)]
        if len(X) == 0 or X.index[0].normalize() != s1:
            return None
        return s1 + pd.Timedelta(minutes=570), float(X.o.iloc[0])
    if kind == "after_red_day":
        for j in range(i0, i0 + window_sessions - 1):
            d = S.sessions[j]
            if d not in S.D.index:
                continue
            r = S.D.loc[d]
            if r.c < r.o:
                s1 = S.sessions[j + 1]
                X = S.m5[S.m5.index >= s1 + pd.Timedelta(minutes=570)]
                if len(X) and X.index[0].normalize() == s1:
                    return s1 + pd.Timedelta(minutes=570), float(X.o.iloc[0])
                return None
        return None
    raise ValueError(kind)


def stop_for(S, te, pe, atr):
    """Technical stop: highest high of the last hour of 5-min bars into the entry, a hair above.
    Kept between 0.25 and 2 ATR away."""
    m5 = S.tf["m5"]
    X = m5[(m5.index <= te) & (m5.index > te - pd.Timedelta(hours=1))]
    if len(X) == 0:
        X = m5[m5.index <= te].iloc[-12:]
    st = max(X.h.max(), pe) + 0.05 * atr
    st = min(max(st, pe + 0.25 * atr), pe + 2 * atr)
    return float(st)


# ---------------- exits ----------------
EXITS = ["level1", "level2", "level3", "half_L1_rest_L3", "day_close", "hourly_close_above_20", "daily_close_above_10",
         "hold_3_days", "hold_5_days"]


def simulate(S, te, pe, stop, levels, sessions=10):
    """Returns dict exit_rule -> (R, exit_time). Stop is checked before targets inside a bar (conservative).
    A gap through the stop exits at the bar open."""
    P = S.path(te, sessions)
    if len(P) < 5:
        return None
    risk = stop - pe
    if risk <= 0:
        return None
    o, h, l, c = P.o.values, P.h.values, P.l.values, P.c.values
    idx = P.index
    days = idx.normalize()
    ud = days.unique()
    sess_no = np.searchsorted(ud.values, days.values)
    stop_hit = np.where(h >= stop)[0]
    first_stop = stop_hit[0] if len(stop_hit) else len(P)
    out = {}

    def R(px):
        return (pe - px) / risk

    def stop_px(k):
        return max(o[k], stop) if o[k] > stop else stop

    lv = [p for p, _ in levels]
    for n, name in ((0, "level1"), (1, "level2"), (2, "level3")):
        if len(lv) <= n:
            out[name] = (np.nan, None); continue
        tgt = lv[n]
        hit = np.where((l <= tgt) & (sess_no < 5))[0]
        fh = hit[0] if len(hit) else len(P)
        if fh < first_stop:
            out[name] = (R(min(tgt, o[fh])), idx[fh])
        elif first_stop < len(P) and sess_no[first_stop] < 5:
            out[name] = (R(stop_px(first_stop)), idx[first_stop])
        else:
            k = np.where(sess_no < 5)[0][-1]
            out[name] = (R(c[k]), idx[k])
    # half at L1, stop to breakeven, rest at L3 (or L2 if only 2 levels)
    if len(lv) >= 2:
        t1, t3 = lv[0], lv[min(2, len(lv) - 1)]
        st, half = stop, None
        res = None
        for k in range(len(P)):
            if sess_no[k] >= 5:
                break
            if h[k] >= st:
                px = max(o[k], st) if o[k] > st else st
                res = (0.5 * half + 0.5 * R(px)) if half is not None else R(px)
                break
            if half is None and l[k] <= t1:
                half = R(min(t1, o[k])); st = pe
            if half is not None and l[k] <= t3:
                res = 0.5 * half + 0.5 * R(min(t3, o[k])); break
        if res is None:
            k = np.where(sess_no < 5)[0][-1]
            res = (0.5 * half + 0.5 * R(c[k])) if half is not None else R(c[k])
        out["half_L1_rest_L3"] = (res, None)
    else:
        out["half_L1_rest_L3"] = (np.nan, None)
    # day close
    k_end = np.where(sess_no == 0)[0]
    k_end = k_end[-1] if len(k_end) else 0
    out["day_close"] = (R(stop_px(first_stop)), idx[first_stop]) if first_stop <= k_end else (R(c[k_end]), idx[k_end])
    # hourly close above hourly 20 SMA (swing trail)
    H = S.tf["h1"]
    HX = H[(H.index > te) & (H.index <= idx[-1])]
    trig = HX.index[(HX.c > HX.sma20).values]
    t_tr = trig[0] if len(trig) else idx[-1]
    k_tr = int(np.searchsorted(idx.values, np.datetime64(t_tr), side="right") - 1)
    out["hourly_close_above_20"] = (R(stop_px(first_stop)), idx[first_stop]) if first_stop <= k_tr else (R(c[k_tr]), idx[k_tr])
    # daily close above daily 10 SMA (swing), max 10 sessions
    Dd = S.D
    k_d = len(P) - 1
    for j, d in enumerate(ud):
        if d in Dd.index:
            r = Dd.loc[d]
            if r.c > r.sma10:
                kk = np.where(sess_no == j)[0]
                k_d = kk[-1]
                break
    out["daily_close_above_10"] = (R(stop_px(first_stop)), idx[first_stop]) if first_stop <= k_d else (R(c[k_d]), idx[k_d])
    for n, name in ((3, "hold_3_days"), (5, "hold_5_days")):
        kk = np.where(sess_no < n)[0]
        k = kk[-1]
        out[name] = (R(stop_px(first_stop)), idx[first_stop]) if first_stop <= k else (R(c[k]), idx[k])
    # where the move actually went: lowest low before the stop, within 5 sessions
    lim = min(first_stop, np.where(sess_no < 5)[0][-1] + 1)
    out["_mfe_R"] = (R(l[:lim].min()) if lim > 0 else 0.0, None)
    out["_stopped"] = (float(first_stop < len(P) and sess_no[min(first_stop, len(P) - 1)] < 5), None)
    return out


def levels_reached(levels, low):
    """How many of the support levels the move reached."""
    return sum(1 for p, _ in levels if low <= p)
