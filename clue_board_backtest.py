"""
Backtest the clue board: does ranking names by broken clues pick better puts?

Every trading day, rank the names the way the board does (most broken clues first, fewer strength warnings breaks ties)
and take the top 10 that have at least one broken clue. Outcome for a put from that day's close: 2 ATR down before
2 ATR up within 10 trading days (same race and clue definitions as broken_vs_strength.py). Compare with every name-day.
Split 2016-2021 / 2022-2026.

MODE=local75: his 75 names from the data_ext branch (DATA_DIR), all clues incl. 4h cliff diver and 3h RSI 90.
MODE=all860 : all 860 names, daily bars from yfinance (Actions). Daily clues only (monthly red, 3 weekly lower highs,
              10-day 10 EMA under 10 SMA, MACD plateau, near the 20-day high); the 4h/3h clues need hourly bars for
              860 names back to 2016, which is the slow Alpaca pull already running for Task 1.
Out: results/clue_board/backtest_<mode>.md and BACKTEST.md (both parts that exist).
"""
import os
import numpy as np, pandas as pd
import broken_vs_strength as B

MODE = os.environ.get("MODE", "local75")
DATA = os.environ.get("DATA_DIR", "data_ext")
OUT = "results/clue_board"; os.makedirs(OUT, exist_ok=True)


def load_local():
    U = pd.read_csv("universe/expanded_universe.csv")
    rows = []
    for s in sorted(U[U.group == "your 75"].symbol):
        f = f"{DATA}/m5/{s}.parquet"
        if not os.path.exists(f): continue
        m = pd.read_parquet(f)
        for k in "ohlc": m[k] = m[k].astype(float)
        tm = m.t.dt.hour * 60 + m.t.dt.minute
        r = m[(tm >= 570) & (tm < 960)]
        d = r.groupby(r.t.dt.normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
        h1 = m.groupby(m.t.dt.floor("h")).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last")).reset_index()
        h1.columns = ["t", "o", "h", "l", "c"]
        rows.append(B.features(s, d, h1))
    return pd.concat(rows)


def load_860():
    syms = list(B.U.symbol)
    D = B.daily_all(syms)
    rows = []
    for s in syms:
        if s in D:
            try: rows.append(B.features(s, D[s], None))
            except Exception as e: print("skip", s, e)
    return pd.concat(rows)


def report(X, label, clues):
    X = X.copy()
    X["date"] = X.index
    X["nb"] = X[[c for c in B.BROKEN if c in clues]].astype(int).sum(axis=1)
    X["ns"] = X[[c for c in B.STRONG if c in clues]].astype(int).sum(axis=1)
    X["period"] = np.where(X.date < "2022-01-01", "2016-21", "2022-26")
    X = X.sort_values(["date", "nb", "ns", "sym"], ascending=[True, False, True, True])
    X["rk"] = X.groupby("date").cumcount() + 1
    top = X[(X.rk <= 10) & (X.nb >= 1)]
    groups = [("Every name-day (baseline)", X), ("Board top 10 (1+ broken clue)", top),
              ("Board top 10, no strength warning", top[top.ns == 0]), ("Board top 3", X[(X.rk <= 3) & (X.nb >= 1)]),
              ("2+ broken clues, no strength warning", X[(X.nb >= 2) & (X.ns == 0)]),
              ("Strength warning, no broken clue (the 'don't short' names)", X[(X.ns >= 1) & (X.nb == 0)])]
    L = [f"## {label}", "", f"{X.sym.nunique()} names, {len(X):,} name-days. Clues used: {', '.join(clues)}.", "",
         "| Group | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |", "|---|---|---|---|---|---|---|"]
    base = {p: X[X.period == p].win.mean() for p in ("2016-21", "2022-26")}
    res = {}
    for lab, g in groups:
        cells = []
        for p in ("2016-21", "2022-26"):
            x = g[g.period == p]; w = x.win.mean() if len(x) else np.nan
            res[(lab, p)] = w
            cells += [f"{len(x):,}", f"{w*100:.1f}%" if len(x) else "-", f"{(w-base[p])*100:+.1f} pts" if len(x) else "-"]
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    lift = [res[("Board top 10 (1+ broken clue)", p)] - base[p] for p in ("2016-21", "2022-26")]
    held = all(v >= 0.01 for v in lift)
    L += ["", f"**Verdict:** board top 10 vs every name-day: {lift[0]*100:+.1f} pts (2016-21), {lift[1]*100:+.1f} pts (2022-26). " +
          ("Ranking by broken clues picked better puts in both halves." if held else "Ranking by broken clues did NOT pick clearly better puts in both halves (bar: +1 point in each)."), ""]
    return L, lift, held


def main():
    if MODE == "local75":
        X = load_local(); L, lift, held = report(X, "His 75 names (all clues incl. 4h cliff and 3h RSI 90)", B.BROKEN + B.STRONG)
    else:
        X = load_860(); L, lift, held = report(X, "All 860 names (daily clues only)", ["monthly_red", "weekly_3lh", "tenday_cross", "macd_plateau", "near_20d_high"])
    open(f"{OUT}/backtest_{MODE}.md", "w").write("\n".join(L) + "\n")
    open(f"{OUT}/backtest_{MODE}.txt", "w").write(f"{lift[0]:.4f},{lift[1]:.4f},{int(held)}\n")
    parts = ["# Clue board backtest", "",
             "Every day, rank names like the board (most broken clues, then fewest strength warnings) and take the top 10 with 1+ broken clue. "
             "Outcome: 2 ATR down before 2 ATR up within 10 trading days from that day's close (a same-day tie counts as a loss). "
             "Win rates near 30% are normal for this 10-day race.", ""]
    for m in ("local75", "all860"):
        f = f"{OUT}/backtest_{m}.md"
        parts += open(f).read().splitlines() if os.path.exists(f) else [f"## {m}: not run yet", ""]
    open(f"{OUT}/BACKTEST.md", "w").write("\n".join(parts) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
