"""
Taz deep dive: rebuild the intraday picture at every one of his 576 Robinhood trades (Apr 2024 - Apr 2026)
and find what separates winners from losers.

Data: results/entries_study/trades_features.csv (exact entry/exit minutes, real option returns) and the 5m bars
with extended hours from the data_ext branch (DATA_DIR, default data_ext/). 15m, 1h, 3h and 4h candles are built
from the 5m bars (clock aligned, extended hours). Daily candles are the regular session (9:30-16:00) built from
the same 5m bars so every timeframe uses one consistent, split-adjusted series.

Chart settings (HANDOFF): RSI 14 exponential (ewm span 14, adjust False, min_periods 14), ATR 14 Wilder
(ewm alpha 1/14), 8 EMA, SMAs 10/20/50/200, MACD 12/26/9.

Only bars that had CLOSED by the entry minute are used for momentum, MAs and counts. Price at entry/exit is the
5m bar containing that minute, interpolated open->close by minute (the exact fill is not in the data).

Win = option return > 0. Big win = 2x+ (return >= +100%). Fit = Apr 2024-Mar 2025, judged = Apr 2025-Apr 2026.
Percent returns only. Out: results/taz_deep_dive/REPORT.md, trades_rebuilt.csv
"""
from __future__ import annotations
import os, math
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data_ext")
OUT = "results/taz_deep_dive"; os.makedirs(OUT, exist_ok=True)
SPLIT = pd.Timestamp("2025-04-01")


# ------------------------------------------------------------------ indicators
def rsi(c):
    d = c.diff()
    g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean()
    return 100 - 100 / (1 + g / l)


def macd_hist(c):
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    s = m.ewm(span=9, adjust=False).mean()
    return m, s, m - s


def atr(x):
    tr = pd.concat([x.h - x.l, (x.h - x.c.shift()).abs(), (x.l - x.c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / 14, adjust=False).mean()


def td_counts(c):
    """TD setup: sell count = consecutive closes above the close 4 bars earlier; buy count = below. Restarts after 9."""
    up = (c > c.shift(4)).values; dn = (c < c.shift(4)).values
    su = np.zeros(len(c), int); sd = np.zeros(len(c), int)
    for i in range(len(c)):
        su[i] = (su[i - 1] % 9 + 1) if up[i] and i else 0
        sd[i] = (sd[i - 1] % 9 + 1) if dn[i] and i else 0
    return su, sd


def add_ind(x):
    x = x.copy()
    for n in (50, 200):
        x[f"s{n}"] = x.c.rolling(n).mean()
    x["rsi"] = rsi(x.c)
    _, _, x["mh"] = macd_hist(x.c)
    x["tds"], x["tdb"] = td_counts(x.c)
    x["v20"] = x.v.rolling(20).mean()
    return x


def resample(m5, kind):
    h = m5.t.dt.hour
    if kind == "15m":
        start = m5.t.dt.floor("15min"); span = pd.Timedelta(minutes=15)
    elif kind == "1h":
        start = m5.t.dt.floor("h"); span = pd.Timedelta(hours=1)
    elif kind == "4h":
        start = m5.t.dt.normalize() + pd.to_timedelta((h // 4) * 4, unit="h"); span = pd.Timedelta(hours=4)
    elif kind == "3h":
        m5 = m5[(h >= 4) & (h < 19 + 3)]
        h = m5.t.dt.hour
        start = m5.t.dt.normalize() + pd.to_timedelta(4 + 3 * ((h - 4) // 3), unit="h"); span = pd.Timedelta(hours=3)
    g = m5.groupby(start).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    g = g.reset_index().rename(columns={"index": "t"})
    g.columns = ["t", "o", "h", "l", "c", "v"]
    g["end"] = g.t + span
    return g


def daily_from_m5(m5):
    tm = m5.t.dt.hour * 60 + m5.t.dt.minute
    r = m5[(tm >= 570) & (tm < 960)]
    d = r.groupby(r.t.dt.normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    d.index.name = "date"
    d["atr"] = atr(d)
    d["e8"] = d.c.ewm(span=8, adjust=False).mean(); d["e10"] = d.c.ewm(span=10, adjust=False).mean()
    for n in (10, 20, 50, 200):
        d[f"s{n}"] = d.c.rolling(n).mean()
    d["rsi"] = rsi(d.c)
    d["macd"], d["sig"], _ = macd_hist(d.c)
    d["hh20"] = d.h.rolling(20).max(); d["r5"] = d.c.pct_change(5)
    return d


# ------------------------------------------------------------------ per-symbol cache
class Sym:
    def __init__(self, s):
        m5 = pd.read_parquet(f"{DATA}/m5/{s}.parquet").sort_values("t").reset_index(drop=True)
        m5 = m5[m5.t >= "2022-06-01"].reset_index(drop=True)   # enough history for every MA before Apr 2024
        for k in "ohlcv":
            m5[k] = m5[k].astype(float)
        self.m5 = add_ind(m5); self.m5["end"] = self.m5.t + pd.Timedelta(minutes=5)
        self.tf = {k: add_ind(resample(m5, k)) for k in ("15m", "1h", "4h", "3h")}
        self.d = daily_from_m5(m5)
        self.dates = self.d.index
        self.boxes = self._boxes()
        # weekly / monthly / 10-day candles (regular session daily)
        d = self.d
        self.w = d.groupby(d.index.to_period("W-FRI")).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
        self.mo = d.groupby(d.index.to_period("M")).agg(o=("o", "first"), c=("c", "last"))
        blk = np.arange(len(d)) // 10
        t10 = d.assign(b=blk).groupby("b").agg(c=("c", "last"), last=("c", lambda s: s.index[-1]), n=("c", "size"))
        t10["e10"] = t10.c.ewm(span=10, adjust=False).mean(); t10["s10"] = t10.c.rolling(10).mean()
        self.t10 = t10

    def _boxes(self):
        """Gray boxes: unfilled gaps between daily candle BODIES. A box is filled only when a later body covers it
        all the way through (wicks don't count). Returns, for each day i, the boxes still open after day i's close."""
        d = self.d; o, c = d.o.values, d.c.values
        bl, bh = np.minimum(o, c), np.maximum(o, c)
        open_boxes, snap = [], []
        for i in range(len(d)):
            open_boxes = [b for b in open_boxes if not (bl[i] <= b[0] and bh[i] >= b[1])]
            if i:
                if bl[i] > bh[i - 1]:
                    open_boxes.append((bh[i - 1], bl[i]))
                elif bh[i] < bl[i - 1]:
                    open_boxes.append((bh[i], bl[i - 1]))
            snap.append(list(open_boxes))
        return snap


def last_closed(df, T):
    """index of the last bar whose end <= T (or -1)."""
    return int(np.searchsorted(df.end.values, np.datetime64(T), side="right")) - 1


def price_at(m5, T):
    i = int(np.searchsorted(m5.t.values, np.datetime64(T), side="right")) - 1
    if i < 0:
        return np.nan, i
    r = m5.iloc[i]
    frac = min(max((T - r.t).total_seconds() / 300.0, 0), 1)
    return float(r.o + (r.c - r.o) * frac), i


# ------------------------------------------------------------------ features for one trade
def features(S: Sym, Q: Sym, tr):
    E, X = tr.E, tr.X
    D = E.normalize()
    f = {}
    if D not in S.dates:
        return None
    di = S.dates.get_loc(D)
    if di < 30:
        return None
    p = S.d.iloc[di - 1]; A = p.atr; prevC = p.c
    today = S.d.iloc[di]
    px, _ = price_at(S.m5, E)
    f["px"] = px; f["atr"] = A
    tmin = E.hour * 60 + E.minute
    f["min_after_open"] = tmin - 570
    f["premarket"] = tmin < 570

    m5 = S.m5
    day = m5[(m5.t >= D) & (m5.t < D + pd.Timedelta(days=1))]
    reg = day[(day.t.dt.hour * 60 + day.t.dt.minute >= 570) & (day.t.dt.hour * 60 + day.t.dt.minute < 960)]
    # ---------------- timing vs the day's high/low (hindsight: whole session)
    hod_i = reg.h.idxmax(); lod_i = reg.l.idxmin()
    f["hod_time"] = reg.t[hod_i]; f["hod"] = reg.h[hod_i]; f["lod"] = reg.l[lod_i]
    f["H_entry_before_hod"] = E < reg.t[hod_i] + pd.Timedelta(minutes=5) and E < reg.t[hod_i]
    f["H_hod_dist_atr"] = (reg.h[hod_i] - px) / A
    f["H_min_from_hod"] = (E - reg.t[hod_i]).total_seconds() / 60
    f["H_lod_dist_atr"] = (px - reg.l[lod_i]) / A
    f["H_hod_first30"] = reg.t[hod_i] < D + pd.Timedelta(minutes=600)
    f["H_entry_near_hod"] = f["H_hod_dist_atr"] <= 0.25
    # knowable: high so far (closed bars today incl. pre-market, plus the open of the current bar)
    so_far = day[day.end <= E]
    hi_sofar = max(so_far.h.max() if len(so_far) else -np.inf, px)
    f["dist_hi_sofar_atr"] = (hi_sofar - px) / A
    if len(so_far):
        f["min_since_hi_sofar"] = (E - so_far.t[so_far.h.idxmax()]).total_seconds() / 60 if so_far.h.max() >= px else 0.0
    else:
        f["min_since_hi_sofar"] = np.nan
    reg_sofar = reg[reg.end <= E]
    if len(reg_sofar) and tmin >= 600:
        f["hi_sofar_first30"] = bool(reg_sofar.t[reg_sofar.h.idxmax()] < D + pd.Timedelta(minutes=600))
    else:
        f["hi_sofar_first30"] = np.nan

    # ---------------- location
    f["vs_prevc_atr"] = (px - prevC) / A
    op = reg.o.iloc[0] if len(reg) else np.nan
    f["gap_pct"] = (op / prevC - 1) * 100
    f["vs_open_atr"] = (px - op) / A if tmin >= 570 else np.nan
    if len(reg_sofar):
        tp = (reg_sofar.h + reg_sofar.l + reg_sofar.c) / 3
        vwap = (tp * reg_sofar.v).sum() / max(reg_sofar.v.sum(), 1)
    else:
        vwap = np.nan
    f["vwap"] = vwap; f["vs_vwap_atr"] = (px - vwap) / A
    lev = {"prior close": prevC, "open": op if tmin >= 570 else np.nan, "VWAP": vwap,
           "yday high": p.h, "yday low": p.l, "d8e": p.e8, "d10": p.s10, "d50": p.s50, "d200": p.s200}
    for k, df in (("5m", S.m5), ("15m", S.tf["15m"]), ("1h", S.tf["1h"])):
        j = last_closed(df, E)
        r = df.iloc[j]
        lev[f"{k}50"] = r.s50; lev[f"{k}200"] = r.s200
        f[f"rsi_{k}"] = r.rsi; f[f"tds_{k}"] = r.tds; f[f"tdb_{k}"] = r.tdb
        h3 = df["mh"].values[j - 2:j + 1]
        f[f"macd_turn_dn_{k}"] = bool(h3[2] < h3[1] and h3[1] >= h3[0])
        f[f"macd_falling_{k}"] = bool(h3[2] < h3[1] < h3[0])
        f[f"macd_neg_{k}"] = bool(h3[2] < 0)
    for k, v in lev.items():
        f[f"vs_{k}_atr"] = (px - v) / A if v == v else np.nan
    # gray boxes open as of yesterday's close
    bx = S.boxes[di - 1]
    edges = [e for b in bx for e in b]
    if bx:
        inside = any(b[0] <= px <= b[1] for b in bx)
        dist = min(0 if b[0] <= px <= b[1] else min(abs(px - b[0]), abs(px - b[1])) for b in bx) / A
        above = [b for b in bx if b[0] > px]
        f["box_inside"] = inside; f["box_dist_atr"] = dist
        f["box_overhead_dist_atr"] = (min(b[0] for b in above) - px) / A if above else np.nan
        below = [b for b in bx if b[1] < px]
        f["box_below_dist_atr"] = (px - max(b[1] for b in below)) / A if below else np.nan
    else:
        f["box_inside"] = False; f["box_dist_atr"] = np.nan; f["box_overhead_dist_atr"] = np.nan; f["box_below_dist_atr"] = np.nan
    lv = [v for v in lev.values() if v == v] + edges
    f["stacked"] = int(sum(abs(px - v) <= 0.25 * A for v in lv))
    f["stacked_named"] = ", ".join(k for k, v in lev.items() if v == v and abs(px - v) <= 0.25 * A) + \
        (" + box edge" if any(abs(px - e) <= 0.25 * A for e in edges) else "")

    # ---------------- last 3 closed 5m candles
    j = last_closed(m5, E)
    c3 = m5.iloc[j - 2:j + 1]
    red = (c3.c < c3.o).values
    f["last_red"] = bool(red[-1]); f["red_of3"] = int(red.sum())
    last = c3.iloc[-1]; rng = max(last.h - last.l, 1e-9)
    f["upper_wick_pct"] = (last.h - max(last.o, last.c)) / rng
    f["lower_wick_pct"] = (min(last.o, last.c) - last.l) / rng
    f["lower_high"] = bool(c3.h.iloc[-1] < c3.h.iloc[-2])
    f["vol_ratio"] = last.v / last.v20 if last.v20 > 0 else np.nan

    # ---------------- day's shape
    if tmin >= 585 and len(reg) >= 3:
        f15 = reg.iloc[:3]
        f["first15_close_vs_prevc"] = "over" if f15.c.iloc[-1] > prevC else "under"
        f["first15_red"] = bool(f15.c.iloc[-1] < f15.o.iloc[0])
        f["first15_close_vs_d10"] = "over" if f15.c.iloc[-1] > p.s10 else "under"
    else:
        f["first15_close_vs_prevc"] = np.nan; f["first15_red"] = np.nan; f["first15_close_vs_d10"] = np.nan
    # QQQ at entry
    qd = Q.dates.get_loc(D) if D in Q.dates else None
    qpx, _ = price_at(Q.m5, E)
    if qd is not None:
        qprev = Q.d.c.iloc[qd - 1]
        qreg = Q.m5[(Q.m5.t >= D + pd.Timedelta(minutes=570)) & (Q.m5.end <= E)]
        f["qqq_vs_prevc_pct"] = (qpx / qprev - 1) * 100
        f["qqq_vs_open_pct"] = (qpx / Q.d.o.iloc[qd] - 1) * 100 if tmin >= 570 else np.nan
        if len(qreg):
            tp = (qreg.h + qreg.l + qreg.c) / 3
            f["qqq_under_vwap"] = bool(qpx < (tp * qreg.v).sum() / max(qreg.v.sum(), 1))
        else:
            f["qqq_under_vwap"] = np.nan
        f["qqq_rsi_5m"] = Q.m5.rsi.iloc[last_closed(Q.m5, E)]

    # ---------------- bigger picture (all from completed candles)
    d = S.d
    i = di - 1
    c, h, e8, s10, e10, AA = d.c.values, d.h.values, d.e8.values, d.s10.values, d.e10.values, d.atr.values
    pts = 2 * int(c[i] < e8[i])
    pts += int(h[i] >= min(e8[i], s10[i]) and c[i] < max(e8[i], s10[i]) and c[i - 1] < max(e8[i - 1], s10[i - 1]))
    pts += int(sum(abs(c[k] - s10[k]) <= 0.5 * AA[k] for k in range(i - 4, i + 1)) >= 3)
    pts += int(e10[i] < s10[i])
    qi = Q.dates.get_loc(d.index[i]) if d.index[i] in Q.dates else None
    if qi is not None:
        pts += int(d.r5.iloc[i] < Q.d.r5.iloc[qi])
    f["grade_pts"] = pts
    # monthly red: last month red AND this month so far red
    mp = D.to_period("M")
    mo = S.mo
    if (mp - 1) in mo.index and mp in mo.index:
        f["monthly_red"] = bool(mo.loc[mp - 1].c < mo.loc[mp - 1].o and px < mo.loc[mp].o)
    else:
        f["monthly_red"] = np.nan
    # weekly: 3 lower highs in a row on completed weeks
    wk = S.w[S.w.index < D.to_period("W-FRI")]
    wh = wk.h.values[-4:]
    f["weekly_3lh"] = bool(len(wh) == 4 and wh[3] < wh[2] < wh[1] < wh[0])
    # 10-day candles: 10 EMA under 10 SMA, crossed within the last 2 completed 10-day candles
    t10 = S.t10[(S.t10["last"] < D) & (S.t10.n == 10)]
    under = (t10.e10 < t10.s10).values
    f["tenday_under"] = bool(under[-1]) if len(under) else np.nan
    f["tenday_cross_recent"] = bool(len(under) >= 3 and under[-1] and not under[-3:].all())
    # 4h cliff diver in the last 10 trading days
    d10 = S.dates[max(di - 10, 0)]
    h4 = S.tf["4h"]
    w4 = h4[(h4.end > d10) & (h4.end <= E)]
    prev4 = h4.c.shift()
    lo = np.minimum(h4.s50, h4.s200)
    cliff = (h4.c < h4.o) & ((h4.o - h4.c) >= 0.5 * A) & (h4.c < lo) & (prev4 >= lo) & ((h4.s50 - h4.s200).abs() <= 0.5 * A)
    f["cliff_4h_10d"] = bool(cliff.loc[w4.index].any())
    h3 = S.tf["3h"]
    w3 = h3[(h3.end > d10) & (h3.end <= E)]
    f["rsi3h_90_10d"] = bool((w3.rsi >= 90).any())
    # MACD plateau (daily): MACD above 0, had been rising, now flat over 3 days
    mc = d.macd.values
    f["macd_plateau"] = bool(mc[i] > 0 and (mc[i - 3] - mc[i - 10]) > 0.2 * AA[i] and abs(mc[i] - mc[i - 3]) <= 0.05 * AA[i])
    f["near_20d_high"] = bool((d.hh20.iloc[i] - px) <= AA[i])
    f["daily_rsi"] = d.rsi.iloc[i]

    # ---------------- exit
    xp, _ = price_at(S.m5, X)
    f["exit_px"] = xp
    XD = X.normalize()
    xreg = m5[(m5.t >= XD + pd.Timedelta(minutes=570)) & (m5.t < XD + pd.Timedelta(minutes=960))]
    after = xreg[xreg.t >= X]
    if len(after):
        if tr.put:
            f["exit_left_atr"] = (xp - after.l.min()) / A; f["exit_left_pct"] = (xp / after.l.min() - 1) * 100
        else:
            f["exit_left_atr"] = (after.h.max() - xp) / A; f["exit_left_pct"] = (after.h.max() / xp - 1) * 100
    else:
        f["exit_left_atr"] = 0.0; f["exit_left_pct"] = 0.0
    if len(xreg):
        ext = xreg.l.min() if tr.put else xreg.h.max()
        f["exit_near_day_extreme"] = bool(abs(xp - ext) <= 0.25 * A)
        f["exit_before_day_extreme"] = bool(X < xreg.t[xreg.l.idxmin() if tr.put else xreg.h.idxmax()])
    f["stock_move_atr"] = (px - xp) / A * (1 if tr.put else -1)
    return f


# ------------------------------------------------------------------ report helpers
def pct(x):
    return "-" if x != x else f"{x*100:.0f}%"


def z2(a_w, a_n, b_w, b_n):
    if min(a_n, b_n) == 0:
        return 0.0
    p = (a_w + b_w) / (a_n + b_n)
    se = math.sqrt(max(p * (1 - p) * (1 / a_n + 1 / b_n), 1e-12))
    return (a_w / a_n - b_w / b_n) / se


def bucket_table(T, col, bins, labels, title, note=""):
    t = T.copy()
    t["b"] = pd.cut(t[col], bins=bins, labels=labels, right=False)
    rows = ["", f"### {title}", note, "",
            "| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |",
            "|---|---|---|---|---|---|---|---|"]
    for b in labels:
        a = t[(t.b == b) & (t.half == "fit")]; j = t[(t.b == b) & (t.half == "judged")]; al = t[t.b == b]
        if len(al) == 0:
            continue
        rows.append(f"| {b} | {len(a)} | {pct(a.win.mean()) if len(a) else '-'} | {pct(a.big.mean()) if len(a) else '-'} | "
                    f"{len(j)} | {pct(j.win.mean()) if len(j) else '-'} | {pct(j.big.mean()) if len(j) else '-'} | "
                    f"{al.ret.median()*100:+.0f}% |")
    return rows


def cat_table(T, col, title, order=None, note=""):
    rows = ["", f"### {title}", note, "",
            "| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |",
            "|---|---|---|---|---|---|---|---|"]
    vals = order or [v for v in T[col].dropna().unique()]
    for v in vals:
        a = T[(T[col] == v) & (T.half == "fit")]; j = T[(T[col] == v) & (T.half == "judged")]; al = T[T[col] == v]
        if len(al) == 0:
            continue
        rows.append(f"| {v} | {len(a)} | {pct(a.win.mean()) if len(a) else '-'} | {pct(a.big.mean()) if len(a) else '-'} | "
                    f"{len(j)} | {pct(j.win.mean()) if len(j) else '-'} | {pct(j.big.mean()) if len(j) else '-'} | "
                    f"{al.ret.median()*100:+.0f}% |")
    return rows


# ------------------------------------------------------------------ main
def main():
    tr = pd.read_csv("results/entries_study/trades_features.csv")
    tr["E"] = pd.to_datetime(tr["Entry Time"]); tr["X"] = pd.to_datetime(tr["Exit Time"])
    tr["put"] = tr.Type.eq("Put")
    cache = {}
    Q = cache.setdefault("QQQ", Sym("QQQ"))
    rows = []
    for k, t in tr.iterrows():
        s = t.Symbol
        if s not in cache:
            print("loading", s, flush=True); cache[s] = Sym(s)
        f = features(cache[s], Q, t)
        if f is None:
            print("skip", s, t.E); continue
        f.update(idx=k, sym=s, type=t.Type, E=t.E, X=t.X, ret=t.ret, hold_h=t["Hold (hrs)"], strike=t.Strike,
                 expiry=t.Expiry, dte=t.dte)
        rows.append(f)
    T = pd.DataFrame(rows)
    T["win"] = T.ret > 0; T["big"] = T.ret >= 1.0
    T["half"] = np.where(T.E < SPLIT, "fit", "judged")
    T["daytrade"] = T.E.dt.normalize() == T.X.dt.normalize()
    T.to_csv(f"{OUT}/trades_rebuilt.csv", index=False)
    write_report(T)


def conditions(P):
    """Binary conditions (puts view). Prefix H = hindsight (not knowable at entry), B = his behavior after entry."""
    m = P.min_after_open
    C = {
        "Entered in the first 5 minutes (9:30-9:34)": (m >= 0) & (m < 5),
        "Entered in the first 15 minutes": (m >= 0) & (m < 15),
        "Entered 15-60 minutes after the open": (m >= 15) & (m < 60),
        "Entered 1 hour+ after the open": m >= 60,
        "Entered 2 hours+ after the open": m >= 120,
        "Price above the prior close": P.vs_prevc_atr > 0,
        "Gapped up 0.3%+": P.gap_pct >= 0.3,
        "Gapped down 0.3%+": P.gap_pct <= -0.3,
        "Price above the open": P.vs_open_atr > 0,
        "Price above VWAP": P.vs_vwap_atr > 0,
        "Price 0.5 ATR+ above VWAP": P.vs_vwap_atr >= 0.5,
        "Above the 5m 50": P["vs_5m50_atr"] > 0, "Above the 5m 200": P["vs_5m200_atr"] > 0,
        "Above the 15m 50": P["vs_15m50_atr"] > 0, "Above the 15m 200": P["vs_15m200_atr"] > 0,
        "Above the 1h 50": P["vs_1h50_atr"] > 0, "Above the 1h 200": P["vs_1h200_atr"] > 0,
        "Above the daily 8 EMA": P.vs_d8e_atr > 0, "Above the daily 10 SMA": P.vs_d10_atr > 0,
        "Above the daily 50": P.vs_d50_atr > 0, "Above the daily 200": P.vs_d200_atr > 0,
        "Within 0.25 ATR of yesterday's high": P["vs_yday high_atr"].abs() <= 0.25,
        "Above yesterday's high": P["vs_yday high_atr"] > 0,
        "Below yesterday's low": P["vs_yday low_atr"] < 0,
        "Inside or within 0.25 ATR of an unfilled gray box": P.box_dist_atr <= 0.25,
        "Unfilled box overhead within 0.5 ATR": P.box_overhead_dist_atr <= 0.5,
        "3+ levels stacked within 0.25 ATR": P.stacked >= 3,
        "5+ levels stacked within 0.25 ATR": P.stacked >= 5,
        "Within 0.25 ATR of the high so far": P.dist_hi_sofar_atr <= 0.25,
        "1 ATR+ under the high so far (chasing lower)": P.dist_hi_sofar_atr >= 1,
        "5m RSI 70+": P.rsi_5m >= 70, "5m RSI 60+": P.rsi_5m >= 60, "5m RSI under 40": P.rsi_5m < 40,
        "15m RSI 70+": P.rsi_15m >= 70, "15m RSI 60+": P.rsi_15m >= 60, "15m RSI under 40": P.rsi_15m < 40,
        "5m TD sell count 7-9": P.tds_5m >= 7, "15m TD sell count 7-9": P.tds_15m >= 7, "1h TD sell count 7-9": P.tds_1h >= 7,
        "5m TD buy count 5+ (already falling)": P.tdb_5m >= 5, "15m TD buy count 5+": P.tdb_15m >= 5,
        "5m MACD histogram just turned down": P.macd_turn_dn_5m, "15m MACD histogram just turned down": P.macd_turn_dn_15m,
        "5m MACD histogram falling 2 bars": P.macd_falling_5m, "15m MACD histogram falling 2 bars": P.macd_falling_15m,
        "5m MACD histogram below 0": P.macd_neg_5m, "15m MACD histogram below 0": P.macd_neg_15m,
        "Last 5m candle red": P.last_red, "2+ of last 3 5m candles red": P.red_of3 >= 2,
        "Last 5m candle upper wick 40%+ of range": P.upper_wick_pct >= 0.4,
        "Last 5m candle made a lower high": P.lower_high,
        "Last 5m volume 1.5x+ the 20-bar average": P.vol_ratio >= 1.5,
        "First 15m candle closed back under the prior close": P.first15_close_vs_prevc == "under",
        "First 15m candle red": P.first15_red == True,
        "First 15m candle closed under the daily 10 SMA": P.first15_close_vs_d10 == "under",
        "High so far was set in the first 30 min": P.hi_sofar_first30 == True,
        "QQQ red vs prior close at entry": P.qqq_vs_prevc_pct < 0,
        "QQQ red from the open at entry": P.qqq_vs_open_pct < 0,
        "QQQ under its VWAP": P.qqq_under_vwap == True,
        "Daily grade B or better (4+/6)": P.grade_pts >= 4, "Daily grade A/A- (5+/6)": P.grade_pts >= 5,
        "Monthly red (last month and this month so far)": P.monthly_red == True,
        "3 weekly lower highs": P.weekly_3lh,
        "10-day chart 10 EMA under 10 SMA": P.tenday_under == True,
        "10-day chart 10 EMA crossed under 10 SMA within 2 candles": P.tenday_cross_recent,
        "4h cliff diver in the last 10 days": P.cliff_4h_10d,
        "3h RSI 90 in the last 10 days": P.rsi3h_90_10d,
        "Daily MACD plateau": P.macd_plateau,
        "Within 1 ATR of the 20-day high": P.near_20d_high,
        "Daily RSI 70+": P.daily_rsi >= 70,
        "H: Entered before the day's high printed": P.H_entry_before_hod,
        "H: Entered within 0.25 ATR of the day's high": P.H_entry_near_hod,
        "H: Day's high printed in the first 30 min": P.H_hod_first30,
        "B: Day trade (sold same day)": P.daytrade,
        "B: Held under 1 hour": P.hold_h < 1,
    }
    # evaluable mask: conditions needing a later-in-day entry are only judged on trades where they can be known
    need = {"First 15m candle closed back under the prior close": P.min_after_open >= 15,
            "First 15m candle red": P.min_after_open >= 15,
            "First 15m candle closed under the daily 10 SMA": P.min_after_open >= 15,
            "High so far was set in the first 30 min": P.min_after_open >= 30,
            "Price above VWAP": P.min_after_open >= 5, "Price 0.5 ATR+ above VWAP": P.min_after_open >= 5,
            "Price above the open": P.min_after_open >= 0, "QQQ red from the open at entry": P.min_after_open >= 0,
            "QQQ under its VWAP": P.min_after_open >= 5}
    return C, need


def score(P, C, need, outcome="win"):
    out = []
    for name, cond in C.items():
        ok = need.get(name, pd.Series(True, index=P.index)) & cond.notna()
        cond = cond.fillna(False).astype(bool)
        r = {"cond": name}
        for hf in ("fit", "judged"):
            sub = P[ok & (P.half == hf)]; cc = cond[sub.index]
            y, n = sub[outcome][cc], sub[outcome][~cc]
            r[f"{hf}_n1"], r[f"{hf}_n0"] = len(y), len(n)
            r[f"{hf}_p1"] = y.mean() if len(y) else np.nan; r[f"{hf}_p0"] = n.mean() if len(n) else np.nan
            r[f"{hf}_z"] = z2(y.sum(), len(y), n.sum(), len(n))
            r[f"{hf}_med1"] = sub.ret[cc].median() if len(y) else np.nan
            r[f"{hf}_med0"] = sub.ret[~cc].median() if len(n) else np.nan
        out.append(r)
    return pd.DataFrame(out)


def write_report(T):
    P = T[T.type == "Put"].copy(); Cl = T[T.type == "Call"].copy()
    C, need = conditions(P)
    S = score(P, C, need, "win"); S2 = score(P, C, need, "big")
    S["fit_diff"] = S.fit_p1 - S.fit_p0; S["judged_diff"] = S.judged_p1 - S.judged_p0
    S2["fit_diff"] = S2.fit_p1 - S2.fit_p0; S2["judged_diff"] = S2.judged_p1 - S2.judged_p0
    S.to_csv(f"{OUT}/condition_scores.csv", index=False)
    elig = S[(S.fit_n1 >= 20) & (S.fit_n0 >= 20)].copy()
    elig["rank_fit"] = elig.fit_z.abs().rank(ascending=False)
    elig = elig.sort_values("rank_fit")
    elig["held"] = (np.sign(elig.fit_diff) == np.sign(elig.judged_diff)) & (elig.judged_diff.abs() >= 0.05) & \
                   (elig.judged_n1 >= 15) & (elig.judged_n0 >= 15)
    knowable = elig[~elig.cond.str.startswith(("H:", "B:"))].copy()
    knowable["rank_fit"] = np.arange(1, len(knowable) + 1)
    top_fit = knowable.head(20)
    strict = knowable[(knowable.fit_z.abs() >= 1.5) & knowable.held]
    final = knowable[(knowable.fit_z.abs() >= 1.0) & knowable.held].head(5)

    L = ["# Taz's own trades: deep dive", "",
         f"{len(T)} of 576 trades rebuilt from the 5-minute bars with extended hours ({len(P)} puts, {len(Cl)} calls), "
         f"{T.E.min():%b %d %Y} to {T.E.max():%b %d %Y}.",
         "Every number is a percent or a count. Option returns are his real fills (exit / entry - 1). No dollar P&L anywhere.", "",
         "**How to read this**",
         "- **Win** = option return above 0. **2x+** = option return of +100% or more.",
         "- **Fit period** = Apr 2024 to Mar 2025 (conditions were ranked here). **Judged period** = Apr 2025 to Apr 2026 "
         "(only used to check; nothing was picked here).",
         "- Everything is measured from bars that had **already closed** at his entry minute, so it is what he could have seen. "
         "Rows marked **H:** use the rest of the day (hindsight) and rows marked **B:** are his own behavior after entry; "
         "both are shown for understanding but are kept out of the checklist.",
         "- The main study is his **puts** (" + str(len(P)) + " trades, 91% of everything). All the trend clues are bearish by "
         "definition, so the " + str(len(Cl)) + " calls get their own short section at the end.",
         "- ATR = daily ATR 14 (Wilder) as of the prior close. Levels: daily candles are the regular session; 5m/15m/1h MAs include extended hours.", ""]
    fp, jp = P[P.half == "fit"], P[P.half == "judged"]
    L += ["## Baseline (puts)", "",
          "| Period | Puts | Win rate | 2x+ rate | Median option return |", "|---|---|---|---|---|",
          f"| Fit (Apr 2024-Mar 2025) | {len(fp)} | {pct(fp.win.mean())} | {pct(fp.big.mean())} | {fp.ret.median()*100:+.0f}% |",
          f"| Judged (Apr 2025-Apr 2026) | {len(jp)} | {pct(jp.win.mean())} | {pct(jp.big.mean())} | {jp.ret.median()*100:+.0f}% |",
          f"| All | {len(P)} | {pct(P.win.mean())} | {pct(P.big.mean())} | {P.ret.median()*100:+.0f}% |", ""]

    # ---------------- plain-English summary and checklist (numbers computed here, words written after reading them)
    def wr(mask, hf, col="win"):
        x = P[mask.fillna(False).astype(bool) & (P.half == hf)]
        return f"{pct(x[col].mean())} (n {len(x)})" if len(x) else "-"
    nb = P[["monthly_red", "weekly_3lh", "cliff_4h_10d"]].fillna(False).astype(bool).sum(axis=1)
    lh = P.lower_high.astype(bool)
    near = P.H_entry_near_hod.astype(bool); f30 = P.H_hod_first30.astype(bool)
    early_before = P.H_min_from_hod <= -60; just_after = (P.H_min_from_hod >= 0) & (P.H_min_from_hod < 15)
    u1 = P.hold_h < 1; multi = P.hold_h >= 30
    nr20 = P.near_20d_high.astype(bool)
    allm = pd.Series(True, index=P.index)
    L += ["## Plain-English summary", "",
          f"His puts won {pct(fp.win.mean())} of the time in the fit year and {pct(jp.win.mean())} in the judged year. "
          "Almost nothing about the 5-minute picture (RSI, TD count, MACD, VWAP, the moving averages, the gap, QQQ, how many levels were stacked) "
          "separated winners from losers in a way that held in both years: those flipped sign from one year to the next. "
          "What held is simple: **he wins when the bigger trend has already broken and he shorts the actual top of the day, "
          "and he loses when he shorts a stock that is still going up.**", "",
          "**What held in both years (knowable at entry):**", "",
          f"1. **The bigger trend was already broken.** Monthly red (last month red and this month red so far), 3 weekly lower highs in a row, "
          f"or a 4h cliff diver in the last 10 days. Puts with at least one of these won {wr(nb >= 1, 'fit')} in the fit year and "
          f"{wr(nb >= 1, 'judged')} in the judged year, vs {wr(nb == 0, 'fit')} and {wr(nb == 0, 'judged')} with none. "
          f"With 2 or more: {wr(nb >= 2, 'fit')} and {wr(nb >= 2, 'judged')} (very few trades). Only about 1 in 4 of his puts had any of them.",
          f"2. **The last closed 5m candle made a lower high.** Won {wr(lh, 'fit')} / {wr(lh, 'judged')} vs "
          f"{wr(~lh, 'fit')} / {wr(~lh, 'judged')} without it.",
          f"3. Both together (at least one broken clue plus a 5m lower high): {wr((nb >= 1) & lh, 'fit')} / {wr((nb >= 1) & lh, 'judged')}. "
          f"Neither: {wr((nb == 0) & ~lh, 'fit')} / {wr((nb == 0) & ~lh, 'judged')}.", "",
          "**The biggest difference is timing, and it is hindsight** (you only know the day's high after the close, but it says what his winners look like):", "",
          f"- Entered within 0.25 ATR of the day's eventual high: won {wr(near, 'fit')} / {wr(near, 'judged')}. Everything else: "
          f"{wr(~near, 'fit')} / {wr(~near, 'judged')}.",
          f"- Entered in the 15 minutes after the day's high printed: {wr(just_after, 'fit')} / {wr(just_after, 'judged')}. "
          f"Entered 60+ minutes BEFORE the day's high (shorting while it was still going up): {wr(early_before, 'fit')} / {wr(early_before, 'judged')}.",
          f"- Days where the high printed in the first 30 minutes: {wr(f30, 'fit')} / {wr(f30, 'judged')}. Days where it printed later: "
          f"{wr(~f30, 'fit')} / {wr(~f30, 'judged')}.", "",
          "**How long he held (his behavior, held in both years):**", "",
          f"- Sold within the hour: {wr(u1, 'fit')} / {wr(u1, 'judged')}. Held 2+ days: {wr(multi, 'fit')} / {wr(multi, 'judged')}. "
          "Part of this is cause and effect running backwards (winners hit target fast, losers get held hoping), but it matches the old finding "
          "that his overnight holds bleed.", "",
          "**What did NOT hold (do not use these as reasons to enter):** price above or below VWAP, the open, the prior close, the 5m/15m/1h 50 and 200, "
          "the daily 8 EMA/10/50/200; 5m and 15m RSI; TD counts; MACD turning; volume; gap size; what QQQ was doing; the daily grade "
          "(B or better won 13% in the fit year and 44% in the judged year); levels stacked (83% of all his entries already had 3+ levels within 0.25 ATR, "
          f"so it does not separate anything). Being within 1 ATR of the 20-day high was fine in the fit year and bad in the judged year "
          f"({wr(nr20, 'fit')} / {wr(nr20, 'judged')} vs {wr(~nr20, 'fit')} / {wr(~nr20, 'judged')} away from it).", "",
          "**2x+ winners:** no condition separated 2x+ trades in both years. Every lean in the fit year (above the 5m 200, 15m RSI 60+, near the high so far) "
          "reversed in the judged year. 2x+ trades are too rare (" + f"{int(fp.big.sum())} and {int(jp.big.sum())}) to build a rule on.", "",
          "**Exits:** on winners he left a median of about 0.2 ATR (roughly 0.4% of the stock) on the table to that day's low, and about half his winners "
          "were sold before the day's low printed. Same-day exits leave little on the table; the leak is the entry (shorting the climb) and holding for days.", "",
          "### Winning profile", "",
          "A put on a name whose bigger trend is already broken (month red, weekly lower highs, a recent 4h cliff dive). The day's high prints early, "
          "usually in the first 30 minutes. He enters within a quarter ATR of that high, right after it prints, on a 5m candle that made a lower high, "
          "and he is out the same session, often inside the hour.", "",
          "### Losing profile", "",
          "A put on a stock with its trend intact (no broken clue), often near its 20-day high. He shorts while it is still making new highs: "
          "the day's high comes an hour or more after his entry. The 5m candle at entry is still making higher highs. He then holds it overnight "
          "or for 2 to 3 days.", "",
          "## Taz's A+ setup (only what held in both years)", "",
          "| # | Check | Fit year win rate | Judged year win rate |", "|---|---|---|---|",
          f"| 1 | **Trend already broken**: at least one of monthly red (last month red and this month red so far), 3 weekly lower highs in a row, "
          f"a 4h cliff diver in the last 10 trading days. Two or more = A+. | {wr(nb >= 1, 'fit')}; 2+: {wr(nb >= 2, 'fit')} | "
          f"{wr(nb >= 1, 'judged')}; 2+: {wr(nb >= 2, 'judged')} |",
          f"| 2 | **Trigger**: wait for a closed 5m candle that makes a lower high. No lower high, no entry. | {wr(lh, 'fit')} | {wr(lh, 'judged')} |",
          f"| 3 | **Short the top, not the climb**: the day's high has printed (it held when it printed in the first 30 minutes) and you are within "
          f"0.25 ATR of it. If it is still making new highs, wait. (Built from the hindsight table; the live version is check 2.) | "
          f"{wr(near, 'fit')} | {wr(near, 'judged')} |",
          f"| 4 | **Get paid the same session.** Puts sold inside the hour won {wr(u1, 'fit')} / {wr(u1, 'judged')}; 2+ day holds won "
          f"{wr(multi, 'fit')} / {wr(multi, 'judged')}. | | |",
          f"| | **All of 1 and 2 together** | {wr((nb >= 1) & lh, 'fit')} | {wr((nb >= 1) & lh, 'judged')} |",
          f"| | Baseline (every put) | {wr(allm, 'fit')} | {wr(allm, 'judged')} |", "",
          "**Do not count as a reason:** RSI level, TD count, MACD turn, VWAP, which MA it is above, gap size, QQQ direction, daily grade, "
          "number of stacked levels. None of them held in both years.", "",
          "**Honest limits:** 24 months, one trader, one account. The broken-trend clues are each on only 20 to 40 puts per year, "
          "so a 10-point gap could still be luck (z-scores 0.8 to 2.1). The direction matches the HANDOFF notes on his trades; results/broken_vs_strength tests the same clues market-wide. "
          "Forward-log every A+ trade before trusting it with size.", ""]

    # ---------------- the answer first
    L += ["## The detail: conditions ranked on the fit year, checked on the judged year", "",
          "Ranked on the fit period only (strength of the win-rate gap, z-score, at least 20 trades on each side), "
          "then checked on the judged period. **Held** = same direction in the judged period, gap of 5+ points, 15+ trades each side.", "",
          "| Rank | Condition (knowable at entry) | Fit: win with / without (n) | Fit z | Judged: win with / without (n) | Judged z | Held? |",
          "|---|---|---|---|---|---|---|"]
    for _, r in top_fit.iterrows():
        L.append(f"| {int(r.rank_fit)} | {r.cond} | {pct(r.fit_p1)} / {pct(r.fit_p0)} ({r.fit_n1}/{r.fit_n0}) | {r.fit_z:+.1f} | "
                 f"{pct(r.judged_p1)} / {pct(r.judged_p0)} ({r.judged_n1}/{r.judged_n0}) | {r.judged_z:+.1f} | {'YES' if r.held else 'no'} |")
    L += ["", f"At a strict bar (fit z 1.5+) only {len(strict)} held: " + ", ".join(strict.cond) + ". "
          "To get the 3 to 5 the brief asks for, the bar was lowered to fit z 1.0+ (still ranked on the fit period only). "
          "The extra ones are weaker and rest on 20 to 40 trades each.", "",
          "**The ones that held in both halves (used for the checklist):**", ""]
    for _, r in final.iterrows():
        side = "helps" if r.fit_diff > 0 else "hurts"
        L.append(f"- **{r.cond}** {side}: fit {pct(r.fit_p1)} vs {pct(r.fit_p0)}, judged {pct(r.judged_p1)} vs {pct(r.judged_p0)}.")
    if not len(final):
        L.append("- None held at the bar set above.")
    # stacked count of the held conditions
    if len(final):
        good = [C[c].fillna(False).astype(bool) if d > 0 else ~C[c].fillna(False).astype(bool)
                for c, d in zip(final.cond, final.fit_diff)]
        P["score"] = sum(g.astype(int) for g in good)
        L += ["", "**Stacking them** (how many of the held conditions lined up on the right side):", "",
              "| Count lined up | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |", "|---|---|---|---|---|---|---|---|"]
        for k in range(len(final) + 1):
            a = P[(P.score == k) & (P.half == "fit")]; j = P[(P.score == k) & (P.half == "judged")]; al = P[P.score == k]
            if len(al):
                L.append(f"| {k} of {len(final)} | {len(a)} | {pct(a.win.mean()) if len(a) else '-'} | {pct(a.big.mean()) if len(a) else '-'} | "
                         f"{len(j)} | {pct(j.win.mean()) if len(j) else '-'} | {pct(j.big.mean()) if len(j) else '-'} | {al.ret.median()*100:+.0f}% |")
        T.loc[P.index, "score"] = P.score
        T.to_csv(f"{OUT}/trades_rebuilt.csv", index=False)

    # 2x+ view
    e2 = S2[(S2.fit_n1 >= 20) & (S2.fit_n0 >= 20) & ~S2.cond.str.startswith(("H:", "B:"))].copy()
    e2 = e2.reindex(e2.fit_z.abs().sort_values(ascending=False).index).head(10)
    L += ["", "### Same ranking for 2x+ winners", "",
          "2x+ trades are rare (" + f"{int(fp.big.sum())} in the fit period, {int(jp.big.sum())} in the judged period), so treat this as a lean.", "",
          "| Condition | Fit: 2x+ with / without (n) | Fit z | Judged: 2x+ with / without (n) | Judged z |", "|---|---|---|---|---|"]
    for _, r in e2.iterrows():
        L.append(f"| {r.cond} | {pct(r.fit_p1)} / {pct(r.fit_p0)} ({r.fit_n1}/{r.fit_n0}) | {r.fit_z:+.1f} | "
                 f"{pct(r.judged_p1)} / {pct(r.judged_p0)} ({r.judged_n1}/{r.judged_n0}) | {r.judged_z:+.1f} |")

    # ---------------- post-hoc: knowable version of the strongest hindsight finding
    jt = (P.dist_hi_sofar_atr <= 0.25) & (P.min_since_hi_sofar <= 15) & (P.min_since_hi_sofar > 0) & P.lower_high
    P["jt"] = np.where(jt, "high so far printed 5-15 min ago, within 0.25 ATR of it, last 5m candle a lower high", "everything else")
    L += ["", "### Follow-up added after seeing the data (not used for the checklist)", "",
          "The strongest thing in the whole study is hindsight: his winners were entered right at the day's high "
          "(see section 1). This checks a version he could see live: the high of the day so far printed in the last 15 minutes, "
          "price is still within 0.25 ATR of it, and the last 5m candle made a lower high. It was designed after looking at both "
          "halves, so it is a lead to forward-test, not a proven rule."]
    L += cat_table(P, "jt", "Just topped, knowable at entry", [P.jt[jt].iloc[0] if jt.any() else "", "everything else"])

    # ---------------- detail sections
    L += ["", "## 1. Timing"]
    L += bucket_table(P, "min_after_open", [-1000, 0, 5, 15, 30, 60, 120, 240, 1000],
                      ["pre-market", "0-5 min", "5-15 min", "15-30 min", "30-60 min", "1-2 h", "2-4 h", "last 2 h"],
                      "Minutes after the open at entry")
    P["hodside"] = np.where(P.H_entry_before_hod, "before the day's high (it went higher after)", "after the day's high")
    L += cat_table(P, "hodside", "Entry before or after the day's high (H)")
    L += bucket_table(P, "H_hod_dist_atr", [-10, 0.25, 0.5, 1, 2, 100], ["within 0.25 ATR", "0.25-0.5", "0.5-1", "1-2", "2+ ATR"],
                      "Entry distance under the day's eventual high, in ATR (H)")
    L += bucket_table(P, "H_min_from_hod", [-1000, -60, -15, 0, 15, 60, 1000],
                      ["60+ min before the high", "15-60 before", "0-15 before", "0-15 after", "15-60 after", "60+ min after"],
                      "Minutes from the day's high to his entry (H)")
    P["dtl"] = np.where(P.daytrade, "day trade (sold same day)", "overnight swing")
    L += cat_table(P, "dtl", "Day trade vs overnight swing (B)")
    L += bucket_table(P, "hold_h", [0, 0.25, 1, 3, 7, 30, 80, 10000],
                      ["under 15 min", "15-60 min", "1-3 h", "3 h to close", "1 night", "2-3 days", "4+ days"], "Results by hold length (B)")

    L += ["", "## 2. Location"]
    L += bucket_table(P, "vs_prevc_atr", [-100, -1, -0.25, 0.25, 1, 100], ["1+ ATR under", "0.25-1 under", "at it (+/-0.25)", "0.25-1 over", "1+ ATR over"],
                      "Price vs the prior close (ATR)")
    L += bucket_table(P, "gap_pct", [-100, -1, -0.3, 0.3, 1, 100], ["gap down 1%+", "gap down 0.3-1%", "flat", "gap up 0.3-1%", "gap up 1%+"], "The gap")
    L += bucket_table(P, "vs_open_atr", [-100, -0.5, 0, 0.5, 100], ["0.5+ ATR under the open", "0-0.5 under", "0-0.5 over", "0.5+ over"], "Price vs the open")
    L += bucket_table(P, "vs_vwap_atr", [-100, -0.5, 0, 0.5, 100], ["0.5+ ATR under VWAP", "0-0.5 under", "0-0.5 over", "0.5+ over"], "Price vs VWAP")
    for k, nm in (("5m50", "5m 50"), ("5m200", "5m 200"), ("15m50", "15m 50"), ("15m200", "15m 200"), ("1h50", "1h 50"), ("1h200", "1h 200"),
                  ("d8e", "daily 8 EMA"), ("d10", "daily 10 SMA"), ("d50", "daily 50"), ("d200", "daily 200"),
                  ("yday high", "yesterday's high"), ("yday low", "yesterday's low")):
        L += bucket_table(P, f"vs_{k}_atr", [-100, -0.25, 0.25, 100], ["under (0.25+ ATR)", "at it (+/-0.25 ATR)", "over (0.25+ ATR)"], f"Price vs the {nm}")
    L += bucket_table(P, "box_dist_atr", [0, 0.0001, 0.25, 1, 100], ["inside a box", "within 0.25 ATR", "0.25-1 ATR", "1+ ATR away"],
                      "Nearest unfilled gray box (daily, bodies only)")
    L += bucket_table(P, "box_overhead_dist_atr", [0, 0.25, 1, 100], ["box bottom within 0.25 ATR above", "0.25-1 ATR above", "1+ ATR above"],
                      "Nearest unfilled box ABOVE price (resistance a put would fade)")
    L += bucket_table(P, "stacked", [0, 1, 2, 3, 4, 6, 100], ["0", "1", "2", "3", "4-5", "6+"], "Levels stacked within 0.25 ATR of his entry",
                      "Levels counted: prior close, open, VWAP, yesterday's high and low, 5m/15m/1h 50 and 200, daily 8 EMA/10/50/200, every unfilled box edge.")

    L += ["", "## 3. Momentum"]
    for k in ("5m", "15m"):
        L += bucket_table(P, f"rsi_{k}", [0, 30, 40, 50, 60, 70, 80, 101], ["under 30", "30-40", "40-50", "50-60", "60-70", "70-80", "80+"], f"{k} RSI at entry")
    for k in ("5m", "15m", "1h"):
        L += bucket_table(P, f"tds_{k}", [0, 1, 4, 7, 10], ["0 (no sell count)", "1-3", "4-6", "7-9"], f"TD sell count on the {k}")
    for k in ("5m", "15m"):
        P[f"mh_{k}"] = np.where(P[f"macd_turn_dn_{k}"], "just turned down", np.where(P[f"macd_falling_{k}"], "falling 2+ bars", "rising / flat"))
        L += cat_table(P, f"mh_{k}", f"{k} MACD histogram", ["just turned down", "falling 2+ bars", "rising / flat"])
    L += bucket_table(P, "red_of3", [0, 1, 2, 3, 4], ["0 red", "1 red", "2 red", "3 red"], "Last 3 closed 5m candles: how many red")
    L += bucket_table(P, "upper_wick_pct", [0, 0.2, 0.4, 1.01], ["upper wick under 20%", "20-40%", "40%+"], "Last 5m candle upper wick (share of range)")
    P["lh"] = np.where(P.lower_high, "lower high", "not a lower high")
    L += cat_table(P, "lh", "Last 5m candle made a lower high")
    L += bucket_table(P, "vol_ratio", [0, 0.7, 1.5, 3, 1000], ["under 0.7x", "0.7-1.5x", "1.5-3x", "3x+"], "Last 5m volume vs its 20-bar average")

    L += ["", "## 4. The day's shape"]
    L += cat_table(P[P.min_after_open >= 15], "first15_close_vs_prevc", "First 15m candle closed over or back under the prior close (entries 9:45+)", ["over", "under"])
    gu = P[(P.min_after_open >= 15) & (P.gap_pct >= 0.3)]
    L += cat_table(gu, "first15_close_vs_prevc", "Gap-up days only: first 15m close vs the prior close (entries 9:45+)", ["over", "under"])
    L += cat_table(P[P.min_after_open >= 15], "first15_close_vs_d10", "First 15m candle closed over or under the daily 10 SMA (entries 9:45+)", ["over", "under"])
    P["hf30"] = P.H_hod_first30.map({True: "high printed in the first 30 min", False: "high printed later"})
    L += cat_table(P, "hf30", "Did the day's high print in the first 30 minutes? (H)")
    L += bucket_table(P, "qqq_vs_prevc_pct", [-100, -0.5, 0, 0.5, 100], ["QQQ down 0.5%+", "QQQ down 0-0.5%", "QQQ up 0-0.5%", "QQQ up 0.5%+"],
                      "What QQQ was doing at entry (vs its prior close)")
    P["qv"] = P.qqq_under_vwap.map({True: "QQQ under VWAP", False: "QQQ over VWAP"})
    L += cat_table(P[P.min_after_open >= 5], "qv", "QQQ vs its VWAP at entry")

    L += ["", "## 5. The bigger picture"]
    P["gl"] = pd.cut(P.grade_pts, [-1, 2, 3, 4, 5, 9], labels=["D (0-2)", "C (3)", "B (4)", "A- (5)", "A (6+)"])
    L += cat_table(P, "gl", "Daily grade (the bot's put grade, as of the prior close)", ["D (0-2)", "C (3)", "B (4)", "A- (5)", "A (6+)"])
    for col, nm in (("monthly_red", "Monthly red (last month red and this month so far)"), ("weekly_3lh", "3 weekly lower highs"),
                    ("tenday_under", "10-day chart: 10 EMA under 10 SMA"), ("tenday_cross_recent", "10-day chart: 10 EMA crossed under 10 SMA within 2 candles"),
                    ("cliff_4h_10d", "4h cliff diver in the last 10 days"), ("rsi3h_90_10d", "3h RSI 90 in the last 10 days"),
                    ("macd_plateau", "Daily MACD plateau"), ("near_20d_high", "Within 1 ATR of the 20-day high")):
        P["_c"] = P[col].map({True: "yes", False: "no"})
        L += cat_table(P, "_c", nm, ["yes", "no"])
    br = P[["monthly_red", "weekly_3lh", "tenday_cross_recent", "cliff_4h_10d"]].fillna(False).astype(int).sum(axis=1)
    P["nbroken"] = br.clip(upper=3).map({0: "0", 1: "1", 2: "2", 3: "3+"})
    L += cat_table(P, "nbroken", "Broken-trend clues stacked (monthly red, weekly lower highs, 10-day cross, 4h cliff)", ["0", "1", "2", "3+"])
    st = P[["rsi3h_90_10d", "macd_plateau", "near_20d_high"]].fillna(False).astype(int).sum(axis=1)
    P["nstrong"] = st.clip(upper=2).map({0: "0", 1: "1", 2: "2+"})
    L += cat_table(P, "nstrong", "Strength clues stacked (3h RSI 90, MACD plateau, near the 20-day high)", ["0", "1", "2+"])

    L += ["", "## 6. Exits: his sell vs the day's eventual low"]
    w, l = P[P.win], P[~P.win]
    L += ["", "Stock move left after his sell, to the lowest print of the rest of that session (puts). In ATR and in % of the stock price "
          "(an option on a 1-week expiry moves several times the stock %).", "",
          "| Group | Trades | Median left (ATR) | Median left (% of stock) | Sold within 0.25 ATR of the day's low | Sold before the day's low printed |",
          "|---|---|---|---|---|---|"]
    for nm, g in (("Winners", w), ("2x+ winners", P[P.big]), ("Losers", l), ("All puts", P)):
        L.append(f"| {nm} | {len(g)} | {g.exit_left_atr.median():.2f} | {g.exit_left_pct.median():.2f}% | "
                 f"{pct(g.exit_near_day_extreme.mean())} | {pct(g.exit_before_day_extreme.mean())} |")
    L += ["", "| Period | Winners: median left (ATR) | Winners sold before the low | Losers: median left (ATR) | Losers sold before the low |", "|---|---|---|---|---|"]
    for hf in ("fit", "judged"):
        a, b = P[(P.half == hf) & P.win], P[(P.half == hf) & ~P.win]
        L.append(f"| {hf} | {a.exit_left_atr.median():.2f} | {pct(a.exit_before_day_extreme.mean())} | {b.exit_left_atr.median():.2f} | {pct(b.exit_before_day_extreme.mean())} |")
    L += bucket_table(P, "exit_left_atr", [0, 0.1, 0.5, 1, 100], ["under 0.1 ATR (sold near the low)", "0.1-0.5 ATR", "0.5-1 ATR", "1+ ATR left"],
                      "How much was left after his sell")

    # ---------------- profiles
    L += ["", "## 7. Winning vs losing profile (puts, all 24 months)", "",
          "Share of winners vs losers that had each trait (traits picked to describe, not to rank).", "",
          "| Trait at entry | Winners | Losers | 2x+ winners |", "|---|---|---|---|"]
    traits = {"Entered in the first 15 minutes": (P.min_after_open >= 0) & (P.min_after_open < 15),
              "Entered 1 hour+ after the open": P.min_after_open >= 60,
              "Price above VWAP": P.vs_vwap_atr > 0, "Above the prior close": P.vs_prevc_atr > 0,
              "Gapped up 0.3%+": P.gap_pct >= 0.3, "Above the daily 8 EMA": P.vs_d8e_atr > 0,
              "5m RSI 60+": P.rsi_5m >= 60, "15m RSI 60+": P.rsi_15m >= 60, "15m TD sell 7-9": P.tds_15m >= 7,
              "3+ levels stacked": P.stacked >= 3, "Within 0.25 ATR of the high so far": P.dist_hi_sofar_atr <= 0.25,
              "QQQ red at entry": P.qqq_vs_prevc_pct < 0, "Monthly red": P.monthly_red == True, "3 weekly lower highs": P.weekly_3lh,
              "10-day 10 EMA under 10 SMA": P.tenday_under == True, "4h cliff diver last 10 days": P.cliff_4h_10d,
              "3h RSI 90 last 10 days": P.rsi3h_90_10d, "Within 1 ATR of the 20-day high": P.near_20d_high,
              "Daily grade B or better": P.grade_pts >= 4, "H: entered before the day's high": P.H_entry_before_hod,
              "B: day trade": P.daytrade, "B: held under 1 hour": P.hold_h < 1}
    for k, v in traits.items():
        v = v.fillna(False).astype(bool)
        L.append(f"| {k} | {pct(v[P.win].mean())} | {pct(v[~P.win].mean())} | {pct(v[P.big].mean())} |")
    L += ["", "Median values:", "", "| Measure | Winners | Losers | 2x+ |", "|---|---|---|---|"]
    for col, nm, fmt in (("min_after_open", "Minutes after the open", "{:.0f}"), ("rsi_5m", "5m RSI", "{:.0f}"), ("rsi_15m", "15m RSI", "{:.0f}"),
                         ("dist_hi_sofar_atr", "Distance under the high so far (ATR)", "{:.2f}"), ("vs_vwap_atr", "Vs VWAP (ATR)", "{:+.2f}"),
                         ("vs_prevc_atr", "Vs prior close (ATR)", "{:+.2f}"), ("stacked", "Levels stacked", "{:.0f}"),
                         ("H_hod_dist_atr", "H: under the day's high (ATR)", "{:.2f}"), ("hold_h", "B: hold (hours)", "{:.1f}"),
                         ("stock_move_atr", "B: stock move in his favor, entry to exit (ATR)", "{:+.2f}")):
        L.append(f"| {nm} | {fmt.format(P[P.win][col].median())} | {fmt.format(P[~P.win][col].median())} | {fmt.format(P[P.big][col].median())} |")

    # ---------------- calls
    Cl["win"] = Cl.ret > 0
    L += ["", "## 8. Calls (small sample)", "",
          f"{len(Cl)} calls: fit {int((Cl.half=='fit').sum())} trades, win {pct(Cl[Cl.half=='fit'].win.mean())}; "
          f"judged {int((Cl.half=='judged').sum())} trades, win {pct(Cl[Cl.half=='judged'].win.mean())}. Too few to rank conditions; timing and hold shown for completeness."]
    L += bucket_table(Cl, "min_after_open", [-1000, 0, 15, 60, 1000], ["pre-market", "0-15 min", "15-60 min", "1 h+"], "Calls: minutes after the open")
    L += bucket_table(Cl, "hold_h", [0, 1, 7, 10000], ["under 1 h", "1 h to close", "overnight+"], "Calls: hold length")

    open(f"{OUT}/REPORT.md", "w").write("\n".join(str(x) for x in L) + "\n")
    print("\n".join(str(x) for x in L[:80]))


if __name__ == "__main__":
    main()
