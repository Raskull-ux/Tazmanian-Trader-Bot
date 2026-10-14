"""Every Sep-Oct 2026 alert we can price exactly, valued the way a member following the alert would get it:
bought at the first real print after the alert, sold at the last print before Taz posted he was out.
One contract each. Also: what a $200 / $500 account taking one contract per alert would look like (in order).
Posted-only results (spreads, unknown strikes) are listed separately, not mixed in.
HOOD is left out: his $1.12 -> $5.01 contract is not the $100 10/23 single put (that traded 1.04 -> 2.30), so it could not be priced exactly."""
import numpy as np, pandas as pd

SRC = "results/recent_options"
OUT = "results/deep_analysis"
# (contract, alert time, out time, label). out=None -> no exit posted: valued at expiration.
ALERTS = [
    ("QQQ260903P00710000", "2026-09-03 09:41", "2026-09-03 10:04", "QQQ $710 put 10AM reversal"),
    ("SPY260903P00767000", "2026-09-03 10:27", "2026-09-03 10:35", "SPY $767 put"),
    ("PLTR260918P00170000", "2026-09-08 09:32", "2026-09-08 09:50", "PLTR $170 put 9/18"),
    ("QQQ260911P00710000", "2026-09-09 09:33", "2026-09-09 12:20", "QQQ $710 put for Friday"),
    ("NVDA260916C00215000", "2026-09-16 10:02", "2026-09-16 11:06", "NVDA same-day call (strike $215 assumed)"),
    ("NVDA260918C00220000", "2026-09-16 10:02", "2026-09-16 11:06", "NVDA $220 call for Friday"),
    ("NVDA260916C00217500", "2026-09-16 14:02", "2026-09-16 14:08", "NVDA FOMC $217.5 call"),
    ("AAPL260918P00320000", "2026-09-16 15:10", None, "AAPL $320 put lotto (no exit posted)"),
    ("INTC260925P00108000", "2026-09-18 09:37", None, "INTC $108 put (no exit posted)"),
    ("NVDA260925P00225000", "2026-09-22 09:45", "2026-09-22 10:04", "NVDA $225 put"),
    ("QQQ260928P00740000", "2026-09-25 12:51", "2026-09-25 14:07", "QQQ $740 put for Monday"),
    ("QQQ260925P00743000", "2026-09-25 13:06", "2026-09-25 14:07", "QQQ $743 same-day put"),
    ("QQQ261002C00743000", "2026-09-30 09:28", "2026-09-30 10:06", "QQQ calls for Friday ($743 strike)"),
    ("QQQ261001P00739000", "2026-10-01 12:37", "2026-10-01 12:54", "QQQ $739 same-day put"),
    ("TSLA261007P00365000", "2026-10-05 10:26", "2026-10-05 11:07", "TSLA $365 put"),
    ("MSTR261009P00155000", "2026-10-05 12:39", "2026-10-05 14:50", "MSTR $155 put"),
    ("INTC261012P00110000", "2026-10-05 14:56", "2026-10-06 12:15", "INTC $110 put 10/12"),
    ("QQQ261009P00750000", "2026-10-06 15:40", "2026-10-07 09:59", "QQQ $750 put swing"),
    ("QQQ261009P00750000", "2026-10-08 09:35", "2026-10-08 11:15", "QQQ $750 put next-day"),
    ("QQQ261009P00748000", "2026-10-08 11:15", "2026-10-08 11:58", "QQQ $748 put next-day"),
    ("TSLA261009P00367500", "2026-10-08 11:58", "2026-10-08 13:36", "TSLA $367.5 put"),
    ("TSLA261012P00365000", "2026-10-08 15:59", "2026-10-09 10:18", "TSLA $365 put overnight"),
    ("QQQ261012P00745000", "2026-10-09 10:18", "2026-10-09 12:44", "QQQ $745 put"),
    ("QQQ261012C00748000", "2026-10-12 11:43", "2026-10-12 12:04", "QQQ $748 same-day call"),
    ("QQQ261012P00746000", "2026-10-12 12:24", "2026-10-12 12:57", "QQQ $746 same-day put"),
]


def px(b, t, before=False):
    t = pd.Timestamp(t)
    x = b[(b.t <= t) & (b.t >= t - pd.Timedelta(minutes=30))] if before else b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=30))]
    return float(x.c.iloc[-1] if before else x.c.iloc[0]) if len(x) else np.nan


def main():
    rows = []
    for occ, a, z, label in ALERTS:
        b = pd.read_csv(f"{SRC}/{occ}.csv", parse_dates=["t"])
        p_in = px(b, a)
        if z is None:
            exp = pd.Timestamp("20" + occ[-15:-9]) + pd.Timedelta(hours=16)
            p_out = float(b[b.t <= exp].c.iloc[-1])
        else:
            p_out = px(b, z, before=True)
        rows.append(dict(month=a[:7], alert=a, out=z or "expiration", trade=label, contract=occ,
                         cost_1=round(p_in * 100, 2), sold_1=round(p_out * 100, 2),
                         pct=round((p_out / p_in - 1) * 100, 1), dollars_1=round((p_out - p_in) * 100, 2)))
    D = pd.DataFrame(rows)
    for start in (200, 500):
        bal, col = start, []
        for r in D.itertuples():
            if r.cost_1 <= bal:
                bal += r.dollars_1
                col.append(round(bal, 2))
            else:
                col.append(np.nan)
        D[f"acct_{start}"] = col
    D.to_csv(f"{OUT}/alert_scoreboard.csv", index=False)
    pd.set_option("display.width", 250)
    print(D.to_string(index=False))
    for m, g in D.groupby("month"):
        print(m, "alerts", len(g), "green", (g.pct > 0).sum(), "one-contract total $", round(g.dollars_1.sum(), 2),
              "| $100 per alert total $", round(g.pct.sum(), 0))


if __name__ == "__main__":
    main()
