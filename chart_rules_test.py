"""
Taz's chart rules test — three setups, one report (free, Alpaca daily bars, 2016 -> now)
======================================================================================
Standalone: needs no other file (uses universe/universe.csv if the repo has it, otherwise a
built-in list of liquid names). Works with either repo's Alpaca secrets.

A. COUNT FROM THE BOTTOM (Taz: the top / pullback comes ~9-11 bars after the bottom;
   weekly: week 10 usually the top; if week 11 closes red, weeks 13-16 are mostly red)
   Bottom = the lowest low that ends a DUMP:
     daily : lowest low of the 11 days around it, at least 12% below the high of the prior 40 days
     weekly: lowest low of the 7 weeks around it, at least 20% below the high of the prior 26 weeks
   Measured: which bar after the bottom the rally tops out on (highest high in bars 1-25),
   and the puts-direction move from the close of bar k (k = 1..20) over the next 5 bars,
   vs random days in the same stock. Weekly: after a red week 11, how many of weeks 13-16 are red.

B. TRIPLE MA BREAK ("sayonara")
   Closes under the 10, 20 AND 50 SMA today, and was NOT under all three two days earlier.
   Graded two entries: (1) the break close, (2) the failed retest = within 7 days the high tags
   the 10 SMA from below and the day closes back under it (Taz's Sep 17 2021 / Oct 18 2023 trigger).
   Split by: golden cross (50 crossed above 200) in the last 30 days (Taz: that's a bounce),
   distance of the 50 above the 200, how bunched the 10/20/50 are, next-day follow-through.

C. RALLY -> QUIET CONSOLIDATION -> VOLUME DUMP
   Rally: before the consolidation, price 10%+ above its lowest low of the prior 40 days.
   Consolidation: the longest 3-15 day window right before the dump day with a tight range
   (high-low within 2.5 x ATR) and average volume at or below its 50-day average.
   Dump day: red candle, close below the prior close, volume >= 1.7 x the consolidation's
   average (Taz's example: 25k/28k/22k/24k then 43k = 1.74x). Tiers 1.7-2x, 2-3x, 3x+.

Every result: puts-direction move vs SPY at 5/10/20 days, minus a CONTROL (random days in the
same stock) = EDGE, t clustered by day, and how often the stock dropped 5%+ within 20 days.
PASS (set before running): edge > 0 with t >= 2 in BOTH 2016-2021 and 2022-2026.
Calibration: Taz's QQQ dates printed with whether B fired.
Limits: today's stock list (survivorship), stock moves not option P&L.
Out: results/chart_rules/report.md, events.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/chart_rules"
START = "2015-06-01"
MAX_N = int(os.environ.get("MAX_SYMBOLS", 300))
rng = np.random.default_rng(5)
DUMP_D = float(os.environ.get("DUMP_DAILY_PCT", 12)) / 100   # daily bottom must sit this far under the prior 40-day high
DUMP_W = float(os.environ.get("DUMP_WEEKLY_PCT", 20)) / 100  # weekly bottom must sit this far under the prior 26-week high
FALLBACK = ("QQQ SPY IWM DIA SMH XLK XLF XLE XLY XLV XLI KRE IYT AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX "
            "INTC MU PLTR COIN MSTR HOOD UBER CMG WMT MCD BA DIS NKE SBUX COST HD LOW JPM BAC GS MS C WFC XOM CVX "
            "CRM ORCL ADBE QCOM TXN SHOP SQ PYPL ABNB DASH SNOW CRWD PANW NOW UNH LLY JNJ PFE MRK ABBV CAT DE GE "
            "F GM RIVN LCID SOFI RDDT RKLB ARM SMCI DELL HPQ IBM CSCO T VZ KO PEP PG TGT ROKU CVNA BABA JD PDD").split()
QQQ_DATES = ["2021-09-17", "2022-01-04", "2023-03-09", "2023-10-18", "2024-04-04", "2024-04-15", "2024-08-30", "2025-02-21"]


def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing in this repo's secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


def fetch(symbols, start, end):
    rows, token, H = [], None, keys()
    while True:
        p = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start, "end": end,
             "feed": "sip", "adjustment": "split", "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
        j = r.json()
        for sym, bars in (j.get("bars") or {}).items():
            for b in bars:
                rows.append((sym, b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]))
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["symbol", "t", "o", "h", "l", "c", "v"])
    if len(d):
        d["day"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return d


def symbols():
    if os.path.exists("universe/universe.csv"):
        u = pd.read_csv("universe/universe.csv")
        u = u[u.group != "gauge"].sort_values("avg_dollar_vol", ascending=False)
        s = u.symbol.head(MAX_N).tolist()
        return list(dict.fromkeys(["QQQ", "SPY"] + s))
    return list(dict.fromkeys(FALLBACK))


# ------------------------------------------------------------------ outcomes
def outcome(d, j, spy):
    """Puts direction (positive = stock fell), vs SPY, from close of bar j."""
    r = {}
    c0 = d.c.iloc[j]; day0 = d.index[j]
    for n in (5, 10, 20):
        if j + n >= len(d):
            r[f"x{n}"] = np.nan; continue
        dn = d.index[j + n]
        s = (spy.c.loc[dn] / spy.c.loc[day0] - 1) if (dn in spy.index and day0 in spy.index) else 0.0
        r[f"x{n}"] = -((d.c.iloc[j + n] / c0 - 1) - s) * 100
    lo = d.l.iloc[j + 1:j + 21]
    r["drop5"] = float((lo <= c0 * 0.95).any()) if len(lo) else np.nan
    return r


def control(d, j, spy, k=5):
    lo, hi = max(220, j - 250), min(len(d) - 21, j + 250)
    if hi <= lo:
        return {}
    outs = [outcome(d, int(q), spy) for q in rng.integers(lo, hi, size=k)]
    return pd.DataFrame(outs).mean().add_prefix("ctrl_").to_dict()


# ------------------------------------------------------------------ setups
def setup_A_daily(sym, d, spy, out, counts):
    h, l = d.h.values, d.l.values
    n = len(d)
    for i in range(45, n - 30):
        if l[i] != l[i - 5:i + 6].min():
            continue
        if h[i - 40:i].max() < l[i] * (1 + DUMP_D):
            continue
        seg = h[i + 1:i + 26]
        counts.append(("daily", int(seg.argmax()) + 1))
        for k in range(6, 21):              # bottom is only known 5 bars later
            j = i + k
            if j + 20 >= n:
                break
            out.append(dict(setup="A_daily", symbol=sym, date=d.index[j], k=k, **outcome(d, j, spy), **control(d, j, spy, 2)))


def setup_A_weekly(sym, d, spy, wk_rows, counts):
    w = d.resample("W-FRI").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    h, l, o, c = w.h.values, w.l.values, w.o.values, w.c.values
    base_red = (c < o).mean()
    for i in range(30, len(w) - 20):
        if l[i] != l[i - 3:i + 4].min() or h[i - 26:i].max() < l[i] * (1 + DUMP_W):
            continue
        seg = h[i + 1:i + 26]
        if len(seg) < 25:
            continue
        counts.append(("weekly", int(seg.argmax()) + 1))
        wk11_red = c[i + 11] < o[i + 11]
        red_13_16 = (c[i + 13:i + 17] < o[i + 13:i + 17]).mean()
        ret_12_16 = -(c[i + 16] / c[i + 12] - 1) * 100
        wk_rows.append(dict(symbol=sym, date=w.index[i], wk11_red=wk11_red, red_13_16=red_13_16,
                            base_red=base_red, puts_12_to_16=ret_12_16))


def setup_B(sym, d, spy, out, calib):
    c, h = d.c, d.h
    s10, s20, s50, s200 = (c.rolling(n).mean() for n in (10, 20, 50, 200))
    b3 = (c < s10) & (c < s20) & (c < s50)
    fire = b3 & ~b3.shift(2, fill_value=False)
    gc = (s50 > s200) & (s50.shift() <= s200.shift())
    gc_recent = gc.rolling(30, min_periods=1).max().astype(bool)
    for j in np.where(fire.values)[0]:
        if j < 220 or j + 21 >= len(d):
            continue
        base = dict(symbol=sym, date=d.index[j], golden_cross_30d=bool(gc_recent.iloc[j]),
                    s50_vs_200=(s50.iloc[j] / s200.iloc[j] - 1) * 100,
                    bunch=(max(s10.iloc[j], s20.iloc[j], s50.iloc[j]) - min(s10.iloc[j], s20.iloc[j], s50.iloc[j])) / c.iloc[j] * 100,
                    next_day_lower=bool(c.iloc[j + 1] < c.iloc[j]))
        out.append(dict(setup="B_break", **base, **outcome(d, j, spy), **control(d, j, spy)))
        # next-day check is only known at the NEXT close, so those rows enter there (no peeking)
        out.append(dict(setup="B_nextday", **base, **outcome(d, j + 1, spy), **control(d, j + 1, spy)))
        for q in range(j + 1, min(j + 8, len(d) - 21)):
            if h.iloc[q] >= s10.iloc[q] and c.iloc[q] < s10.iloc[q]:
                out.append(dict(setup="B_retest", **base, **outcome(d, q, spy), **control(d, q, spy)))
                break
        if sym == "QQQ":
            calib.append(d.index[j])


def setup_C(sym, d, spy, out):
    c, o, h, l, v = d.c.values, d.o.values, d.h.values, d.l.values, d.v.values
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().values
    v50 = pd.Series(v).rolling(50).mean().values
    last = -99
    for i in range(80, len(d) - 21):
        if not (c[i] < o[i] and c[i] < c[i - 1]) or i - last < 10:
            continue
        best = None
        for n in range(15, 2, -1):
            w = slice(i - n, i)
            if h[w].max() - l[w].min() <= 2.5 * atr[i - 1] and v[w].mean() <= v50[i - 1]:
                best = n; break
        if best is None:
            continue
        start = i - best
        if c[start] < 1.10 * l[max(0, start - 40):start].min():
            continue
        ratio = v[i] / v[i - best:i].mean()
        if ratio < 1.7:
            continue
        last = i
        out.append(dict(setup="C_vol_dump", symbol=sym, date=d.index[i], consol_days=best, vol_ratio=ratio,
                        **outcome(d, i, spy), **control(d, i, spy)))


# ------------------------------------------------------------------ report
def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); dd = pd.Series(np.asarray(dates))
    ok = x.notna(); x, dd = x[ok], dd[ok]
    if len(x) < 10:
        return float("nan")
    dm = x.groupby(dd.values).mean()
    return dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")


def row(name, x):
    if len(x) < 10:
        return f"| {name} | {len(x)} | — | — | — | — |"
    cells = [f"| {name} | {len(x)} |"]
    for n in (5, 10, 20):
        e = x[f"x{n}"] - x[f"ctrl_x{n}"]
        cells.append(f" {x[f'x{n}'].mean():+.2f}% vs {x[f'ctrl_x{n}'].mean():+.2f}% → **{e.mean():+.2f}** (t {tcl(e, x.date.values):.1f}) |")
    cells.append(f" {x.drop5.mean():.0%} vs {x.ctrl_drop5.mean():.0%} |")
    return "".join(cells)


H = ("| Group | Count | 5 days: puts move vs SPY vs control → edge | 10 days | 20 days | Dropped 5%+ in 20 days |\n"
     "|---|---|---|---|---|---|")


def report(E, W, counts, calib, n):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    for col in ("golden_cross_30d", "next_day_lower"):
        E[col] = E[col].fillna(False).astype(bool)
    periods = (("2016-2021", E.date < "2022-01-01"), ("2022-2026", E.date >= "2022-01-01"))
    L = ["# Taz's chart rules — tested",
         f"\n{n} names, daily bars {E.date.min():%Y} to {E.date.max():%b %Y}. 'Puts move' = how much the stock fell vs SPY "
         "(positive = good for puts). Control = random days in the same stock. Edge = setup minus control.\n"]
    # calibration
    L += ["## Calibration: your QQQ dates vs the triple-break rule (B fires within 2 trading days?)\n"]
    cal = pd.DatetimeIndex(calib)
    for ds in QQQ_DATES:
        t = pd.Timestamp(ds)
        hit = [x for x in cal if abs((x - t).days) <= 4]
        L.append(f"- {ds}: {'fired on ' + ', '.join(f'{x:%b %d}' for x in hit) if hit else 'did NOT fire'}")
    # A
    C = pd.DataFrame(counts, columns=["tf", "top_bar"])
    L += ["\n## A. Count from the bottom\n", "### Which bar the rally topped out on (bars 1-25 after the bottom)\n",
          "| Timeframe | Bottoms | Top on bar 9-11 | Bar 12-13 | Expected if random (3 of 25 bars) | Median top bar |", "|---|---|---|---|---|---|"]
    for tf in ("daily", "weekly"):
        x = C[C.tf == tf]
        if len(x):
            L.append(f"| {tf} | {len(x)} | {x.top_bar.between(9, 11).mean():.0%} | {x.top_bar.between(12, 13).mean():.0%} | 12% | {x.top_bar.median():.0f} |")
    A = E[E.setup == "A_daily"]
    L += ["\n### Daily: puts from the close of bar k after the bottom\n", H]
    for lab, m in (("bars 6-8", A.k.between(6, 8)), ("**bars 9-11**", A.k.between(9, 11)),
                   ("bars 12-14", A.k.between(12, 14)), ("bars 15-20", A.k.between(15, 20))):
        L.append(row(lab, A[m]))
    if len(W):
        W["wk11_red"] = W.wk11_red.astype(bool)
        r = W[W.wk11_red]; nr = W[~W.wk11_red]
        L += ["\n### Weekly: after week 11 closes red\n",
              "| Case | Bottoms | Share of weeks 13-16 red | Normal red-week share | Puts week 12 → 16 |", "|---|---|---|---|---|",
              f"| Week 11 red | {len(r)} | {r.red_13_16.mean():.0%} | {r.base_red.mean():.0%} | {r.puts_12_to_16.mean():+.2f}% |",
              f"| Week 11 green | {len(nr)} | {nr.red_13_16.mean():.0%} | {nr.base_red.mean():.0%} | {nr.puts_12_to_16.mean():+.2f}% |"]
    # B and C by period
    checks = []
    for title, m in periods:
        X = E[m]
        B = X[X.setup == "B_break"]; N = X[X.setup == "B_nextday"]; R = X[X.setup == "B_retest"]; V = X[X.setup == "C_vol_dump"]
        L += [f"\n## {title}\n", "### B. Triple MA break\n", H,
              row("All breaks (entry at break)", B), row("All failed retests of the 10 (entry at retest)", R),
              row("Break, NO golden cross in last 30 days", B[~B.golden_cross_30d]),
              row("Break INTO a golden cross (expect bounce)", B[B.golden_cross_30d]),
              row("Next day closes lower (entry at that close)", N[N.next_day_lower]),
              row("Next day bounces (entry at that close)", N[~N.next_day_lower])]
        for lo, hi in ((-99, 0), (0, 5), (5, 10), (10, 20), (20, 999)):
            lab = "50 SMA under the 200" if lo == -99 else (f"50 SMA {lo}%+ above the 200" if hi == 999 else f"50 SMA {lo}-{hi}% above the 200")
            L.append(row(f"Break, {lab}", B[B.s50_vs_200.between(lo, hi, inclusive='left')]))
        for lo, hi in ((0, 1), (1, 2), (2, 4), (4, 99)):
            L.append(row(f"Break, 10/20/50 bunched within {lo}-{hi if hi < 99 else '+'}% of price", B[B.bunch.between(lo, hi, inclusive='left')]))
        L += ["\n### C. Rally → quiet consolidation → volume dump\n", H, row("All volume dumps", V)]
        for lo, hi, lab in ((1.7, 2, "1.7-2x"), (2, 3, "2-3x"), (3, 99, "3x+")):
            L.append(row(f"Volume {lab}", V[V.vol_ratio.between(lo, hi, inclusive='left')]))
        for lo, hi in ((3, 5), (6, 8), (9, 11), (12, 15)):
            L.append(row(f"Consolidation {lo}-{hi} days", V[V.consol_days.between(lo, hi)]))
        for name, x in (("A daily bars 9-11", X[(X.setup == "A_daily") & X.k.between(9, 11)]),
                        ("B break, no golden cross", B[~B.golden_cross_30d]), ("B failed retest", R), ("C volume dump", V)):
            e = x["x10"] - x["ctrl_x10"]
            checks.append((title, name, e.mean(), tcl(e, x.date.values), len(x)))
    L += ["\n## PASS CHECK (set before running): 10-day edge > 0 with t >= 2 in BOTH periods\n",
          "| Setup | 2016-2021 | 2022-2026 | Verdict |", "|---|---|---|---|"]
    ck = pd.DataFrame(checks, columns=["period", "setup", "edge", "t", "n"])
    for s, g in ck.groupby("setup", sort=False):
        cells = [f"{r.edge:+.2f}, t {r.t:.1f}, n {r.n}" for r in g.itertuples()]
        ok = len(g) == 2 and (g.edge > 0).all() and (g.t >= 2).all()
        L.append(f"| {s} | {cells[0] if cells else '—'} | {cells[1] if len(cells) > 1 else '—'} | {'PASS' if ok else 'fail'} |")
    L.append("\nLimits: today's stock list (survivorship bias against puts in older years), stock moves not option P&L.")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    syms = symbols()
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    data = {}
    for i in range(0, len(syms), 50):
        ch = syms[i:i + 50]
        try:
            d = fetch(ch, START, end)
        except Exception as ex:
            print("fetch", ch[:2], ex); continue
        for s, g in d.groupby("symbol"):
            if len(g) > 300:
                data[s] = g.set_index("day")[["o", "h", "l", "c", "v"]].sort_index()
        print(f"  prices {min(i + 50, len(syms))}/{len(syms)}", flush=True)
    spy = data["SPY"]
    E, W, counts, calib = [], [], [], []
    for k, (s, d) in enumerate(data.items()):
        try:
            setup_A_daily(s, d, spy, E, counts); setup_A_weekly(s, d, spy, W, counts)
            setup_B(s, d, spy, E, calib); setup_C(s, d, spy, E)
        except Exception as ex:
            print(f"  {s}: {ex}")
        if (k + 1) % 50 == 0:
            print(f"  tested {k + 1}/{len(data)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/events.csv.gz", index=False, compression="gzip")
    report(E, pd.DataFrame(W), counts, calib, len(data))


if __name__ == "__main__":
    main()
