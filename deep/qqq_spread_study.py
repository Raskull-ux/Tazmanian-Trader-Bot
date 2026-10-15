"""QQQ 1-wide next-day CALL spread, bought at 3:50 PM (long the at-the-money strike, short +1), real 1-minute
option trades since Feb 2024. What it cost, and what it was worth the next morning depending on how far QQQ popped.
Spread value each minute = long leg last trade - short leg last trade (both carried forward)."""
import os
import numpy as np, pandas as pd
from . import lib

OUT = "results/deep_analysis"


def main():
    J = pd.read_csv("deep/qqq_nextday_spreads.csv", parse_dates=["day", "next"])
    B = pd.read_parquet("results/qqq_spreads/bars.parquet")
    B["t"] = pd.to_datetime(B.t)
    bars = {o: g.set_index("t").c.sort_index() for o, g in B.groupby("occ")}
    m = lib.load_m5("QQQ")
    tod = m.index.hour * 60 + m.index.minute
    r = m[(tod >= 570) & (tod < 960)]
    rows = []
    for (d, n), g in J[J.cp == "C"].groupby(["day", "next"]):
        ks = sorted(g.k.unique())
        lo, hi = f"QQQ{n:%y%m%d}C{ks[0] * 1000:08d}", f"QQQ{n:%y%m%d}C{ks[1] * 1000:08d}"
        if lo not in bars or hi not in bars:
            continue
        s = pd.concat([bars[lo].rename("l"), bars[hi].rename("h")], axis=1).sort_index().ffill().dropna()
        sp = (s.l - s.h).clip(lower=0)
        buy_t = d + pd.Timedelta(hours=15, minutes=50)
        pre = sp[(sp.index <= buy_t) & (sp.index >= buy_t - pd.Timedelta(minutes=15))]
        if len(pre) == 0:
            continue
        cost = float(pre.iloc[-1])
        if cost <= 0.05 or cost >= 0.95:
            continue
        nx = sp[(sp.index >= n + pd.Timedelta(minutes=570)) & (sp.index <= n + pd.Timedelta(minutes=955))]
        q = r[r.index.normalize() == n]
        qd = r[r.index.normalize() == d]
        if len(nx) < 5 or len(q) == 0 or len(qd) == 0:
            continue
        c1 = float(qd.c.iloc[-1])
        first30 = nx[nx.index < n + pd.Timedelta(minutes=600)]
        t_hi = q.h.idxmax() + pd.Timedelta(minutes=5)
        at_hi = sp[sp.index <= t_hi]
        rows.append(dict(day=d.date(), cost=cost, qqq_close=c1,
                         pop_high_pct=(q.h.max() / c1 - 1) * 100,
                         pop_30m_pct=(q[q.index < n + pd.Timedelta(minutes=600)].h.max() / c1 - 1) * 100,
                         open_pct=(q.o.iloc[0] / c1 - 1) * 100,
                         v_open=float(nx.iloc[0]), v_best30=float(first30.max()) if len(first30) else np.nan,
                         v_at_stock_high=float(at_hi.iloc[-1]) if len(at_hi) else np.nan,
                         v_close=float(nx.iloc[-1])))
    D = pd.DataFrame(rows)
    for c in ("v_open", "v_best30", "v_at_stock_high", "v_close"):
        D[c.replace("v_", "ret_")] = (D[c] / D.cost - 1) * 100
    D.to_csv(f"{OUT}/qqq_nextday_callspread.csv", index=False)
    print(f"{len(D)} days | median cost ${D.cost.median():.2f} (25-75%: ${D.cost.quantile(.25):.2f}-${D.cost.quantile(.75):.2f})")
    bins = [-99, 0, 0.3, 0.6, 0.9, 1.2, 1.5, 99]
    D["pop_bin"] = pd.cut(D.pop_high_pct, bins)
    D["pop30_bin"] = pd.cut(D.pop_30m_pct, bins)
    print("\nBy next-day HIGH vs the 3:50 close (what the spread was worth when QQQ hit its high):")
    print(D.groupby("pop_bin", observed=True).agg(days=("cost", "size"), median_ret_at_high=("ret_at_stock_high", "median"),
                                                  median_ret_close=("ret_close", "median")).round(0).to_string())
    print("\nBy the FIRST 30 MINUTES high (best spread value in the first 30 minutes):")
    print(D.groupby("pop30_bin", observed=True).agg(days=("cost", "size"), median_best30=("ret_best30", "median"),
                                                    median_open=("ret_open", "median")).round(0).to_string())


if __name__ == "__main__":
    main()
