"""
Grade Taz's Discord calls against real prices.
==============================================
Input: calls.csv (extracted from his own Discord messages, 2024-2026): time (UTC), ticker,
direction (bear = top/puts/short, bull = bottom/calls/long), tier:
   A = explicit trade call (strike / "took puts" / "calls at the open" ...): direction is unambiguous
   B = directional comment found by keywords: noisier (the classifier gets roughly 1 in 4 wrong)
Only forecasts are included: questions and after-the-fact result posts ("paid", "congrats",
"sold", ...) were removed. One call per ticker per day per direction.

Entry price = the stock's price when the call was posted (15-min bar), or the next open if the
call came outside market hours.

For each call:
  - move in the call's direction at the entry-day close, +1, +3, +5, +10 trading days
  - same, minus SPY's move over the same window ("vs market")
  - TARGET-FIRST: did the stock move 1 ATR (its normal daily range) in the call's direction
    before it moved 1 ATR against, within 10 days?
  - CONTROL: the same measurements for 10 random tickers from the names Taz calls most,
    at the same minute, same direction. Skill = calls beat the control.
Free (Alpaca). Out: results/call_grades/{report.md, graded_calls.csv}
"""
from __future__ import annotations
import os, math
import numpy as np, pandas as pd
import setup_backtest as sb

OUT = "results/call_grades"
NY = "America/New_York"
H = [0, 1, 3, 5, 10]
rng = np.random.default_rng(7)


def load():
    C = pd.read_csv("calls.csv")
    C["t"] = pd.to_datetime(C.ts_utc).dt.tz_localize("UTC").dt.tz_convert(NY)
    C = C[C.ticker != "VIX"].copy()
    return C.reset_index(drop=True)


def fetch_all(syms, start, end):
    D, M = {}, {}
    for i in range(0, len(syms), 20):
        ch = syms[i:i + 20]
        try:
            d = sb.fetch(ch, "1Day", start, end); m = sb.fetch(ch, "15Min", start, end)
        except Exception as ex:
            print("fetch", ch[:3], ex); continue
        for s in ch:
            x = d[d.symbol == s].copy()
            if len(x):
                x["day"] = x.t.dt.tz_localize(None).dt.normalize()
                x = x.set_index("day").sort_index()
                pc = x.c.shift()
                tr = np.maximum(x.h - x.l, np.maximum((x.h - pc).abs(), (x.l - pc).abs()))
                x["atr"] = tr.rolling(14).mean().shift()          # known before the day
                D[s] = x
            y = m[m.symbol == s].copy()
            if len(y):
                y["end"] = y.t + pd.Timedelta(minutes=15)
                M[s] = y.sort_values("t").reset_index(drop=True)
        print(f"  prices {min(i + 20, len(syms))}/{len(syms)}", flush=True)
    return D, M


def entry_point(sym, t, D, M):
    """(entry price, index of entry day in daily frame)."""
    d = D.get(sym)
    if d is None:
        return None
    day = pd.Timestamp(t.date())
    tod = t.hour * 60 + t.minute
    if day in d.index and 570 <= tod < 960 and sym in M:
        m = M[sym]
        k = np.searchsorted(m.end.values, np.datetime64(t.tz_convert("UTC").tz_localize(None)), side="right") - 1
        if k >= 0 and m.t.iloc[k].date() == t.date():
            return float(m.c.iloc[k]), d.index.get_loc(day)
    # before the open -> that day's open; after the close / non-trading day -> next open
    later = d.index[d.index > day] if tod >= 960 or day not in d.index else d.index[d.index >= day]
    if len(later) == 0:
        return None
    j = d.index.get_loc(later[0])
    return float(d.o.iloc[j]), j


def measure(sym, t, sgn, D, M, spy_entry):
    ep = entry_point(sym, t, D, M)
    if ep is None:
        return None
    px, j = ep
    d = D[sym]; s = D["SPY"]
    out = {}
    for n in H:
        if j + n >= len(d):
            out[f"m{n}"] = out[f"x{n}"] = np.nan; continue
        r = d.c.iloc[j + n] / px - 1
        out[f"m{n}"] = sgn * r * 100
        day_n = d.index[j + n]
        if spy_entry is not None and day_n in s.index:
            out[f"x{n}"] = sgn * (r - (s.c.loc[day_n] / spy_entry - 1)) * 100
        else:
            out[f"x{n}"] = np.nan
    atr = d.atr.iloc[j]
    hit = np.nan
    if atr == atr and atr > 0:
        up, dn = px + atr, px - atr
        hit = 0
        for k in range(j, min(j + 11, len(d))):
            good = d.l.iloc[k] <= dn if sgn < 0 else d.h.iloc[k] >= up
            bad = d.h.iloc[k] >= up if sgn < 0 else d.l.iloc[k] <= dn
            if good and not bad:
                hit = 1; break
            if bad:
                break                     # both in one day counts against the call (conservative)
    out["target_first"] = hit
    return out


def tstat(v, days):
    v = pd.Series(np.asarray(v, dtype=float)); dd = pd.Series(np.asarray(days))
    ok = v.notna()
    x, dd = v[ok], dd[ok]
    if len(x) < 5:
        return float("nan")
    dm = x.groupby(dd.values).mean()
    return dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")


def main():
    os.makedirs(OUT, exist_ok=True)
    C = load()
    top = C.ticker.value_counts().head(50).index.tolist()
    syms = sorted(set(C.ticker) | set(top) | {"SPY"})
    start = (C.t.min() - pd.Timedelta(days=40)).date().isoformat()
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    D, M = fetch_all(syms, start, end)
    rows = []
    for _, c in C.iterrows():
        sgn = -1 if c.dir == "bear" else 1
        sp = entry_point("SPY", c.t, D, M)
        spy_entry = sp[0] if sp else None
        r = measure(c.ticker, c.t, sgn, D, M, spy_entry)
        if r is None:
            continue
        ctrl = []
        pool = [x for x in top if x != c.ticker and x in D]
        for x in rng.choice(pool, size=min(10, len(pool)), replace=False):
            q = measure(x, c.t, sgn, D, M, spy_entry)
            if q:
                ctrl.append(q)
        row = {**c.drop(labels=["t"]).to_dict(), "day": c.t.date(), **r}
        if ctrl:
            Q = pd.DataFrame(ctrl).mean()
            for k, v in Q.items():
                row["ctrl_" + k] = v
        rows.append(row)
    G = pd.DataFrame(rows)
    G.to_csv(f"{OUT}/graded_calls.csv", index=False)
    report(G)


def line(name, x):
    if len(x) < 5:
        return None
    cells = [f"| {name} | {len(x)} |"]
    for n in (1, 3, 5, 10):
        v = x[f"x{n}"]; dlt = (x[f"x{n}"] - x[f"ctrl_x{n}"]).values
        cells.append(f" {v.mean():+.2f}% ({(v > 0).mean():.0%}) vs ctrl {x[f'ctrl_x{n}'].mean():+.2f}% → edge {dlt.mean():+.2f} (t {tstat(dlt, x.day.values):.1f}) |")
    tf = x.target_first.dropna(); ctf = x.ctrl_target_first.dropna()
    cells.append(f" {tf.mean():.0%} vs ctrl {ctf.mean():.0%} |")
    return "".join(cells)


HDR = ("| Group | Calls | 1 day | 3 days | 5 days | 10 days | Target-first (1 ATR) |\n"
       "|---|---|---|---|---|---|---|")


def report(G):
    G = G.copy()
    G["year"] = pd.to_datetime(G.day).dt.year
    L = ["# Your calls, graded",
         f"\n{len(G)} calls from your Discord ({G.day.min()} to {G.day.max()}). Each cell: average move in your call's "
         "direction **vs the market (SPY)** (share that went your way) vs the CONTROL (random names you trade, same minute, "
         "same direction) → your EDGE over the control (t, clustered by day). Target-first = reached 1 ATR your way "
         "before 1 ATR against within 10 days.\n",
         "## Headline\n", HDR]
    for name, m in (("Tier A — explicit trade calls", G.tier == "A"), ("Tier B — keyword calls (noisier)", G.tier == "B"),
                    ("All calls", G.tier.notna())):
        L.append(line(name, G[m]))
    for tier in ("A", "B"):
        X = G[G.tier == tier]
        L += [f"\n## Tier {tier} by direction and year\n", HDR]
        for name, m in (("TOPS / bearish calls", X.dir == "bear"), ("Bottoms / bullish calls", X.dir == "bull")):
            L.append(line(name, X[m]))
        for y in sorted(X.year.unique()):
            L.append(line(f"{y}", X[X.year == y]))
    L += ["\n## By ticker (all tiers, 10+ calls)\n", HDR]
    for tk, x in G.groupby("ticker"):
        if len(x) >= 10:
            L.append(line(tk, x))
    L += ["\n## The names you mentioned — every bearish call\n",
          "| Date | Ticker | Tier | 1 day | 5 days | 10 days | Target-first |", "|---|---|---|---|---|---|---|"]
    for _, r in G[(G.ticker.isin(["TSLA", "INTC", "SLV", "GLD", "USO", "COIN", "MSTR", "NFLX", "AMD"])) & (G.dir == "bear")].sort_values("day").iterrows():
        tf = "yes" if r.target_first == 1 else ("no" if r.target_first == 0 else "—")
        L.append(f"| {r.day} | {r.ticker} | {r.tier} | {r.x1:+.1f}% | {r.x5:+.1f}% | {r.x10:+.1f}% | {tf} |")
    L += ["\n## How to read\n",
          "- 'vs the market' removes the market's own move, so a falling market can't flatter bearish calls.",
          "- EDGE is the honest number: your calls minus random calls in the same names at the same minute.",
          "- t >= 2 = likely real, t >= 3 = strong. Tier A is the clean read; Tier B includes misread messages.",
          "- Calls are what you POSTED, traded or not."]
    open(f"{OUT}/report.md", "w").write("\n".join(x for x in L if x) + "\n"); print("\n".join(x for x in L if x))


if __name__ == "__main__":
    main()
