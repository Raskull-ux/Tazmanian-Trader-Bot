"""Pulls real 1-minute option trade bars (Alpaca, free) for Taz's Sep-Oct 2026 contracts listed in
deep/recent_trades.csv, from entry day through expiration (or today). Saves results/recent_options/<occ>.csv."""
import os
import pandas as pd
import option_reality as R

OUT = "results/recent_options"


def main():
    R.HD = R.keys()
    os.makedirs(OUT, exist_ok=True)
    T = pd.read_csv(os.environ.get("TRADES_FILE", "deep/recent_trades.csv"), parse_dates=["entry"])
    now = pd.Timestamp.now(tz="America/New_York").tz_localize(None) - pd.Timedelta(minutes=20)
    status = []
    for occ, g in T.groupby("occ"):
        exp = pd.Timestamp("20" + occ[-15:-9])
        start = g.entry.min().normalize() + pd.Timedelta(hours=4)
        end = min(exp + pd.Timedelta(hours=16, minutes=15), now)
        bars = R.option_bars([occ], start, end).get(occ)
        n = 0 if bars is None else len(bars)
        if n:
            bars.to_csv(f"{OUT}/{occ}.csv", index=False)
        status.append(dict(occ=occ, bars=n, start=start, end=end))
        print(occ, n, flush=True)
    pd.DataFrame(status).to_csv(f"{OUT}/status.csv", index=False)


if __name__ == "__main__":
    main()
