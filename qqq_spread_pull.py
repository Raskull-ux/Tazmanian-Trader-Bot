"""Real 1-minute option bars for QQQ next-day 1-wide spreads (deep/qqq_nextday_spreads.csv): from 15:00 on the
buy day to the close of the next day. Plus the current chain (10/16, 10/19, 10/23 expiries) on 10/14.
Saves results/qqq_spreads/bars.parquet and results/qqq_spreads/chain_1014.parquet"""
import os
import pandas as pd
import option_reality as R

OUT = "results/qqq_spreads"


def main():
    R.HD = R.keys()
    os.makedirs(OUT, exist_ok=True)
    J = pd.read_csv("deep/qqq_nextday_spreads.csv", parse_dates=["day", "next"])
    parts = []
    for (d, n), g in J.groupby(["day", "next"]):
        b = R.option_bars(sorted(set(g.occ)), d + pd.Timedelta(hours=15), n + pd.Timedelta(hours=16, minutes=15))
        for o, df in b.items():
            df["occ"] = o
            parts.append(df)
    if parts:
        pd.concat(parts).to_parquet(f"{OUT}/bars.parquet", index=False)
    print("spread bars", sum(len(p) for p in parts), flush=True)
    occs = []
    for exp in ("261016", "261019", "261023"):
        for k in range(705, 746):
            for cp in "CP":
                occs.append(f"QQQ{exp}{cp}{k * 1000:08d}")
    b = R.option_bars(occs, pd.Timestamp("2026-10-14 09:30"), pd.Timestamp("2026-10-14 16:15"))
    ch = []
    for o, df in b.items():
        df["occ"] = o
        ch.append(df)
    if ch:
        pd.concat(ch).to_parquet(f"{OUT}/chain_1014.parquet", index=False)
    print("chain contracts with trades", len(ch), flush=True)


if __name__ == "__main__":
    main()
