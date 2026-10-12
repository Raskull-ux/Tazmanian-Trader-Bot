"""
3-hour RSI 90 top test — Taz's read, graded the way he described it:
  "90 RSI on the 3-hour (extended hours) is code for a top forming. It may not top right away. There's usually a
   pullback the day after or the day after that, even if it keeps going. It can make new highs later, but it's the
   beginning of the end: we end up lower, sooner than later. Sometimes it takes a month (TSLA), it did it on RDDT too."

So two claims, both tested:
  SHORT: a pullback within 1-3 days (even if the trend continues)
  LONG : a top forms within about a month and price ends lower over the next 1-3 months

Data: Alpaca 1-hour bars INCLUDING extended hours (2016 -> now), built into 3-hour candles starting 4:00, 7:00, 10:00,
13:00, 16:00, 19:00 ET (Taz's chart), RSI(14) Wilder on those candles. Daily bars for outcomes. Needs the Alpaca keys.

Signal: first 3-hour close with RSI >= 90 (also 85 and 80, to see if 90 is special), one per 20 trading days per name.
Entry: that day's close if the candle closed by 16:00, otherwise the next day's close (after-hours signal).

Measured (puts direction: positive = it fell), against TWO comparisons:
  'random'     = every day of the same name and period
  'overbought' = only days when the DAILY RSI(14) was 70+ (is 3h RSI 90 different from ordinary overbought?)
  1. close-to-close after 1, 2, 3, 5, 10, 20, 40, 60 days
  2. the pullback: deepest drop vs highest rise inside 3 and 5 days (net = drop minus rise, so bigger swings both
     ways don't count as an edge)
  3. 'top formed within a month': the highest high of the next 30 days is never beaten in days 31-90
  4. deepest low within 60 days

t clustered by month (by quarter for 40/60-day and top-within-a-month measures; on random test data, monthly
clusters let a 40-day result pass falsely once in 5 runs).
PASS (set before running), per group, 100+ signals, vs RANDOM, positive in BOTH periods (2016-21, 2022-26), t >= 3,
on any of: close at 3/5/10/20/40/60 days, net pullback at 3 days, or top-within-a-month rate (+5 points or more).
The 'overbought' comparison is shown next to it so you can see whether 90 adds anything beyond 'it's extended'.
Out: results/rsi3h_top/report.md, signals.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/rsi3h_top"
GROUPS = {
    "ETF": "QQQ SPY IWM DIA XLK SMH SOXX IGV XLY ARKK".split(),
    "MEGA": "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split(),
    "HIGHBETA": ("PLTR MU COIN MSTR HOOD RDDT SMCI ARM SHOP SNOW CRWD UBER INTC MARA RIOT SOFI AFRM UPST RIVN "
                 "ROKU NET DDOG ZS PANW CVNA DKNG ABNB DASH TTD ENPH").split(),
}
PERIODS = (("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))
H = (1, 2, 3, 5, 10, 20, 40, 60)
LEVELS = (90, 85, 80)


# ------------------------------------------------------------------ data
def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing: run this in the repo that has the Alpaca secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


def fetch(sym, tf, start):
    Hd, rows, token = keys(), [], None
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
            raise RuntimeError(f"{sym} {tf} {r.status_code}: {r.text[:200]}")
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    if len(d):
        d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York")
    return d


def three_hour(h1):
    """1-hour bars (extended hours) -> 3-hour candles starting 4,7,10,13,16,19 ET."""
    h = h1.t.dt.hour
    h1 = h1[(h >= 4) & (h < 20)].copy()
    h1["start"] = 4 + 3 * ((h1.t.dt.hour - 4) // 3)
    h1["date"] = h1.t.dt.tz_localize(None).dt.normalize()
    g = h1.groupby(["date", "start"]).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last")).reset_index()
    return g.sort_values(["date", "start"]).reset_index(drop=True)


def wilder_rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


# ------------------------------------------------------------------ outcomes (vectorised over all days)
def fwd(a, n, fn):
    """fn over a[j+1 .. j+n] for every j (NaN where incomplete)."""
    s = pd.Series(a[::-1])
    r = getattr(s.rolling(n, min_periods=n), fn)().values[::-1]
    out = np.full(len(a), np.nan)
    out[:-1] = r[1:]
    return out


def all_outcomes(dd):
    c, h, l = dd.c.values, dd.h.values, dd.l.values
    n = len(c); O = {}
    for k in H:
        x = np.full(n, np.nan); x[:-k] = -(c[k:] / c[:-k] - 1) * 100
        O[f"x{k}"] = x
    for w in (3, 5):
        O[f"drop{w}"] = -(fwd(l, w, "min") / c - 1) * 100
        O[f"rise{w}"] = (fwd(h, w, "max") / c - 1) * 100
        O[f"net{w}"] = O[f"drop{w}"] - O[f"rise{w}"]
    O["low60"] = -(fwd(l, 60, "min") / c - 1) * 100
    hi30 = np.fmax(h, fwd(h, 30, "max"))
    later = np.full(n, np.nan); later[:-30] = fwd(h, 60, "max")[30:]          # days 31..90
    O["top30"] = np.where(np.isnan(later) | np.isnan(hi30), np.nan, (hi30 >= later).astype(float))
    return O


METRICS = [f"x{k}" for k in H] + ["drop3", "rise3", "net3", "drop5", "rise5", "net5", "low60", "top30"]


def period_of(day):
    for pn, a, z in PERIODS:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


# ------------------------------------------------------------------ per symbol
def run_symbol(sym, grp, out, lists):
    dd = fetch(sym, "1Day", "2015-06-01")
    if len(dd) < 400:
        return
    dd.index = dd.t.dt.tz_localize(None).dt.normalize(); dd = dd[["o", "h", "l", "c"]]
    h1 = fetch(sym, "1Hour", "2015-10-01")
    t3 = three_hour(h1)
    t3["rsi"] = wilder_rsi(t3.c)
    drsi = wilder_rsi(dd.c)
    O = all_outcomes(dd)
    days = dd.index
    # baselines: all days, and daily-RSI-70+ days, per period
    base = {}
    dser = pd.Series(days)
    for pn, a, z in PERIODS:
        m = ((dser >= a) & (dser < z)).values
        ob = m & (drsi.values >= 70)
        base[(pn, "all")] = {k: np.nanmean(O[k][m]) for k in METRICS}
        base[(pn, "ob")] = {k: np.nanmean(O[k][ob]) if ob.sum() > 5 else np.nan for k in METRICS}
    for lvl in LEVELS:
        last_i = -99
        for r in t3[(t3.rsi >= lvl) & (t3.date >= "2016-03-01")].itertuples():
            pos = days.searchsorted(r.date)
            if pos >= len(days) or days[pos] != r.date:
                continue
            i = pos if r.start <= 13 else pos + 1          # after-hours candle -> next day's close
            if i >= len(days) or i - last_i < 20:
                continue
            last_i = i
            pn = period_of(days[i])
            rec = dict(level=lvl, symbol=sym, group=grp, date=days[i], signal_time=f"{r.date:%Y-%m-%d} {r.start}:00",
                       rsi3h=r.rsi, daily_rsi=drsi.iloc[i])
            for k in METRICS:
                rec[k] = O[k][i]
                rec[f"all_{k}"] = base[(pn, "all")][k]
                rec[f"ob_{k}"] = base[(pn, "ob")][k]
            out.append(rec)
    if sym in ("TSLA", "RDDT", "QQQ", "NVDA", "PLTR", "MSTR", "COIN"):
        lists[sym] = (dd, t3)


# ------------------------------------------------------------------ report
def tcl(x, dates, freq="M"):
    """t clustered by month; by quarter for 40-day+ measures (their windows overlap across months, which
    inflated t on random test data)."""
    x = pd.Series(np.asarray(x, float)); dd = pd.Series(np.asarray(dates))
    ok = x.notna(); x, dd = x[ok], dd[ok]
    dm = x.groupby(pd.DatetimeIndex(dd.values).to_period(freq)).mean()
    if len(dm) < 5 or dm.std() == 0:
        return float("nan")
    return dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm)))


def per(x, a, b):
    return x[(x.date >= a) & (x.date < b)]


def check(x, k):
    e = x[k] - x[f"all_{k}"]
    pe = [(per(x, a, b)[k] - per(x, a, b)[f"all_{k}"]).mean() for _, a, b in PERIODS]
    t = tcl(e, x.date.values, "Q" if k in ("x40", "x60", "top30", "low60") else "M")
    floor = 0.05 if k == "top30" else 0.0
    ok = len(x) >= 100 and all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3 and e.mean() >= floor
    return ok, pe, e.mean(), t


def report(E, lists):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    L = ["# 3-hour RSI 90 — does it mark a top?", "",
         "3-hour candles with extended hours (4:00/7:00/10:00/13:00/16:00/19:00 ET), RSI(14). One signal per name per 20 "
         "trading days. Puts direction: positive = price fell. 'vs random' = every day of that name and period. "
         "'vs overbought' = only days with daily RSI 70+. t clustered by month.", "",
         "## PASS CHECK (set before running): 100+ signals, vs random, positive in BOTH periods, t >= 3, on any of close at "
         "3/5/10/20/40/60 days, net pullback at 3 days, or top-within-a-month (+5 points)", "",
         "| 3h RSI | Group | Signals | Passes on | Strongest |", "|---|---|---|---|---|"]
    tries = ["x3", "x5", "x10", "x20", "x40", "x60", "net3", "top30"]
    for lvl in LEVELS:
        for g in GROUPS:
            x = E[(E.level == lvl) & (E.group == g)]
            if not len(x):
                continue
            hits, best = [], None
            for k in tries:
                ok, pe, em, t = check(x, k)
                if ok:
                    hits.append(k)
                if pd.notna(t) and (best is None or t > best[2]):
                    best = (k, em, t, pe)
            ev = f"{best[0]}: {best[1]:+.2f} (t {best[2]:.1f}; {' / '.join(f'{p:+.2f}' for p in best[3])})" if best else "—"
            L.append(f"| {lvl} | {g} | {len(x)} | {'**' + ', '.join(hits) + '**' if hits else 'nothing'} | {ev} |")

    L += ["\n## 1. Close-to-close, puts direction (edge vs random | vs overbought)\n",
          "| 3h RSI | Group | Signals | " + " | ".join(f"{k}d" for k in H) + " |", "|---|---|---|" + "---|" * len(H)]
    for lvl in LEVELS:
        for g in list(GROUPS) + ["TSLA", "RDDT", "QQQ"]:
            x = E[(E.level == lvl) & ((E.group == g) if g in GROUPS else (E.symbol == g))]
            if len(x) < 5:
                continue
            cells = []
            for k in H:
                e1 = x[f"x{k}"] - x[f"all_x{k}"]; e2 = x[f"x{k}"] - x[f"ob_x{k}"]
                cells.append(f"{e1.mean():+.2f} (t {tcl(e1, x.date.values, 'Q' if k >= 40 else 'M'):.1f}) \\| {e2.mean():+.2f}")
            L.append(f"| {lvl} | {g} | {len(x)} | " + " | ".join(cells) + " |")

    L += ["\n## 2. The pullback (next 3 and 5 days) and the long run\n",
          "| 3h RSI | Group | Deepest drop 3d | Highest rise 3d | Net 3d (edge, t) | Net 5d (edge, t) | Top formed within a month | Deepest low in 60d |",
          "|---|---|---|---|---|---|---|---|"]
    for lvl in LEVELS:
        for g in list(GROUPS) + ["TSLA", "RDDT", "QQQ"]:
            x = E[(E.level == lvl) & ((E.group == g) if g in GROUPS else (E.symbol == g))]
            if len(x) < 5:
                continue
            n3 = x.net3 - x.all_net3; n5 = x.net5 - x.all_net5
            L.append(f"| {lvl} | {g} ({len(x)}) | {x.drop3.mean():.1f}% vs {x.all_drop3.mean():.1f}% | {x.rise3.mean():.1f}% vs {x.all_rise3.mean():.1f}% | "
                     f"{n3.mean():+.2f} (t {tcl(n3, x.date.values):.1f}) | {n5.mean():+.2f} (t {tcl(n5, x.date.values):.1f}) | "
                     f"{x.top30.mean():.0%} vs {x.all_top30.mean():.0%} random, {x.ob_top30.mean():.0%} overbought | "
                     f"{x.low60.mean():.1f}% vs {x.all_low60.mean():.1f}% |")

    for sym in ("TSLA", "RDDT", "NVDA", "PLTR", "MSTR", "COIN", "QQQ"):
        x = E[(E.symbol == sym) & (E.level == 90)].sort_values("date")
        if not len(x) or sym not in lists:
            continue
        dd, _ = lists[sym]
        L += [f"\n## {sym}: every 3h RSI 90 signal\n",
              "| Signal (3h candle) | 3h RSI | Daily RSI | 3d | 10d | 20d | 40d | 60d | Drop within 3d | Next top (date, % above entry) | Fall from that top within 60d |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in x.itertuples():
            i = dd.index.get_loc(r.date)
            seg = dd.iloc[i:i + 31]
            tday = seg.h.idxmax(); top = seg.h.max()
            after = dd.loc[tday:].iloc[1:61]
            fall = (after.l.min() / top - 1) * 100 if len(after) else np.nan
            L.append(f"| {r.signal_time} | {r.rsi3h:.0f} | {r.daily_rsi:.0f} | {-r.x3:+.1f}% | {-r.x10:+.1f}% | {-r.x20:+.1f}% | "
                     f"{-r.x40:+.1f}% | {-r.x60:+.1f}% | {r.drop3:.1f}% | {tday:%Y-%m-%d}, {(top / dd.c.iloc[i] - 1) * 100:+.1f}% | {fall:.1f}% |")
    L += ["", "In the per-name lists, moves are the stock's own move (negative = it fell). Limits: today's names "
          "(survivorship: names that collapsed and delisted are missing, which hurts puts), Alpaca extended-hours data "
          "starts 2016, stock moves not option prices."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    E, lists = [], {}
    for g, syms in GROUPS.items():
        for s in syms:
            try:
                run_symbol(s, g, E, lists)
            except Exception as ex:
                print(f"  {s}: {ex}"); continue
            print(f"  {s}: signals so far {len(E)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/signals.csv.gz", index=False, compression="gzip")
    report(E, lists)


if __name__ == "__main__":
    main()
