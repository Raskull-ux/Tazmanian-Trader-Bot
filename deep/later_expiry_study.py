"""Sep-Oct 2026 trades: original contract vs the same strike with a later expiration (+1 week, +2 weeks).
Real 1-minute option prices. Same entry time, same exit time. Percent moves only."""
import os
import numpy as np, pandas as pd

SRC = "results/recent_options"
OUT = "results/deep_analysis"


def load(occ):
    f = f"{SRC}/{occ}.csv"
    return pd.read_csv(f, parse_dates=["t"]) if os.path.exists(f) else None


def px(b, t, before=False):
    if b is None or t is None or pd.isna(t):
        return np.nan
    x = b[(b.t <= t) & (b.t >= t - pd.Timedelta(minutes=30))] if before else b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=30))]
    if len(x) == 0 and before:
        x = b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=30))]
    return float(x.c.iloc[-1] if before else x.c.iloc[0]) if len(x) else np.nan


def main():
    T = pd.read_csv("deep/recent_trades.csv", parse_dates=["entry", "exit"])
    M = pd.read_csv(f"{SRC}/later_map.csv", parse_dates=["entry"])
    rep = pd.read_csv(f"{OUT}/recent_trades_replay.csv", parse_dates=["entry", "hold_next_level_at"])
    days = pd.bdate_range("2026-09-01", "2026-10-30")
    rows = []
    for r in T.itertuples():
        variants = [("original", r.occ)] + [(g.tag, g.occ) for g in M[(M.orig == r.occ) & (M.entry == r.entry)].itertuples()]
        i0 = days.searchsorted(r.entry.normalize())
        five = days[min(i0 + 4, len(days) - 1)] + pd.Timedelta(hours=15, minutes=59)
        hn = rep[(rep.occ == r.occ) & (rep.entry == r.entry)]
        t_hold = hn.hold_next_level_at.iloc[0] if len(hn) and "hold_next_level_at" in hn else None
        for tag, occ in variants:
            b = load(occ)
            rec = dict(trade=f"{r.occ} @ {r.entry:%m-%d %H:%M}", variant=tag, occ=occ)
            if b is None:
                rec["status"] = "no bars (contract may not exist)"; rows.append(rec); continue
            exp = pd.Timestamp("20" + occ[-15:-9]) + pd.Timedelta(hours=16)
            p0 = px(b, r.entry)
            if np.isnan(p0):
                rec["status"] = "no print near entry"; rows.append(rec); continue
            rec["entry_px"] = p0
            if pd.notna(r.exit):
                rec["at_your_exit_pct"] = (px(b, r.exit, before=True) / p0 - 1) * 100
            win = b[(b.t > r.entry) & (b.t <= min(five, exp))]
            if len(win):
                rec["best_5d_pct"] = (win.c.max() / p0 - 1) * 100
                rec["worst_5d_pct"] = (win.c.min() / p0 - 1) * 100
                end5 = b[b.t <= min(five, exp)]
                rec["held_5d_or_expiry_pct"] = (end5.c.iloc[-1] / p0 - 1) * 100
                rec["held_to"] = end5.t.iloc[-1]
            if t_hold is not None and pd.notna(t_hold):
                rec["next_level_rule_pct"] = (px(b, t_hold, before=True) / p0 - 1) * 100
            rows.append(rec)
    D = pd.DataFrame(rows)
    D.to_csv(f"{OUT}/later_expiry_replay.csv", index=False)
    pd.set_option("display.width", 260)
    print(D.drop(columns=["occ"]).round(1).to_string())
    print()
    for tag, g in D.groupby("variant"):
        g = g.dropna(subset=["entry_px"])
        print(f"{tag:9s} n {len(g):2d} | up 50%+ at some point within 5 days: {(g.best_5d_pct >= 50).sum()} | "
              f"green at your exit: {(g.at_your_exit_pct > 0).sum()}/{g.at_your_exit_pct.notna().sum()} "
              f"(avg {g.at_your_exit_pct.mean():.0f}%) | green if held 5 days: {(g.held_5d_or_expiry_pct > 0).sum()} "
              f"(avg {g.held_5d_or_expiry_pct.mean():.0f}%, med {g.held_5d_or_expiry_pct.median():.0f}%) | "
              f"next-level rule avg {g.next_level_rule_pct.mean():.0f}% med {g.next_level_rule_pct.median():.0f}%")


if __name__ == "__main__":
    main()
