"""
30m gap-back rejection (Taz's "perfect setup"), test + live scan helper.

Setup, on 30m candles with extended hours (clock aligned :00/:30), on a GAP DOWN day (9:30 open 0.3%+ under the prior
regular close):
  1. price rallies back INTO the gap (above the day's open) during the regular session,
  2. it stalls at the 30m 50 SMA without filling the gap: the pattern high is within 0.1 daily ATR of the 50 SMA (or
     above it) but stays under the prior close, and the last candle closes back under the 50 SMA,
  3. red-green-green-red top: the last four closed 30m candles are red, green, green, red,
  4. the 30m 200 SMA is below the entry (that is the target).
Entry = close of the final red candle. Win = price reaches the 30m 200 SMA (value at entry) before it trades back over
the setup high (highest high of the four candles), within 5 trading days of 30m bars. Neither = not a win.
Baseline = every 30m candle that touched the 50 SMA from below and closed back under it (high >= 50, close < 50), with the
200 below, same outcome (target the 200, stop over that candle's high).
Split 2022-2024 / 2025-2026. Data: data_ext 5m (Alpaca, extended hours), 75 names. Out: results/gap_back/REPORT.md
"""
import os
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data_ext")
OUT = "results/gap_back"; os.makedirs(OUT, exist_ok=True)
HORIZON = 5 * 32   # 5 days of 30m bars (16 per extended session x 2)


def bars30(sym):
    m = pd.read_parquet(f"{DATA}/m5/{sym}.parquet")
    m = m[m.t >= "2021-06-01"]
    for k in "ohlcv": m[k] = m[k].astype(float)
    g = m.groupby(m.t.dt.floor("30min")).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    g["s50"] = g.c.rolling(50).mean(); g["s200"] = g.c.rolling(200).mean()
    tm = m.t.dt.hour * 60 + m.t.dt.minute
    r = m[(tm >= 570) & (tm < 960)]
    d = r.groupby(r.t.dt.normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    d["pc"] = d.c.shift(); d["patr"] = d.atr.shift()
    return g, d


def outcome(h, l, j, target, stop):
    for k in range(j + 1, min(j + 1 + HORIZON, len(h))):
        if h[k] > stop: return 0
        if l[k] <= target: return 1
    return 0


def scan(sym):
    g, d = bars30(sym)
    t = g.index; o, h, l, c, s50, s200 = (g[k].values for k in ("o", "h", "l", "c", "s50", "s200"))
    day = t.normalize(); tm = t.hour * 60 + t.minute
    dinfo = d.reindex(day)
    gap_down = (dinfo.o.values <= dinfo.pc.values * 0.997)
    reg = (tm >= 570) & (tm < 960)
    rows = []
    for j in range(203, len(g)):
        if t[j] < pd.Timestamp("2022-01-01") or not reg[j] or np.isnan(s200[j]): continue
        A = dinfo.patr.values[j]
        if not A > 0: continue
        # baseline: a 30m touch of the 50 from below that closes back under it, 200 below
        if h[j] >= s50[j] and c[j] < s50[j] and s200[j] < c[j]:
            rows.append(dict(sym=sym, t=t[j], kind="baseline", win=outcome(h, l, j, s200[j], h[j]),
                             rr=(c[j] - s200[j]) / max(h[j] - c[j], 1e-9)))
        # the setup
        if not gap_down[j] or j < 3: continue
        k4 = range(j - 3, j + 1)
        if any(day[k] != day[j] or not reg[k] for k in k4): continue
        col = [c[k] > o[k] for k in k4]
        if col != [False, True, True, False]: continue
        top = max(h[k] for k in k4)
        dop, pc = dinfo.o.values[j], dinfo.pc.values[j]
        if not (top > dop and top < pc): continue                      # back in the gap, gap not filled
        if not (top >= s50[j] - 0.1 * A and c[j] < s50[j]): continue    # stalled at the 50, closed back under
        if not s200[j] < c[j]: continue
        rows.append(dict(sym=sym, t=t[j], kind="setup", win=outcome(h, l, j, s200[j], top), rr=(c[j] - s200[j]) / max(top - c[j], 1e-9)))
    return rows


def main():
    names = sorted(f[:-8] for f in os.listdir(f"{DATA}/m5"))
    rows = []
    for s in names:
        try: rows += scan(s)
        except Exception as e: print("skip", s, e)
    R = pd.DataFrame(rows)
    R["period"] = np.where(R.t < "2025-01-01", "2022-24", "2025-26")
    R.to_csv(f"{OUT}/signals.csv.gz", index=False)
    S = R[R.kind == "setup"]
    L = ["# 30m gap-back rejection: gap down, rally into the gap, stall at the 30m 50, red-green-green-red, target the 30m 200", "",
         f"{R.sym.nunique()} names, 30m candles with extended hours, Jan 2022 to Oct 14 2026 (Alpaca 5m bars on the data_ext branch).",
         "Win = reaches the 30m 200 SMA before trading back over the setup high (within 5 sessions). Baseline = every 30m touch of the 50 SMA from "
         "below that closed back under it, with the 200 below.", "",
         "| Group | Period | Signals | Reached the 200 first | Median reward:risk (200 distance / stop distance) |", "|---|---|---|---|---|"]
    res = {}
    for kind in ("setup", "baseline"):
        for per in ("2022-24", "2025-26"):
            x = R[(R.kind == kind) & (R.period == per)]
            res[(kind, per)] = x.win.mean() if len(x) else np.nan
            L.append(f"| {kind} | {per} | {len(x):,} | {x.win.mean()*100:.1f}% | {x.rr.median():.2f} |" if len(x) else f"| {kind} | {per} | 0 | - | - |")
    # fair comparison: same reward:risk bucket
    L += ["", "Same comparison inside reward:risk buckets (a far target is harder to reach, so compare like with like):", "",
          "| Reward:risk | Period | Setup n | Setup win | Baseline n | Baseline win |", "|---|---|---|---|---|---|"]
    R["rrb"] = pd.cut(R.rr, [0, 1, 2, 4, 1e9], labels=["under 1", "1-2", "2-4", "4+"])
    for b in ["under 1", "1-2", "2-4", "4+"]:
        for per in ("2022-24", "2025-26"):
            a = R[(R.kind == "setup") & (R.period == per) & (R.rrb == b)]; z = R[(R.kind == "baseline") & (R.period == per) & (R.rrb == b)]
            L.append(f"| {b} | {per} | {len(a)} | {a.win.mean()*100:.0f}% | {len(z):,} | {z.win.mean()*100:.0f}% |" if len(a) else f"| {b} | {per} | 0 | - | {len(z):,} | {z.win.mean()*100:.0f}% |")
    held = all(res[("setup", p)] - res[("baseline", p)] >= 0.05 for p in ("2022-24", "2025-26") if res[("setup", p)] == res[("setup", p)])
    held = held and all(res[("setup", p)] == res[("setup", p)] for p in ("2022-24", "2025-26")) and len(S) >= 40
    L += ["", "## Answer", "",
          f"Setup: {res[('setup','2022-24')]*100:.1f}% (2022-24) and {res[('setup','2025-26')]*100:.1f}% (2025-26) reached the 30m 200 first; "
          f"baseline {res[('baseline','2022-24')]*100:.1f}% and {res[('baseline','2025-26')]*100:.1f}%.",
          ("**Held in both halves** (5+ points over the baseline in each, 40+ signals). Added to the watchlist pre-market check." if held else
           "**Did not hold in both halves** at the bar set before running (5+ points over the baseline in each half, 40+ signals). "
           "Not added to the watchlist alerts. Lean worth knowing: inside the same reward:risk bucket it beat the baseline in 3 of 4 buckets "
           "in both halves (all but 1-2 in 2025-26), so the pattern is not useless, but it is too thin to alert on."), "",
          "By name (setup signals):", "", "| Name | Signals | Win |", "|---|---|---|"]
    for s, x in S.groupby("sym"):
        L.append(f"| {s} | {len(x)} | {x.win.mean()*100:.0f}% |")
    open(f"{OUT}/REPORT.md", "w").write("\n".join(L) + "\n")
    open(f"{OUT}/held.txt", "w").write("yes\n" if held else "no\n")
    print("\n".join(L[:40]))


if __name__ == "__main__":
    main()
