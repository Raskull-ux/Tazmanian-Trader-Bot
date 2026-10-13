"""
RETEST + HOURLY DIVERGENCE, BIG RUN (about 300 names).
Last run (50 names) found one lead: after a 10/20 SMA bear cross, the retest of the 10 SMA that closes back under it
WITH an hourly bearish divergence fell more than random (high-beta 118 entries, 5-day t 2.4; ETFs 63 entries, t 2.6),
while the same retests WITHOUT a divergence did nothing. Too few entries to prove it.
This run adds ~258 NEW names (Taz's core list + the most-traded names) that were NOT in the first run, so the NEW
names are a clean second look at the lead (out-of-sample).

DIVERGENCE PASS (set before running), NEW names only:
  10/20 cross -> retest 10 SMA, close back under -> hourly bearish divergence on the retest day;
  100+ entries; edge vs random positive in BOTH periods (2016-21 and 2022-26) on 5-day OR NET 10-day; t >= 2.5
  (one idea confirmed on fresh names, so 2.5, not 3.5). The first-run names and the triple break are shown, info only.

Original description of the base test:
Retest test (Taz: "All these breaks, check if the stock goes down before or after. Catch the retest.
Find the divergences on the smaller time frames.")

Breaks (daily close, first one per name per 10 sessions):
  TRIPLE  : close under the 10, 20 and 50 SMA, not under all three 2 days earlier
  X1020   : 10 SMA crosses under the 20 SMA
For each break:
  1. ORDER: in the next 10 sessions, what comes first:
       'retest' = price trades back up into the 10 SMA (day's high >= 10 SMA), or
       'down first' = price trades under the break day's low
  2. Three ways to take puts:
       E0  at the break close
       E1  at the RETEST REJECTION: first day (within 10) that tags the 10 SMA from below and closes back under it
       E1b same, at the 20 SMA
       E2  E1 + an HOURLY BEARISH DIVERGENCE on the retest day: the retest day's hourly high is at/above the bounce's
           earlier hourly high, but hourly RSI(14) is LOWER (2016+, needs Alpaca hourly bars)
  3. Outcome from each entry, puts direction (positive = it fell): close after 1/3/5/10/20 sessions,
     NET 5/10 = deepest drop minus highest rise (so bigger swings both ways don't count), dropped 5%+ within 20.
Compared with every day of the same name and period ('random'). t clustered by month.
Names: QQQ + 9 index/tech ETFs, 10 mega tech, 30 high-beta (same as the MA cross test).
Daily data: Yahoo back to 2000 (Alpaca fallback). Hourly: Alpaca 2016+.

PASS (set before running), per group, 100+ entries, vs random, positive in EVERY period
(2000-15 / 2016-21 / 2022-26), t >= 3.5 (many tries), on 5-day, 10-day or NET 10-day.
'Retest beats the break' = E1's 10-day edge is higher than E0's in every period.
Out: results/retest/report.md, events.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/retest_divergence"
GROUPS = {
    "ETF": "QQQ SPY IWM DIA XLK SMH SOXX IGV XLY ARKK".split(),
    "MEGA": "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split(),
    "HIGHBETA": ("PLTR MU COIN MSTR HOOD RDDT SMCI ARM SHOP SNOW CRWD UBER INTC MARA RIOT SOFI AFRM UPST RIVN "
                 "ROKU NET DDOG ZS PANW CVNA DKNG ABNB DASH TTD ENPH").split(),
}
SKIP = {"VXX", "UVXY", "JNUG", "TLT", "UNG", "USO", "GLD", "SLV", "GDX", "SQQQ", "TQQQ", "SOXL", "SOXS", "SPXL", "SPXS",
        "TZA", "TNA", "UPRO", "SDS", "SH", "PSQ", "LABU", "LABD", "NVDL", "TSLL", "TSLQ", "MSTU", "MSTX", "CONL", "BITX"}


def new_names(target=308):
    """Taz's core list + most-traded names, minus the first run's 50 and leveraged/volatility/commodity products."""
    try:
        u = pd.read_csv("universe/universe.csv")
    except Exception as ex:
        print(f"  universe/universe.csv not readable ({ex}); NEW group empty"); return []
    have = {x for v in GROUPS.values() for x in v}
    core = u[u.group == "core"].symbol.tolist()
    broad = u[u.group == "broad"].sort_values("avg_dollar_vol", ascending=False).symbol.tolist()
    out = []
    for x in dict.fromkeys(core + broad):
        if x in have or x in SKIP or not isinstance(x, str) or "." in x:
            continue
        out.append(x)
        if len(out) + len(have) >= target:
            break
    return out


PD = (("2000-2015", "1999-01-01", "2016-01-01"), ("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))
DH = (1, 3, 5, 10, 20)


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
    H = akeys()
    if not H:
        return None
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": "all", "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            return None
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    if not rows:
        return None
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def fwd(a, n, fn):
    s = pd.Series(a[::-1])
    r = getattr(s.rolling(n, min_periods=n), fn)().values[::-1]
    out = np.full(len(a), np.nan); out[:-1] = r[1:]
    return out


def outcomes(dd):
    c, h, l = dd.c.values, dd.h.values, dd.l.values
    n = len(c); O = {}
    for k in DH:
        x = np.full(n, np.nan); x[:-k] = -(c[k:] / c[:-k] - 1) * 100
        O[f"x{k}"] = x
    for w in (5, 10):
        O[f"net{w}"] = -(fwd(l, w, "min") / c - 1) * 100 - (fwd(h, w, "max") / c - 1) * 100
    lo20 = fwd(l, 20, "min")
    O["hit5"] = np.where(np.isnan(lo20), np.nan, (lo20 <= c * 0.95).astype(float))
    return O


MET = [f"x{k}" for k in DH] + ["net5", "net10", "hit5"]


def pof(day):
    for pn, a, z in PD:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


def hourly_divergence(hr, start_day, q_day):
    """Bearish divergence on the retest day: hourly high on q_day >= the bounce's earlier hourly high,
    with hourly RSI lower."""
    if hr is None:
        return np.nan
    seg = hr[(hr.t >= start_day) & (hr.t < q_day + pd.Timedelta(days=1))]
    if len(seg) < 20:
        return np.nan
    before, today = seg[seg.t < q_day], seg[seg.t >= q_day]
    if len(before) < 5 or not len(today):
        return np.nan
    a = before.h.idxmax(); b = today.h.idxmax()
    return float(seg.h[b] >= seg.h[a] * 0.999 and seg.rsi[b] < seg.rsi[a])


def run_symbol(sym, grp, out):
    dd = yahoo(sym); time.sleep(0.5)
    if dd is None:
        a = alpaca(sym, "1Day", "2015-01-01")
        if a is None:
            return
        a.index = a.t.dt.normalize(); dd = a[["o", "h", "l", "c"]]
    if len(dd) < 300:
        return
    hr = alpaca(sym, "1Hour", "2016-01-01")
    if hr is not None:
        hr = hr.sort_values("t").reset_index(drop=True); hr["rsi"] = rsi(hr.c)
    c = dd.c
    s10, s20, s50 = c.rolling(10).mean(), c.rolling(20).mean(), c.rolling(50).mean()
    b3 = (c < s10) & (c < s20) & (c < s50)
    sig = {"TRIPLE": b3 & ~b3.shift(2, fill_value=False),
           "X1020": (s10 < s20) & (s10.shift() >= s20.shift())}
    O = outcomes(dd)
    days = dd.index; ds = pd.Series(days)
    base = {pn: {k: np.nanmean(O[k][((ds >= a) & (ds < z)).values & np.isfinite(s50.values)]) for k in MET} for pn, a, z in PD}
    H, L, C, S10, S20 = dd.h.values, dd.l.values, c.values, s10.values, s20.values
    for name, s in sig.items():
        last = -99
        for j in np.where(s.values)[0]:
            if j - last < 10 or j < 60 or j + 32 >= len(days):
                continue
            last = j
            # order of events
            order = "neither"
            for q in range(j + 1, j + 11):
                up = H[q] >= S10[q]; dn = L[q] < L[j]
                if up and dn:
                    order = "same day"; break
                if up:
                    order = "retest first"; break
                if dn:
                    order = "down first"; break
            ent = {"E0 break close": j}
            for lab, S in (("E1 retest 10 SMA, close back under", S10), ("E1b retest 20 SMA, close back under", S20)):
                for q in range(j + 1, j + 11):
                    if H[q] >= S[q] and C[q] < S[q]:
                        ent[lab] = q; break
            for lab, q in ent.items():
                pn = pof(days[q])
                rec = dict(setup=name, entry=lab, symbol=sym, group=grp, date=days[q], break_date=days[j], order=order,
                           wait=q - j)
                for k in MET:
                    rec[k] = O[k][q]; rec[f"all_{k}"] = base[pn][k]
                if lab.startswith("E1 ") and days[q] >= pd.Timestamp("2016-02-01"):
                    rec["hdiv"] = hourly_divergence(hr, days[j], days[q])
                out.append(rec)


def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); d = pd.Series(np.asarray(dates))
    ok = x.notna(); x, d = x[ok], d[ok]
    g = x.groupby(pd.DatetimeIndex(d.values).to_period("M")).mean()
    if len(g) < 5 or g.std() == 0:
        return float("nan")
    return g.mean() / (g.std(ddof=1) / math.sqrt(len(g)))


def per(x, a, z):
    return x[(x.date >= a) & (x.date < z)]


def div_section(E):
    """The pre-set divergence pass check (NEW names = out-of-sample), plus info rows."""
    L = ["## 0. DIVERGENCE PASS CHECK (set before running)",
         "10/20 cross -> retest of the 10 SMA that closes back under -> hourly bearish divergence that day. "
         "NEW names only (not in the first run): 100+ entries, edge vs random positive in 2016-21 AND 2022-26 on 5-day "
         "or NET 10-day, t >= 2.5. Edge = how much more it fell than a random day, % of price. Other rows are info only.", "",
         "| Break | Names | Divergence? | Entries | 5-day edge (2016-21 / 2022-26) | t | NET 10-day edge (2016-21 / 2022-26) | t | Dropped 5% in 20d (random) | Verdict |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    if "hdiv" not in E:
        return L + ["(no hourly data: divergence not measured)", ""]
    R = E[E.entry.str.startswith("E1 ") & E.hdiv.notna()]
    first = [g for g in GROUPS if g != "NEW"]
    rows = [("X1020", "NEW", ["NEW"], True), ("X1020", "first-run 50", first, False), ("X1020", "all", list(GROUPS), False),
            ("TRIPLE", "NEW", ["NEW"], False), ("TRIPLE", "all", list(GROUPS), False)]
    for setup, lab, gs, judged in rows:
        for dv, dl in ((1.0, "yes"), (0.0, "no")):
            x = R[(R.setup == setup) & R.group.isin(gs) & (R.hdiv == dv)]
            if len(x) < 8:
                continue
            cells, ok = [], False
            for k in ("x5", "net10"):
                e = x[k] - x[f"all_{k}"]
                pe = [(per(x, a, z)[k] - per(x, a, z)[f"all_{k}"]).mean() for _, a, z in PD[1:]]
                t = tcl(e, x.date.values)
                cells += [f"{e.mean():+.2f}% ({' / '.join('—' if pd.isna(p) else f'{p:+.2f}' for p in pe)})", f"{t:.1f}"]
                if len(x) >= 100 and all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 2.5:
                    ok = True
            verdict = ("**PASS**" if ok else "fail") if (judged and dv == 1.0) else "info"
            L.append(f"| {setup} | {lab} | {dl} | {len(x)} | " + " | ".join(cells) +
                     f" | {x.hit5.mean():.0%} ({x.all_hit5.mean():.0%}) | {verdict} |")
    return L + [""]


def report(E):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    L = ["# Retest + hourly divergence: big run (about 300 names)", "",
         "Puts direction: positive = it fell. Random = every day of the same name and period. NET = deepest drop minus "
         "highest rise. t clustered by month.", ""]
    L += div_section(E)
    L += ["## 1. What happens first after the break (next 10 sessions)\n", "| Break | Group | Breaks | Retest first | Down first | Same day | Neither |",
          "|---|---|---|---|---|---|---|"]
    B = E[E.entry == "E0 break close"]
    for s in ("TRIPLE", "X1020"):
        for g in list(GROUPS) + ["QQQ"]:
            x = B[(B.setup == s) & ((B.group == g) if g in GROUPS else (B.symbol == g))]
            if len(x):
                vc = x.order.value_counts(normalize=True)
                L.append(f"| {s} | {g} | {len(x)} | {vc.get('retest first', 0):.0%} | {vc.get('down first', 0):.0%} | "
                         f"{vc.get('same day', 0):.0%} | {vc.get('neither', 0):.0%} |")
    L += ["\n## PASS CHECK (set before running): 100+ entries, vs random, positive in every period, t >= 3.5, on 5d / 10d / NET 10d\n",
          "| Break | Entry | Group | Entries | Passes on | Strongest |", "|---|---|---|---|---|---|"]
    for s in ("TRIPLE", "X1020"):
        for en in sorted(E.entry.unique()):
            for g in GROUPS:
                x = E[(E.setup == s) & (E.entry == en) & (E.group == g)]
                if not len(x):
                    continue
                hits, best = [], None
                for k in ("x5", "x10", "net10"):
                    e = x[k] - x[f"all_{k}"]
                    pe = [(per(x, a, z)[k] - per(x, a, z)[f"all_{k}"]).mean() for _, a, z in PD]
                    t = tcl(e, x.date.values)
                    if len(x) >= 100 and all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3.5:
                        hits.append(k)
                    if pd.notna(t) and (best is None or t > best[2]):
                        best = (k, e.mean(), t, pe)
                ev = f"{best[0]}: {best[1]:+.2f} (t {best[2]:.1f}; {' / '.join('—' if pd.isna(p) else f'{p:+.2f}' for p in best[3])})" if best else "—"
                L.append(f"| {s} | {en} | {g} | {len(x)} | {'**' + ', '.join(hits) + '**' if hits else 'nothing'} | {ev} |")
    L += ["\n## 2. Entry vs entry (edge vs random, in % of price; t)\n",
          "| Break | Group | Entry | Entries | Waited (median sessions) | 1d | 3d | 5d | 10d | 20d | NET 10d | Dropped 5% in 20d |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in ("TRIPLE", "X1020"):
        for g in list(GROUPS) + ["QQQ"]:
            for en in sorted(E.entry.unique()):
                x = E[(E.setup == s) & (E.entry == en) & ((E.group == g) if g in GROUPS else (E.symbol == g))]
                if len(x) < 8:
                    continue
                cells = [f"{(x[k] - x[f'all_{k}']).mean():+.2f} (t {tcl(x[k] - x[f'all_{k}'], x.date.values):.1f})" for k in ("x1", "x3", "x5", "x10", "x20", "net10")]
                L.append(f"| {s} | {g} | {en} | {len(x)} | {x.wait.median():.0f} | " + " | ".join(cells) + f" | {x.hit5.mean():.0%} vs {x.all_hit5.mean():.0%} |")
    L += ["\n## 3. Retest beats the break? (10-day edge by period: E1 minus E0)\n", "| Break | Group | 2000-15 | 2016-21 | 2022-26 | Verdict |", "|---|---|---|---|---|---|"]
    for s in ("TRIPLE", "X1020"):
        for g in GROUPS:
            d = []
            for _, a, z in PD:
                e1 = per(E[(E.setup == s) & (E.group == g) & (E.entry.str.startswith("E1 "))], a, z)
                e0 = per(E[(E.setup == s) & (E.group == g) & (E.entry.str.startswith("E0"))], a, z)
                d.append((e1.x10 - e1.all_x10).mean() - (e0.x10 - e0.all_x10).mean() if len(e1) and len(e0) else np.nan)
            ok = all(pd.notna(v) and v > 0 for v in d)
            L.append(f"| {s} | {g} | " + " | ".join('—' if pd.isna(v) else f'{v:+.2f}' for v in d) + f" | {'retest better' if ok else 'not consistent'} |")
    if "hdiv" in E:
        L += ["\n## 4. Retest + hourly bearish divergence (2016+)\n", "| Break | Group | Divergence? | Entries | 1d | 3d | 5d | 10d | NET 10d |", "|---|---|---|---|---|---|---|---|---|"]
        R = E[E.entry.str.startswith("E1 ") & E.hdiv.notna()]
        for s in ("TRIPLE", "X1020"):
            for g in list(GROUPS) + ["ALL"]:
                for dv, lab in ((1.0, "yes"), (0.0, "no")):
                    x = R[(R.setup == s) & (R.hdiv == dv) & ((R.group == g) if g in GROUPS else True)]
                    if len(x) < 8:
                        continue
                    cells = [f"{(x[k] - x[f'all_{k}']).mean():+.2f} (t {tcl(x[k] - x[f'all_{k}'], x.date.values):.1f})" for k in ("x1", "x3", "x5", "x10", "net10")]
                    L.append(f"| {s} | {g} | {lab} | {len(x)} | " + " | ".join(cells) + " |")
    q = E[(E.symbol == "QQQ") & (E.date >= "2022-01-01")].sort_values(["break_date", "entry"])
    L += ["\n## QQQ since 2022: each break, what came first, and each entry (+ = it fell)\n",
          "| Break date | Break | First | Entry | Entry date | 3d | 10d | 20d |", "|---|---|---|---|---|---|---|---|"]
    for r in q.itertuples():
        L.append(f"| {r.break_date:%Y-%m-%d} | {r.setup} | {r.order} | {r.entry} | {r.date:%Y-%m-%d} | {r.x3:+.1f}% | {r.x10:+.1f}% | {r.x20:+.1f}% |")
    L += ["", "Limits: today's names (survivorship hurts puts); stock moves, not option prices; daily bars can't tell the "
          "order of a retest and a new low on the same day ('same day')."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    if not akeys():
        print("  No Alpaca keys: hourly divergence part skipped.")
    E = []
    GROUPS["NEW"] = new_names()
    print(f"  {sum(len(v) for v in GROUPS.values())} names ({len(GROUPS['NEW'])} new)", flush=True)
    for g, syms in GROUPS.items():
        for s in syms:
            try:
                run_symbol(s, g, E)
            except Exception as ex:
                print(f"  {s}: {ex}"); continue
            print(f"  {s}: entries so far {len(E)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/events.csv.gz", index=False, compression="gzip")
    report(E)


if __name__ == "__main__":
    main()
