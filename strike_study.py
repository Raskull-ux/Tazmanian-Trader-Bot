"""
Strike-distance study — how far from the stock should Taz buy?
==============================================================
Contract price alone is a blunt proxy. This measures, for every option position
since 2024 (all accounts), exactly where the strike sat relative to the stock
at the moment of entry, three ways:

  pct_otm   distance from the stock price, % (negative = in the money)
  sd_otm    that distance in units of the stock's expected move over the
            option's life (comparable across stocks and expiries)
  delta     the option's real delta, computed from the implied volatility
            backed out of Taz's OWN fill price (not a model guess)

Stock price at entry:
  - fills with a real time (Robinhood emails): the 5-min bar at that minute
  - fills with a date only: that day's VWAP (labelled; less precise)
Prices are UNADJUSTED for splits, so they match the strikes as traded.

Then: results by delta / distance bucket within each expiry group, the same
split by period (before, best run, after), and a walk-forward cutoff: the delta
floor that would have helped most on 2024 - Oct 2025, scored on Nov 2025 onward.

Free (Alpaca stock data). Out: results/strike_study/{report.md, positions.csv}
"""
from __future__ import annotations
import os, glob, math, time
import numpy as np, pandas as pd, requests
from scipy.special import ndtr
from scipy.optimize import brentq
import setup_backtest as sb

OUT = "results/strike_study"
START = "2024-01-01"
BEST = (pd.Timestamp("2025-11-01"), pd.Timestamp("2026-04-30"))


def fetch_raw(symbols, tf, start, end):
    """Like sb.fetch but UNADJUSTED prices and keeps VWAP."""
    rows, token = [], None
    while True:
        p = {"symbols": ",".join(symbols), "timeframe": tf, "start": start, "end": end,
             "feed": "sip", "adjustment": "raw", "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get(sb.DATA, headers=sb._hdr(), params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            raise RuntimeError(f"{tf} {r.status_code}: {r.text[:200]}")
        j = r.json()
        for sym, bars in (j.get("bars") or {}).items():
            for b in bars:
                rows.append((sym, b["t"], b["o"], b["h"], b["l"], b["c"], b["v"], b.get("vw", np.nan)))
        token = j.get("next_page_token")
        if not token:
            break
    df = pd.DataFrame(rows, columns=["symbol", "t", "o", "h", "l", "c", "v", "vw"])
    if len(df):
        df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert(sb.NY)
    return df


def positions():
    path = sorted(glob.glob("Tazmanian_Trade_Record*.xlsx"))[-1]
    r = pd.read_excel(path, "Raw Fills (All Accounts)", header=3)
    r["Date"] = pd.to_datetime(r["Date"]).dt.normalize()
    r = r[r.Date >= START].copy()
    r["Expiry"] = pd.to_datetime(r["Expiry"], errors="coerce")
    r["Side"] = r["Side"].astype(str).str.upper()
    r["put"] = r["Type"].astype(str).str.lower().str.startswith("p")
    r["cash"] = r["Qty"] * r["Price"] * 100
    r["row"] = range(len(r))
    rows = []
    for key, g in r.groupby(["Account", "Symbol", "Expiry", "put", "Strike"]):
        b = g[g.Side == "BUY"].sort_values(["Date", "Time (ET)", "row"], na_position="last")
        s = g[g.Side == "SELL"]
        if b.empty or pd.isna(key[2]):
            continue
        bq, sq = b.Qty.sum(), s.Qty.sum()
        cost, proceeds = b.cash.sum(), s.cash.sum() * (min(1, bq / sq) if sq else 1)
        f = b.iloc[0]
        t = None
        if pd.notna(f["Time (ET)"]):
            t = pd.Timestamp(f"{f.Date:%Y-%m-%d} {f['Time (ET)']}").tz_localize(sb.NY)
        rows.append(dict(account=key[0], symbol=str(key[1]).upper(), expiry=key[2], put=key[3],
                         strike=float(key[4]), entry=f.Date, entry_t=t, price=float(f.Price),
                         qty=float(f.Qty), cost=cost, net=proceeds - cost,
                         ret=proceeds / cost - 1 if cost > 0 else np.nan))
    P = pd.DataFrame(rows)
    P["dte"] = (P.expiry - P.entry).dt.days
    return P[P.dte >= 0].reset_index(drop=True)


def years_left(entry_t, entry_day, dte):
    mins = 16 * 60 - (entry_t.hour * 60 + entry_t.minute) if pd.notna(entry_t) else 195  # midday if unknown
    mins = max(mins, 5)
    return (mins + 390 * np.busday_count(entry_day.date(), (entry_day + pd.Timedelta(days=int(dte))).date())) / (390 * 252)


def bs(S, K, T, sig, put):
    v = sig * math.sqrt(T); d1 = (math.log(S / K) + 0.5 * v * v) / v
    call = S * ndtr(d1) - K * ndtr(d1 - v)
    return (call - S + K) if put else call, d1


def implied(S, K, T, price, put):
    intrinsic = max(K - S, 0) if put else max(S - K, 0)
    if price <= intrinsic + 0.005 or T <= 0:
        return np.nan
    f = lambda s: bs(S, K, T, s, put)[0] - price
    try:
        if f(0.01) > 0 or f(8.0) < 0:
            return np.nan
        return brentq(f, 0.01, 8.0, xtol=1e-4)
    except Exception:
        return np.nan


def main():
    os.makedirs(OUT, exist_ok=True)
    P = positions()
    print(f"Positions since {START}: {len(P)} | with real entry time: {P.entry_t.notna().sum()}")
    syms = sorted(P.symbol.unique())
    s0 = (P.entry.min() - pd.Timedelta(days=40)).date().isoformat()
    cap = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    D, M = {}, {}
    timed_days = P[P.entry_t.notna()].groupby("symbol").entry.agg(["min", "max"])
    for i in range(0, len(syms), 25):
        ch = syms[i:i + 25]
        d = fetch_raw(ch, "1Day", s0, cap)
        for s in ch:
            x = d[d.symbol == s].copy()
            x["day"] = x.t.dt.tz_localize(None).dt.normalize()
            x["rv20"] = np.log(x.c).diff().rolling(20).std().shift() * math.sqrt(252)
            D[s] = x.set_index("day")
        tch = [s for s in ch if s in timed_days.index]
        if tch:
            lo = (timed_days.loc[tch, "min"].min()).date().isoformat()
            hi = min((timed_days.loc[tch, "max"].max() + pd.Timedelta(days=1)).tz_localize("UTC"),
                     pd.Timestamp(cap)).isoformat()
            m = fetch_raw(tch, "5Min", lo, hi)
            for s in tch:
                y = m[m.symbol == s].copy()
                y["end"] = y.t + pd.Timedelta(minutes=5)
                M[s] = y.sort_values("t").reset_index(drop=True)
        print(f"  prices: {min(i + 25, len(syms))}/{len(syms)}", flush=True)

    out = []
    for _, p in P.iterrows():
        d = D.get(p.symbol)
        if d is None or p.entry not in d.index:
            continue
        row = d.loc[p.entry]
        S, src = row.vw if row.vw == row.vw else (row.h + row.l + row.c) / 3, "day VWAP"
        if pd.notna(p.entry_t) and p.symbol in M:
            m = M[p.symbol]
            k = np.searchsorted(m.end.values, np.datetime64(p.entry_t.tz_convert("UTC").tz_localize(None)), side="right") - 1
            if k >= 0 and m.t.iloc[k].date() == p.entry.date():
                S, src = m.c.iloc[k], "exact minute"
        T = years_left(p.entry_t, p.entry, p.dte)
        pct = ((S - p.strike) if p.put else (p.strike - S)) / S * 100
        rv = row.rv20 if row.rv20 == row.rv20 else np.nan
        sd = pct / 100 / (rv * math.sqrt(T)) if rv == rv and rv > 0 else np.nan
        iv = implied(S, p.strike, T, p.price, p.put)
        delta = np.nan
        if iv == iv:
            _, d1 = bs(S, p.strike, T, iv, p.put)
            delta = abs(ndtr(d1) - (1 if p.put else 0))
        out.append({**p.to_dict(), "S": S, "s_source": src, "pct_otm": pct, "sd_otm": sd, "iv": iv, "delta": delta})
    R = pd.DataFrame(out)
    R["period"] = np.where(R.entry < BEST[0], "before", np.where(R.entry <= BEST[1], "best run", "after"))
    R["dteg"] = pd.cut(R.dte, [-1, 0, 3, 14, 9999], labels=["0DTE", "1-3 days", "4-14 days", "15+ days"])
    R.to_csv(f"{OUT}/positions.csv", index=False)
    report(R)


def fmt(x):
    if len(x) == 0:
        return "| 0 | | | | |"
    v = x.ret.clip(upper=5)
    dm = v.groupby(x.entry.values).mean()
    t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")
    return f"| {len(x)} | {(x.net > 0).mean():.0%} | {v.mean()*100:+.0f}% (t {t:.1f}) | {x.ret.median()*100:+.0f}% | ${x.net.sum():,.0f} |"


H = "| Bucket | Positions | Win rate | Avg return | Median | Net $ |\n|---|---|---|---|---|---|"
DB = [0, 0.10, 0.20, 0.30, 0.40, 0.50, 1.01]
DL = ["delta <0.10", "0.10-0.20", "0.20-0.30", "0.30-0.40", "0.40-0.50", "0.50+ (in the money)"]


def report(R):
    R = R.copy()
    R["db"] = pd.cut(R.delta, DB, labels=DL, right=False)
    R["pb"] = pd.cut(R.pct_otm, [-99, 0, 0.5, 1, 2, 4, 999], labels=["in the money", "0-0.5% OTM", "0.5-1%", "1-2%", "2-4%", "4%+ OTM"], right=False)
    exact = R.s_source.eq("exact minute").mean()
    L = ["# Strike-distance study — how far out of the money should you buy?",
         f"\n{len(R)} positions since 2024, all accounts. Stock price at entry: exact minute for "
         f"{exact:.0%}, that day's VWAP for the rest. Delta from implied vol backed out of YOUR fill price "
         f"(available for {R.delta.notna().mean():.0%}). Avg return capped at +500% per trade; t clustered by day.\n",
         "## 1. By delta (all expiries)\n", H]
    L += [f"| {lab} " + fmt(R[R.db == lab]) for lab in DL]
    L += ["\n## 2. By distance from the stock price\n", H]
    L += [f"| {lab} " + fmt(R[R.pb == lab]) for lab in R.pb.cat.categories]
    L += ["\n## 3. Delta within each expiry group (does it hold at every expiry?)\n"]
    for g in R.dteg.cat.categories:
        x = R[R.dteg == g]
        if len(x) < 30:
            continue
        L += [f"\n**{g}**\n", H] + [f"| {lab} " + fmt(x[x.db == lab]) for lab in DL if (x.db == lab).sum()]
    L += ["\n## 4. Delta by period (does it hold before, during and after the best run?)\n"]
    for per in ["before", "best run", "after"]:
        x = R[R.period == per]
        L += [f"\n**{per}** — median delta bought: {x.delta.median():.2f}, "
              f"share at delta >= 0.30: {(x.delta >= 0.30).mean():.0%}\n", H] + \
             [f"| {lab} " + fmt(x[x.db == lab]) for lab in DL if (x.db == lab).sum()]
    # walk-forward delta floor
    tr, te = R[R.period == "before"], R[R.period != "before"]
    best, best_v = None, -1e9
    for fl in [0, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
        x = tr[tr.delta >= fl]
        if len(x) >= 100 and x.ret.clip(upper=5).mean() > best_v:
            best, best_v = fl, x.ret.clip(upper=5).mean()
    L += ["\n## 5. Walk-forward delta floor\n",
          f"Picked on Jan 2024 - Oct 2025 only: **buy delta >= {best:.2f}**. Scored on Nov 2025 - Sep 2026:\n", H,
          "| Nov 2025+, everything " + fmt(te[te.delta.notna()]),
          f"| Nov 2025+, delta >= {best:.2f} " + fmt(te[te.delta >= best]),
          f"| Nov 2025+, delta < {best:.2f} " + fmt(te[te.delta < best])]
    L += ["\n## Notes\n",
          "- Exact-minute prices make delta precise; VWAP-based rows can be off when the stock moved a lot that day.",
          "- Positions with no delta: fill at or below intrinsic value, or an unrealistic implied vol.",
          "- This measures what WAS bought; it doesn't prove a deeper strike would have won on the same idea, "
          "but it shows where your results come from."]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
