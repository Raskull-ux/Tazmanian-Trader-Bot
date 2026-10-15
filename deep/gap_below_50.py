"""Setup: daily 10 SMA at least 2.5% above the 50 SMA (yesterday's close), and today OPENS below the 50 SMA.
Long daily history from Yahoo (results/long_daily). Outcomes measured from the gap-day open.
Episodes = first signal after 14 quiet days."""
import pandas as pd

for f in ("QQQ", "SPY", "IDX_NDX", "IDX_GSPC"):
    d = pd.read_csv(f"results/long_daily/{f}.csv", parse_dates=["t"]).set_index("t")
    d = d[d.o > 0]
    d["s10"], d["s50"] = d.c.rolling(10).mean(), d.c.rolling(50).mean()
    d["g"] = (d.s10 / d.s50 - 1) * 100
    p = d.shift()
    sig = d[(p.g >= 2.5) & (d.o < p.s50)]
    first = [t for t in sig.index if not ((sig.index < t) & (sig.index >= t - pd.Timedelta(days=14))).any()]
    rows = []
    for t in first:
        i = d.index.get_loc(t)
        o = d.o.iloc[i]
        rows.append(dict(sym=f, date=t.date(), gap_10_50=round(p.g.loc[t], 1),
                         day=(d.c.iloc[i] / o - 1) * 100, d5=(d.c.iloc[min(i + 5, len(d) - 1)] / o - 1) * 100,
                         d10=(d.c.iloc[min(i + 10, len(d) - 1)] / o - 1) * 100,
                         low10=(d.l.iloc[i:i + 11].min() / o - 1) * 100))
    pd.DataFrame(rows).round(2).to_csv(f"results/deep_analysis/gap_below_50_{f}.csv", index=False)
