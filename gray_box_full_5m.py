"""
Gray Box v2 on full 5m history from 2024, per stock, for the 43 names in results/chart_data.
Rules = the live bot v2 (open box, arm 0.4 range, trigger a tenth before the edge, stop half a range, half off at half a
range, stop to entry, runner three quarters or the close). Same engine as gray_box_filled_edges.py ("open" level).
Data: data_ext Alpaca 5m bars (regular session for grading), Jan 2024 to Oct 14 2026. Split 2024 / 2025-26.
Out: results/gray_box/full_5m.md
"""
import os
import numpy as np, pandas as pd
import gray_box_filled_edges as G

OUT = "results/gray_box"


def main():
    names = sorted({f.split(".")[0] for f in os.listdir("results/chart_data/daily")})
    rows = []
    for s in names:
        try:
            rows += [r for r in G.run(s) if r["kind"] == "open" and r["date"] >= pd.Timestamp("2024-01-01")]
        except Exception as e:
            print("skip", s, e)
    R = pd.DataFrame(rows); R["period"] = np.where(R.date < "2025-01-01", "2024", "2025-26")
    T = R[R.rr.notna()]
    L = ["# Gray Box v2 on 5m bars from 2024, per stock", "",
         f"{R.sym.nunique()} names (results/chart_data), Jan 2024 to Oct 14 2026, Alpaca 5m bars from the data_ext branch. "
         "Live bot rules, half off at half a range. Result per triggered trade in daily ranges (stock move, no option P&L). "
         "A stopped trade is -0.50, half + runner is +0.625.", "",
         "## All names", "", "| Side | Period | Setups | Triggered | Half off | Stopped | Avg result |", "|---|---|---|---|---|---|---|"]
    for side in ("PUT", "CALL", "both"):
        for per in ("2024", "2025-26"):
            x = R[(R.period == per) & ((R.side == side) if side != "both" else True)]; t = x[x.rr.notna()]
            L.append(f"| {side} | {per} | {len(x):,} | {len(t):,} | {t.res.str.startswith('half').mean()*100:.0f}% | {(t.res=='stopped').mean()*100:.0f}% | {t.rr.mean():+.3f} |")
    L += ["", "## Per stock (triggered trades)", "",
          "| Stock | 2024 n | 2024 avg | 2025-26 n | 2025-26 avg | Both n | Both avg | Half off | Stopped | Positive in both? |", "|---|---|---|---|---|---|---|---|---|---|"]
    g = []
    for s, x in T.groupby("sym"):
        a, b = x[x.period == "2024"], x[x.period == "2025-26"]
        both = len(a) >= 10 and len(b) >= 10 and a.rr.mean() > 0 and b.rr.mean() > 0
        g.append((x.rr.mean(), s, f"| {s} | {len(a)} | {a.rr.mean():+.3f} | {len(b)} | {b.rr.mean():+.3f} | {len(x)} | {x.rr.mean():+.3f} | "
                 f"{x.res.str.startswith('half').mean()*100:.0f}% | {(x.res=='stopped').mean()*100:.0f}% | {'yes' if both else 'no'} |", both))
    g.sort(reverse=True)
    L += [z[2] for z in g]
    pos = [z[1] for z in g if z[3]]
    L += ["", "## Answer", "",
          f"Across all 43 names the average triggered trade was {T[T.period=='2024'].rr.mean():+.3f} range in 2024 and "
          f"{T[T.period=='2025-26'].rr.mean():+.3f} in 2025-26. Names positive in both periods with 10+ trades each: "
          f"{', '.join(pos) if pos else 'none'}. With ~20 to 60 trades per name, single-name averages within about 0.1 range of zero are noise."]
    open(f"{OUT}/full_5m.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[:16] + L[-3:]))


if __name__ == "__main__":
    main()
