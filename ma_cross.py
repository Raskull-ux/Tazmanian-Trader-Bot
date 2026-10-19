"""
MA cross test — the crosses Taz says START the move down at a top:
  1. 10 EMA crosses below the 10 SMA
  2. 10 SMA crosses below the 20 SMA
  3. Both: the 10/20 cross comes within 5 days after a 10 EMA/10 SMA cross (the sequence)
Daily closes. One signal per type per name per 10 trading days.

"At a top" (set before running): the name made its highest close of the last 60 days within the 10 sessions before
the cross. Also shown: daily RSI hit 70+ in the 15 sessions before the cross, and 50 SMA over/under the 200.

Two ways it's traded, both graded:
  A. DAILY: puts at the cross close. Move after 1, 2, 3, 5, 10, 15, 20 days; deepest drop and highest rise inside
     5 and 10 days, and NET = drop minus rise (so a stock that just swings harder both ways is not counted as an edge);
     dropped 5% within 20 days. Yahoo daily history back to 2000.
  B. NEXT MORNING: puts at the 9:35 bar the day after the cross. Move after 15m, 30m, 1h, 2h, 3h and at the close;
     deepest drop and highest rise within 3h, and NET. Alpaca 5-minute bars, 2016 -> now (needs the Alpaca keys).

Compared with:
  'random'          = every day of the same name and period (for B: every day's 9:35 bar)
  'at a top, no X'  = every day that meets the same at-a-top condition, cross or not
                      -> tells you whether the CROSS adds anything beyond 'it just topped'

PASS (set before running): group (ETF / Mega tech / High beta), 100+ signals, vs RANDOM, positive in EVERY period
(A: 2000-15, 2016-21, 2022-26; B: 2016-21, 2022-26), t >= 3.5 (monthly clusters; quarterly for 15-20 days),
on any of: A 3/5/10/20-day move, A net 5/10 days; B 1h / 3h / close move (at least 0.10% of price), B net 3h.
Why 3.5 and not 3: this test makes ~270 tries (3 signals x 3 filters x 3 groups x 10 measures). On random-walk test
data, t >= 3 passed noise 2 times in 4 runs; t >= 3.5 passed it 0 times.
Out: results/ma_cross/report.md, signals.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/ma_cross"
GROUPS = {
    "ETF": "QQQ SPY IWM DIA XLK SMH SOXX IGV XLY ARKK".split(),
    "MEGA": "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split(),
    "HIGHBETA": ("PLTR MU COIN MSTR HOOD RDDT SMCI ARM SHOP SNOW CRWD UBER INTC MARA RIOT SOFI AFRM UPST RIVN "
                 "ROKU NET DDOG ZS PANW CVNA DKNG ABNB DASH TTD ENPH").split(),
}
PD = (("2000-2015", "1999-01-01", "2016-01-01"), ("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))
PI = PD[1:]
DH = (1, 2, 3, 5, 10, 15, 20)
IH = {"15m": 3, "30m": 6, "1h": 12, "2h": 24, "3h": 36}
NB = 78
QQQ_DATES = ["2021-09-17", "2022-01-04", "2023-03-09", "2023-10-18", "2024-04-04", "2024-04-15", "2024-08-30", "2025-02-21"]


# ------------------------------------------------------------------ data
def yahoo(sym):
    try:
        import yfinance as yf
        d = yf.download(sym, start="1999-01-01", auto_adjust=True, progress=False, threads=False)
        if d is None or len(d) < 300:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower)[["open", "high", "low", "close"]]
        d.columns = ["o", "h", "l", "c"]
        d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        return d.dropna()
    except Exception as ex:
        print(f"  yahoo {sym}: {ex}")
        return None


def akeys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s} if k and s else None


def alpaca(sym, tf, start):
    Hd = akeys()
    if not Hd:
        return None
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": "all", "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=Hd, params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            print(f"  alpaca {sym} {tf}: {r.status_code}"); return None
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    if not rows:
        return None
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York")
    return d


def load_daily(sym):
    d = yahoo(sym); time.sleep(0.5)
    if d is None:
        a = alpaca(sym, "1Day", "2015-01-01")
        if a is not None:
            a.index = a.t.dt.tz_localize(None).dt.normalize(); d = a[["o", "h", "l", "c"]]
    return d


# ------------------------------------------------------------------ helpers
def fwd(a, n, fn):
    s = pd.Series(a[::-1])
    r = getattr(s.rolling(n, min_periods=n), fn)().values[::-1]
    out = np.full(len(a), np.nan); out[:-1] = r[1:]
    return out


def wilder_rsi(c, n=14):
    # RSI uses EXPONENTIAL averaging (EMA span) to match Taz's charts (RSI 14 exponential). Verified QQQ 2026-10-16 = 20.87.
    d = c.diff()
    up = d.clip(lower=0).ewm(span=n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(span=n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def daily_outcomes(dd):
    c, h, l = dd.c.values, dd.h.values, dd.l.values
    n = len(c); O = {}
    for k in DH:
        x = np.full(n, np.nan); x[:-k] = -(c[k:] / c[:-k] - 1) * 100
        O[f"x{k}"] = x
    for w in (5, 10):
        O[f"drop{w}"] = -(fwd(l, w, "min") / c - 1) * 100
        O[f"rise{w}"] = (fwd(h, w, "max") / c - 1) * 100
        O[f"net{w}"] = O[f"drop{w}"] - O[f"rise{w}"]
    lo20 = fwd(l, 20, "min")
    O["hit5"] = np.where(np.isnan(lo20), np.nan, (lo20 <= c * 0.95).astype(float))
    return O


DM = [f"x{k}" for k in DH] + ["drop5", "rise5", "net5", "drop10", "rise10", "net10", "hit5"]
IM = list(IH) + ["close", "fav3h", "adv3h", "net3h"]


def morning_outcomes(m, days):
    """Puts entered at the close of each day's 9:35 bar (slot 0)."""
    di = pd.Index(days)
    r = di.get_indexer(m.day); ok = r >= 0
    g = {k: np.full((len(days), NB), np.nan) for k in ("h", "l", "c")}
    for k in g:
        g[k][r[ok], m.slot.values[ok]] = m[k].values[ok]
    c = pd.DataFrame(g["c"]).ffill(axis=1).values
    h = np.where(np.isnan(g["h"]), c, g["h"]); l = np.where(np.isnan(g["l"]), c, g["l"])
    last = np.nanmax(np.where(np.isnan(c), -1, np.arange(NB)[None, :]), axis=1)
    c0 = c[:, 0]; O = {}
    for lab, hb in IH.items():
        tgt = np.minimum(hb, last)
        O[lab] = -(c[np.arange(len(days)), tgt] / c0 - 1) * 100
    O["close"] = -(c[np.arange(len(days)), last] / c0 - 1) * 100
    O["fav3h"] = -(np.nanmin(l[:, 1:37], axis=1) / c0 - 1) * 100
    O["adv3h"] = (np.nanmax(h[:, 1:37], axis=1) / c0 - 1) * 100
    O["net3h"] = O["fav3h"] - O["adv3h"]
    return O


def pof(day, periods):
    for pn, a, z in periods:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


# ------------------------------------------------------------------ per symbol
def run_symbol(sym, grp, out):
    dd = load_daily(sym)
    if dd is None or len(dd) < 300:
        print(f"  {sym}: no daily data"); return
    c = dd.c
    e10 = c.ewm(span=10, adjust=False).mean(); s10 = c.rolling(10).mean(); s20 = c.rolling(20).mean()
    s50 = c.rolling(50).mean(); s200 = c.rolling(200).mean()
    rsi = wilder_rsi(c)
    x1 = (e10 < s10) & (e10.shift() >= s10.shift())
    x2 = (s10 < s20) & (s10.shift() >= s20.shift())
    x1_recent = x1.rolling(6, min_periods=1).max().astype(bool)          # today or the 5 days before
    both = x2 & x1_recent
    hi60 = c.rolling(60).max()
    at_top = (c.eq(hi60)).astype(int).rolling(10, min_periods=1).max().shift(1).fillna(0).astype(bool)   # 60-day closing high in prior 10 sessions
    rsi_top = (rsi >= 70).astype(int).rolling(15, min_periods=1).max().shift(1).fillna(0).astype(bool)
    O = daily_outcomes(dd)
    days = dd.index
    dser = pd.Series(days)
    base = {}
    for pn, a, z in PD:
        msk = ((dser >= a) & (dser < z)).values & np.isfinite(s200.values)
        tp = msk & at_top.values
        base[(pn, "all")] = {k: np.nanmean(O[k][msk]) if msk.sum() else np.nan for k in DM}
        base[(pn, "top")] = {k: np.nanmean(O[k][tp]) if tp.sum() > 10 else np.nan for k in DM}
    # next-morning intraday
    MO, mbase, mdays = None, {}, None
    m = alpaca(sym, "5Min", "2016-01-01")
    if m is not None and len(m):
        m["day"] = m.t.dt.tz_localize(None).dt.normalize()
        mins = m.t.dt.hour * 60 + m.t.dt.minute
        m = m[(mins >= 570) & (mins < 960)].copy()
        m["slot"] = (m.t.dt.hour * 60 + m.t.dt.minute - 570) // 5
        mdays = pd.Index(sorted(m.day.unique()))
        MO = morning_outcomes(m, mdays)
        ms = pd.Series(mdays)
        for pn, a, z in PI:
            msk = ((ms >= a) & (ms < z)).values
            mbase[pn] = {k: np.nanmean(MO[k][msk]) for k in IM}
    for name, sig in (("10 EMA x 10 SMA", x1), ("10 SMA x 20 SMA", x2), ("Both (10/10 then 10/20)", both)):
        last = -99
        for j in np.where(sig.values)[0]:
            if j - last < 10 or j < 200 or j + 21 >= len(days) or not np.isfinite(s200.iloc[j]):
                continue
            last = j
            day = days[j]; pn = pof(day, PD)
            rec = dict(signal=name, symbol=sym, group=grp, date=day, at_top=bool(at_top.iloc[j]), rsi_top=bool(rsi_top.iloc[j]),
                       trend="50 over 200" if s50.iloc[j] > s200.iloc[j] else "50 under 200")
            for k in DM:
                rec[k] = O[k][j]; rec[f"all_{k}"] = base[(pn, "all")][k]; rec[f"top_{k}"] = base[(pn, "top")][k]
            if MO is not None and j + 1 < len(days):
                nd = days[j + 1]
                pos = mdays.get_indexer([nd])[0]
                if pos >= 0:
                    ipn = pof(nd, PI)
                    for k in IM:
                        rec[f"m_{k}"] = MO[k][pos]; rec[f"mall_{k}"] = mbase.get(ipn, {}).get(k, np.nan)
            out.append(rec)


# ------------------------------------------------------------------ report
def tcl(x, dates, freq="M"):
    x = pd.Series(np.asarray(x, float)); dd = pd.Series(np.asarray(dates))
    ok = x.notna(); x, dd = x[ok], dd[ok]
    dm = x.groupby(pd.DatetimeIndex(dd.values).to_period(freq)).mean()
    if len(dm) < 5 or dm.std() == 0:
        return float("nan")
    return dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm)))


def per(x, a, b):
    return x[(x.date >= a) & (x.date < b)]


def check(x, col, base, periods, floor=0.0, freq="M"):
    x = x.dropna(subset=[col])
    e = x[col] - x[base]
    pe = [(per(x, a, b)[col] - per(x, a, b)[base]).mean() for _, a, b in periods]
    t = tcl(e, x.date.values, freq)
    ok = len(x) >= 100 and all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3.5 and e.mean() >= floor
    return ok, pe, e.mean(), t, len(x)


def report(E):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    sigs = list(dict.fromkeys(E.signal))
    L = ["# 10 EMA / 10 SMA and 10 / 20 SMA crosses down — do they start the move?", "",
         "Puts direction: positive = it fell. 'vs random' = every day of that name and period. 'vs at-a-top' = every day "
         "that made a 60-day closing high in the prior 10 sessions, cross or not. NET = deepest drop minus highest rise "
         "(bigger swings both ways don't count). t clustered by month (quarter for 15-20 days).", "",
         "## PASS CHECK (set before running): 100+ signals, vs random, positive in every period, t >= 3.5 (many tries, so the bar is higher)", "",
         "| Signal | Filter | Group | Signals | Passes on | Strongest |", "|---|---|---|---|---|---|"]
    tries = [("x3", "all_x3", PD, 0, "M", "3d"), ("x5", "all_x5", PD, 0, "M", "5d"), ("x10", "all_x10", PD, 0, "M", "10d"),
             ("x20", "all_x20", PD, 0, "Q", "20d"), ("net5", "all_net5", PD, 0, "M", "net 5d"), ("net10", "all_net10", PD, 0, "M", "net 10d"),
             ("m_1h", "mall_1h", PI, 0.10, "M", "next-morning 1h"), ("m_3h", "mall_3h", PI, 0.10, "M", "next-morning 3h"),
             ("m_close", "mall_close", PI, 0.10, "M", "next-morning close"), ("m_net3h", "mall_net3h", PI, 0, "M", "next-morning net 3h")]
    filters = [("all", lambda x: x.signal == x.signal), ("at a top", lambda x: x.at_top), ("RSI 70 in last 15d", lambda x: x.rsi_top)]
    for s in sigs:
        for fl, f in filters:
            for g in GROUPS:
                x = E[(E.signal == s) & (E.group == g)]
                x = x[f(x)]
                if not len(x):
                    continue
                hits, best = [], None
                for col, b, prd, fl0, fq, lab in tries:
                    if col not in x:
                        continue
                    ok, pe, em, t, n = check(x, col, b, prd, fl0, fq)
                    if ok:
                        hits.append(lab)
                    if pd.notna(t) and (best is None or t > best[2]):
                        best = (lab, em, t, pe)
                ev = f"{best[0]}: {best[1]:+.2f} (t {best[2]:.1f}; {' / '.join('—' if pd.isna(p) else f'{p:+.2f}' for p in best[3])})" if best else "—"
                L.append(f"| {s} | {fl} | {g} | {len(x)} | {'**' + ', '.join(hits) + '**' if hits else 'nothing'} | {ev} |")

    def rows_for(x, lab):
        if len(x) < 8:
            return None
        cells = []
        for k in DH:
            e = x[f"x{k}"] - x[f"all_x{k}"]
            cells.append(f"{e.mean():+.2f} (t {tcl(e, x.date.values, 'Q' if k >= 15 else 'M'):.1f})")
        n10 = x.net10 - x.all_net10
        tn = (x.net10 - x.top_net10).mean()
        return (f"| {lab} | {len(x)} | " + " | ".join(cells) +
                f" | {n10.mean():+.2f} (t {tcl(n10, x.date.values):.1f}) | {tn:+.2f} | {x.hit5.mean():.0%} vs {x.all_hit5.mean():.0%} |")

    L += ["\n## A. Daily — puts at the cross close (edge vs random, t)\n"]
    for s in sigs:
        L += [f"\n### {s}\n", "| Group / filter | Signals | 1d | 2d | 3d | 5d | 10d | 15d | 20d | Net 10d vs random | Net 10d vs at-a-top | Dropped 5% in 20d |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        X = E[E.signal == s]
        for g in list(GROUPS) + ["QQQ"]:
            base = X[X.group == g] if g in GROUPS else X[X.symbol == g]
            for fl, f in filters + [("50 over 200", lambda x: x.trend == "50 over 200"), ("50 under 200", lambda x: x.trend == "50 under 200")]:
                r = rows_for(base[f(base)], f"{g}: {fl}")
                if r:
                    L.append(r)
    if "m_1h" in E:
        L += ["\n## B. Next morning — puts at the 9:35 bar after the cross (edge vs every day's 9:35, t)\n"]
        for s in sigs:
            L += [f"\n### {s}\n", "| Group / filter | Signals | 15m | 30m | 1h | 2h | 3h | Close | Deepest drop 3h | Highest rise 3h | Net 3h |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
            X = E[(E.signal == s)].dropna(subset=["m_1h"])
            for g in list(GROUPS) + ["QQQ"]:
                base = X[X.group == g] if g in GROUPS else X[X.symbol == g]
                for fl, f in filters:
                    x = base[f(base)]
                    if len(x) < 8:
                        continue
                    cells = [f"{(x[f'm_{k}'] - x[f'mall_{k}']).mean():+.2f} (t {tcl(x[f'm_{k}'] - x[f'mall_{k}'], x.date.values):.1f})" for k in list(IH) + ["close"]]
                    nn = x.m_net3h - x.mall_net3h
                    L.append(f"| {g}: {fl} | {len(x)} | " + " | ".join(cells) +
                             f" | {x.m_fav3h.mean():.2f}% vs {x.mall_fav3h.mean():.2f}% | {x.m_adv3h.mean():.2f}% vs {x.mall_adv3h.mean():.2f}% | {nn.mean():+.2f} (t {tcl(nn, x.date.values):.1f}) |")
    q = E[(E.symbol == "QQQ") & (E.date >= "2018-01-01")].sort_values("date")
    L += ["\n## QQQ — every cross since 2018 (raw puts-direction moves, + = it fell)\n",
          "| Date | Signal | At a top | 50 vs 200 | 1d | 3d | 5d | 10d | 20d | Deepest drop 10d | Highest rise 10d |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in q.itertuples():
        L.append(f"| {r.date:%Y-%m-%d} | {r.signal} | {'yes' if r.at_top else ''} | {r.trend} | {r.x1:+.1f}% | {r.x3:+.1f}% | {r.x5:+.1f}% | "
                 f"{r.x10:+.1f}% | {r.x20:+.1f}% | {r.drop10:.1f}% | {r.rise10:.1f}% |")
    L += ["\n## Your QQQ dates: the nearest cross within 7 days (+ = it fell)\n", "| Your date | Nearest cross | Signal | 3d | 10d | 20d |", "|---|---|---|---|---|---|"]
    qa = E[E.symbol == "QQQ"]
    for ds in QQQ_DATES:
        t = pd.Timestamp(ds)
        near = qa[(qa.date - t).abs() <= pd.Timedelta(days=7)].copy()
        if not len(near):
            L.append(f"| {ds} | none within 7 days | | | | |"); continue
        for r in near.sort_values("date").itertuples():
            L.append(f"| {ds} | {r.date:%Y-%m-%d} | {r.signal} | {r.x3:+.1f}% | {r.x10:+.1f}% | {r.x20:+.1f}% |")
    for sym in ("TSLA", "INTC", "NVDA"):
        q2 = E[(E.symbol == sym) & (E.date >= "2025-01-01")].sort_values("date")
        if len(q2):
            L += [f"\n## {sym} — crosses since 2025 (+ = it fell)\n", "| Date | Signal | At a top | 3d | 10d | 20d | Deepest drop 10d |", "|---|---|---|---|---|---|---|"]
            for r in q2.itertuples():
                L.append(f"| {r.date:%Y-%m-%d} | {r.signal} | {'yes' if r.at_top else ''} | {r.x3:+.1f}% | {r.x10:+.1f}% | {r.x20:+.1f}% | {r.drop10:.1f}% |")
    L += ["",
          "Limits: today's names (survivorship: collapsed names are missing, which hurts puts); stock moves, not option prices; "
          "next-morning part covers 2016 on."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    if not akeys():
        print("  No Alpaca keys: daily part only (next-morning part skipped).")
    E = []
    for g, syms in GROUPS.items():
        for s in syms:
            try:
                run_symbol(s, g, E)
            except Exception as ex:
                print(f"  {s}: {ex}"); continue
            print(f"  {s}: signals so far {len(E)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/signals.csv.gz", index=False, compression="gzip")
    report(E)


if __name__ == "__main__":
    main()
