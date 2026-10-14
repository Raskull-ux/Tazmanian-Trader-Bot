"""Same trades as deep/recent_trades.csv, same strike, but a LATER expiration:
  +1wk: the first Friday at least 7 days after entry (Taz's rule: a week or more out)
  +2wk: the first Friday at least 14 days after entry
Pulls real 1-minute option bars (Alpaca, free) into results/recent_options/."""
import os
import pandas as pd
import option_reality as R

OUT = "results/recent_options"


def friday_on_or_after(d):
    return d + pd.Timedelta(days=(4 - d.weekday()) % 7)


def main():
    R.HD = R.keys()
    os.makedirs(OUT, exist_ok=True)
    T = pd.read_csv("deep/recent_trades.csv", parse_dates=["entry"])
    now = pd.Timestamp.now(tz="America/New_York").tz_localize(None) - pd.Timedelta(minutes=20)
    rows = []
    for r in T.itertuples():
        root, cp, strike = r.occ[:-15], r.occ[-9], r.occ[-8:]
        for tag, days in (("1wk", 7), ("2wk", 14)):
            exp = friday_on_or_after(r.entry.normalize() + pd.Timedelta(days=days))
            occ = f"{root}{exp:%y%m%d}{cp}{strike}"
            rows.append(dict(orig=r.occ, entry=r.entry, tag=tag, occ=occ))
    M = pd.DataFrame(rows)
    M.to_csv(f"{OUT}/later_map.csv", index=False)
    for occ, g in M.groupby("occ"):
        exp = pd.Timestamp("20" + occ[-15:-9])
        start = g.entry.min().normalize() + pd.Timedelta(hours=4)
        end = min(exp + pd.Timedelta(hours=16, minutes=15), now)
        if os.path.exists(f"{OUT}/{occ}.csv"):
            print(occ, "already have"); continue
        b = R.option_bars([occ], start, end).get(occ)
        if b is not None and len(b):
            b.to_csv(f"{OUT}/{occ}.csv", index=False)
        print(occ, 0 if b is None else len(b), flush=True)


if __name__ == "__main__":
    main()
