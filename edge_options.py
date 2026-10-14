"""
EDGE SEARCH, STAGE 2: real option prices for every stage-1 survivor (Feb 2024 -> now, Alpaca 1-minute option trades).

Reads results/edge_search/survivors.csv + events_2024.csv.gz. For each survivor (up to 20), up to 120 of its signals
(spread over time, fixed random seed), direction from stage 1 (calls if the edge was up, puts if down).
Taz's rules: expiry a week or more out (first expiry at least 7 days away and after the exit), no 0DTE.
THREE CONTRACT CHOICES:
  single ATM, single 0.5% OTM, and a DEBIT SPREAD (buy ATM, sell the strike ~1% further out).
  Every trade is flagged under / over $500 (single: price x 100; spread: net debit x 100).
PRICES: first real trade at/after the planned minute within 30 minutes (entry and exit); if none at exit, the last
  trade before it that day. No trade = not counted.
COSTS (assumption; Alpaca has no historical bid/ask): max($0.02, 1% of price) against you on every leg, each way.
  'Stress' doubles it.
RANDOM: each signal gets one random session (not a signal day) with the same clock time, hold and contract rule.
VERDICT (set before running), per survivor: MAKES MONEY if any of the 3 contract choices has 30+ signal days with
  average return after costs > 0 AND above random, t >= 2.5 on both (t clustered by entry date).
Out: results/edge_options/report.md, trades.csv
"""
from __future__ import annotations
import os, math
import numpy as np, pandas as pd
import option_reality as orl

OUT = "results/edge_options"
SRC = "results/edge_search"
MAX_SURV, MAX_EV, WITHIN = 20, 120, 30
INTRA = {"15m": 15, "30m": 30, "1h": 60, "2h": 120}


def price_after(b, t):
    x = b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=WITHIN))]
    return float(x.c.iloc[0]) if len(x) else np.nan


def price_exit(b, t):
    p = price_after(b, t)
    if np.isnan(p):
        x = b[(b.t <= t) & (b.t >= t.normalize())]
        p = float(x.c.iloc[-1]) if len(x) else np.nan
    return p


STOCK = {}


def stock(sym):
    if sym not in STOCK:
        d = orl.stock_bars(sym, "1Day", "2024-01-01T00:00:00Z")
        m = orl.stock_bars(sym, "5Min", "2024-01-15T00:00:00Z")
        m = m[(m.t.dt.hour * 60 + m.t.dt.minute >= 570) & (m.t.dt.hour * 60 + m.t.dt.minute < 960)].copy()
        m["end"] = m.t + pd.Timedelta(minutes=5)
        STOCK[sym] = (pd.DatetimeIndex(d.t.dt.normalize().unique()), m)
    return STOCK[sym]


def spot_at(m, t):
    x = m[(m.end <= t) & (m.end > t - pd.Timedelta(hours=18))]
    return float(x.c.iloc[-1]) if len(x) else np.nan


def exit_time(entry, hold, days):
    day = entry.normalize(); close = day + pd.Timedelta(hours=15, minutes=55)
    if hold in INTRA:
        return min(entry + pd.Timedelta(minutes=INTRA[hold]), close)
    if hold == "close":
        return close
    k = int(hold[0]); pos = days.searchsorted(day)
    return days[pos + k] + pd.Timedelta(hours=15, minutes=55) if pos + k < len(days) else None


def leg_cost(px, m):
    return max(0.02, 0.01 * px) * m


def price_trade(sym, entry, hold, cp, days, m5):
    if entry.hour * 60 + entry.minute >= 958:                 # daily signals: buy at 3:55 pm
        entry = entry.normalize() + pd.Timedelta(hours=15, minutes=55)
    ex = exit_time(entry, hold, days)
    if ex is None or ex <= entry:
        return []
    spot = spot_at(m5, entry)
    if not np.isfinite(spot):
        return []
    C = orl.contracts(sym, entry.normalize(), cp, spot)
    if not len(C):
        return []
    need = max(entry.normalize() + pd.Timedelta(days=7), ex.normalize())
    c = C[C.exp >= need]
    if not len(c):
        return []
    c = c[c.exp == c.exp.min()]
    atm = c.iloc[(c.k - spot).abs().argmin()]
    if cp == "C":
        o5 = c[c.k >= spot * 1.005].sort_values("k"); w1 = c[c.k >= spot * 1.01].sort_values("k")
    else:
        o5 = c[c.k <= spot * 0.995].sort_values("k", ascending=False); w1 = c[c.k <= spot * 0.99].sort_values("k", ascending=False)
    otm = o5.iloc[0] if len(o5) else None
    short = w1.iloc[0] if len(w1) else None
    occs = sorted({x.occ for x in (atm, otm, short) if x is not None})
    B = orl.option_bars(occs, entry.normalize() + pd.Timedelta(hours=9, minutes=30), ex + pd.Timedelta(minutes=WITHIN + 5))
    rows = []

    def px(x):
        b = B.get(x.occ) if x is not None else None
        if b is None:
            return np.nan, np.nan
        return price_after(b, entry), price_exit(b, ex)

    for lab, leg in (("single ATM", atm), ("single 0.5% OTM", otm)):
        a, z = px(leg)
        if np.isfinite(a) and np.isfinite(z) and a > 0:
            rec = dict(contract=lab, occ=leg.occ, cost=a * 100)
            for nm, mm in (("ret", 1), ("stress", 2)):
                rec[nm] = ((z - leg_cost(z, mm)) / (a + leg_cost(a, mm)) - 1) * 100
            rows.append(rec)
    if short is not None and short.occ != atm.occ:
        a1, z1 = px(atm); a2, z2 = px(short)
        if all(np.isfinite([a1, z1, a2, z2])):
            rec = dict(contract="debit spread ATM / ~1% out", occ=f"{atm.occ}-{short.occ}")
            for nm, mm in (("ret", 1), ("stress", 2)):
                debit = (a1 + leg_cost(a1, mm)) - (a2 - leg_cost(a2, mm))
                value = (z1 - leg_cost(z1, mm)) - (z2 + leg_cost(z2, mm))
                rec[nm] = (value / debit - 1) * 100 if debit > 0.05 else np.nan
                if mm == 1:
                    rec["cost"] = debit * 100
            if np.isfinite(rec["ret"]):
                rows.append(rec)
    for r in rows:
        r.update(symbol=sym, entry=entry, hold=hold, spot=spot, under500=r["cost"] <= 500)
    return rows


def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); d = pd.Series(pd.DatetimeIndex(dates).normalize())
    ok = x.notna(); x, d = x[ok], d[ok]
    g = x.groupby(d.values).mean()
    if len(g) < 5 or g.std() == 0:
        return float("nan")
    return g.mean() / (g.std(ddof=1) / math.sqrt(len(g)))


def main():
    orl.HD = orl.keys()
    os.makedirs(OUT, exist_ok=True)
    try:
        S = pd.read_csv(f"{SRC}/survivors.csv")
        S = S[S.survives.astype(str).str.lower() == "true"].head(MAX_SURV)
    except FileNotFoundError:
        S = pd.DataFrame()
    if not len(S):
        open(f"{OUT}/report.md", "w").write("# Edge search, stage 2\n\nNo stage-1 survivors, so nothing to price.\n")
        print("No stage-1 survivors, nothing to price."); return
    E = pd.read_csv(f"{SRC}/events_2024.csv.gz", parse_dates=["entry"])
    rng = np.random.default_rng(11)
    rows = []
    for k, s in enumerate(S.itertuples(), 1):
        cp = "C" if s.edge_disc > 0 else "P"
        ev = E[(E.sig == s.sig) & (E.group == s.group) & (E[f"r_{s.regime}"].astype(str).str.lower() == "true")]
        if len(ev) > MAX_EV:
            ev = ev.iloc[np.sort(rng.choice(len(ev), MAX_EV, replace=False))]
        tag = f"{s.sig} | {s.group} | {s.regime} | {s.hold}"
        sig_days = set(zip(ev.symbol, ev.entry.dt.normalize()))
        for e in ev.itertuples():
            days, m5 = stock(e.symbol)
            for r in price_trade(e.symbol, e.entry, s.hold, cp, days, m5):
                rows.append(dict(r, survivor=tag, direction=cp, random=False))
            pool = [d for d in days[days >= orl.START] if (e.symbol, d) not in sig_days][:-6]
            if pool:
                d = pool[rng.integers(len(pool))]
                t = d + (e.entry - e.entry.normalize())
                for r in price_trade(e.symbol, t, s.hold, cp, days, m5):
                    rows.append(dict(r, survivor=tag, direction=cp, random=True))
        print(f"  [{k}/{len(S)}] {tag}: {len(ev)} signals priced, rows {len(rows)}", flush=True)
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/trades.csv", index=False)
    report(S, T)


def report(S, T):
    L = ["# Edge search, stage 2: do the survivors make money on real options?", "",
         "Real Alpaca option trades, Feb 2024 to now. Expiry a week+ out, no 0DTE. Returns per contract after an assumed "
         "cost of max($0.02, 1%) per leg each way ('stress' doubles it). Random = same trade, same clock time, a random "
         "non-signal session. t clustered by entry date.", "",
         "## 1. VERDICT per survivor (set before running: any contract choice with 30+ signal days, average > 0 and above "
         "random, t >= 2.5 on both)", "",
         "| Survivor (signal, names, regime, hold) | Direction | Best contract | Signal days | Avg cost | Under $500 | Avg return | Median | Win rate | Random avg | t (avg) | t (edge) | Verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    detail = ["", "## 2. Every contract choice", "",
              "| Survivor | Contract | Trades | Signal days | Avg cost | Under $500 | Avg return | Median | Win rate | Stress avg | Random avg | Edge | t (avg) | t (edge) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    if not len(T):
        L.append("| no trades could be priced | | | | | | | | | | | | |")
    for tag, g in (T.groupby("survivor") if len(T) else []):
        best, best_ok = None, False
        for con, x in g.groupby("contract"):
            sg, rd = x[~x.random], x[x.random]
            if len(sg) < 5:
                continue
            rmean = rd.ret.mean() if len(rd) else np.nan
            edge = sg.ret - (rmean if np.isfinite(rmean) else 0)
            r = dict(con=con, n=len(sg), days=sg.entry.dt.normalize().nunique(), cost=sg.cost.mean(),
                     u500=sg.under500.mean(), avg=sg.ret.mean(), med=sg.ret.median(), win=(sg.ret > 0).mean(),
                     st=sg.stress.mean(), rnd=rmean, edge=edge.mean(), ta=tcl(sg.ret, sg.entry), te=tcl(edge, sg.entry))
            ok = r["days"] >= 30 and r["avg"] > 0 and r["edge"] > 0 and r["ta"] >= 2.5 and r["te"] >= 2.5
            detail.append(f"| {tag} | {con} | {r['n']} | {r['days']} | ${r['cost']:,.0f} | {r['u500']:.0%} | {r['avg']:+.1f}% | "
                          f"{r['med']:+.1f}% | {r['win']:.0%} | {r['st']:+.1f}% | {r['rnd']:+.1f}% | {r['edge']:+.1f} | {r['ta']:.1f} | {r['te']:.1f} |")
            if best is None or (ok and not best_ok) or (ok == best_ok and (r["te"] if np.isfinite(r["te"]) else -9) > (best["te"] if np.isfinite(best["te"]) else -9)):
                best, best_ok = r, ok
        if best is None:
            continue
        L.append(f"| {tag} | {g.direction.iloc[0]} | {best['con']} | {best['days']} | ${best['cost']:,.0f} | {best['u500']:.0%} | "
                 f"{best['avg']:+.1f}% | {best['med']:+.1f}% | {best['win']:.0%} | {best['rnd']:+.1f}% | {best['ta']:.1f} | {best['te']:.1f} | "
                 f"{'**MAKES MONEY**' if best_ok else ('too few' if best['days'] < 30 else 'no')} |")
    L += detail
    L += ["", "Limits: Feb 2024 onward only; trade prints, not bid/ask (cost line is an assumption); up to 120 signals per "
          "survivor. Not financial advice."]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
