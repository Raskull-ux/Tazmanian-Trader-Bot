"""
Direction test — was Taz right on DIRECTION, independent of entry timing and option choice?
For each of the 576 exact-time trades: the underlying stock's move in the trade's direction
(put = down is right, call = up is right) from the entry minute to:
  +30 min, +60 min, same-day close, next-day close, 3-day close, 5-day close
plus the best favorable and worst adverse move within 5 days (was he early, or wrong?).
Real Alpaca stock prices; no option pricing involved. Read-only analysis, saves a report.
"""
import os, math
from datetime import timedelta
import numpy as np, pandas as pd
import setup_backtest as sb
import entries_study as es

OUT = "results/direction_test"
H = ["30min", "60min", "close", "next_close", "3d_close", "5d_close"]


def main():
    os.makedirs(OUT, exist_ok=True)
    tr = es.load_trades()
    start = (tr.entry_t.min() - timedelta(days=5)).date().isoformat()
    end = (tr.entry_t.max() + timedelta(days=12)).date().isoformat()
    syms = sorted(tr.Symbol.astype(str).unique())
    m5, d1 = {}, {}
    for i in range(0, len(syms), 20):
        ch = syms[i:i + 20]
        a = sb.fetch(ch, "5Min", start, end); b = sb.fetch(ch, "1Day", start, end)
        for s in ch:
            x = a[a.symbol == s].sort_values("t").reset_index(drop=True)
            x["end"] = x["t"] + pd.Timedelta(minutes=5)
            m5[s] = x; d1[s] = b[b.symbol == s].sort_values("t").reset_index(drop=True)
        print(f"  {min(i + 20, len(syms))}/{len(syms)}")
    rows = []
    for _, t in tr.iterrows():
        s = str(t.Symbol); x = m5.get(s); d = d1.get(s)
        if x is None or d is None or x.empty or d.empty:
            continue
        sg = -1 if t.put else 1
        k = np.searchsorted(x["end"].values, np.datetime64(t.entry_t.tz_convert("UTC").tz_localize(None)), side="right") - 1
        if k < 0 or x.iloc[k]["t"].date() != t.entry_t.date():
            continue
        p0 = x.iloc[k]["c"]
        r = dict(date=t.date, symbol=s, put=t.put, year=t.entry_t.year, opt_ret=t.ret,
                 hold_hrs=t["Hold (hrs)"], dte=t.dte)
        rth = x[(x.t.dt.strftime("%H:%M") >= "09:30") & (x.t.dt.strftime("%H:%M") < "16:00")]
        for mins, name in ((30, "30min"), (60, "60min")):
            tt = t.entry_t + pd.Timedelta(minutes=mins)
            j = np.searchsorted(x["end"].values, np.datetime64(tt.tz_convert("UTC").tz_localize(None)), side="right") - 1
            r[name] = sg * (x.iloc[j]["c"] / p0 - 1) * 100 if j > k else np.nan
        dd = d[d.t.dt.date >= t.entry_t.date()].reset_index(drop=True)
        for n, name in ((0, "close"), (1, "next_close"), (3, "3d_close"), (5, "5d_close")):
            r[name] = sg * (dd.iloc[n]["c"] / p0 - 1) * 100 if len(dd) > n else np.nan
        win = rth[(rth.t > x.iloc[k]["t"]) & (rth.t.dt.date <= (dd.iloc[min(5, len(dd) - 1)]["t"].date() if len(dd) else t.entry_t.date()))]
        if len(win):
            fav = (win["l"].min() / p0 - 1) if t.put else (win["h"].max() / p0 - 1)
            adv = (win["h"].max() / p0 - 1) if t.put else (win["l"].min() / p0 - 1)
            r["best_5d"], r["worst_5d"] = abs(fav) * 100, -abs(adv) * 100
        rows.append(r)
    D = pd.DataFrame(rows); D.to_csv(f"{OUT}/direction_trades.csv", index=False)

    def tline(name, x):
        out = [f"| {name} | {len(x)} |"]
        for h in H:
            v = x[h].dropna()
            t_ = v.mean() / (v.std(ddof=1) / math.sqrt(len(v))) if len(v) > 2 and v.std() > 0 else float("nan")
            out.append(f" {(v > 0).mean():.0%} / {v.mean():+.2f}% (t {t_:.1f}) |")
        return "".join(out)

    L = ["# Direction Test — was the stock moving your way?",
         f"\n{len(D)} trades. Each cell: % of trades where the stock moved in your direction / average move "
         "in your direction (t-stat). A coin flip is 50% / +0.00%.\n",
         "| Group | Trades | 30 min | 60 min | Same-day close | Next close | 3-day close | 5-day close |",
         "|---|---|---|---|---|---|---|---|", tline("all trades", D)]
    for y, g in D.groupby("year"):
        L.append(tline(str(y), g))
    L.append(tline("puts", D[D.put])); L.append(tline("calls", D[~D.put]))
    L.append(tline("trades you held < 1 hr", D[D.hold_hrs < 1]))
    L.append(tline("trades you held 1+ hr", D[D.hold_hrs >= 1]))
    if "best_5d" in D:
        L += ["\n## Early or wrong? Within 5 days of entry\n",
              f"- Median best move your way: {D.best_5d.median():.2f}%",
              f"- Median worst move against you: {D.worst_5d.median():.2f}%",
              f"- Trades where the best move your way beat the worst move against: {(D.best_5d > -D.worst_5d).mean():.0%}"]
    L.append("\nRead: if 'your way' is well above 50% with t >= 3 at some horizon, your direction calls "
             "are an edge and the fix is contract choice and timing. If it sits near 50% / 0, it isn't.")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
