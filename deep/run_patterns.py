"""
Runs every daily + intraday pattern on every name. `--noise` runs the identical pipeline on scrambled data
(daily: days shuffled; intraday: 5-min moves shuffled inside each day) to prove the test doesn't invent edges.

PASS RULE (fixed before looking at results):
  discovery 2016-2022: n >= 30, win-rate excess > 0 with t >= 2.0, and the return excess > 0
  holdout 2023-now:    n >= 30, win-rate excess > 0 with t >= 1.5, and the return excess > 0
"""
import os, sys, glob
import numpy as np, pandas as pd
from . import lib, patterns as P, intraday as I

OUT = "results/deep_analysis"
NOISE = "--noise" in sys.argv
rng = np.random.default_rng(11)


def scramble_daily(D):
    """Shuffle days: keep each day's shape (o/h/l relative to close, volume) but put days in random order."""
    r = np.log(D.c).diff().fillna(0).values
    perm = rng.permutation(len(D))
    c = D.c.iloc[0] * np.exp(np.cumsum(r[perm]))
    rel = D[["o", "h", "l"]].div(D.c, axis=0).values[perm]
    X = pd.DataFrame({"o": rel[:, 0] * c, "h": rel[:, 1] * c, "l": rel[:, 2] * c, "c": c, "v": D.v.values[perm]},
                     index=D.index)
    return X


def scramble_m5(m5):
    """Shuffle 5-min moves inside each day; keep the overnight gap and each day's open."""
    m = m5.copy()
    day = m.index.normalize()
    lc = np.log(m.c.values)
    lo = np.log(m.o.values)
    out_c = np.empty_like(lc)
    rel_h = np.log(m.h.values) - lc
    rel_l = np.log(m.l.values) - lc
    starts = np.r_[0, np.where(day[1:] != day[:-1])[0] + 1, len(m)]
    new_h = np.empty_like(lc); new_l = np.empty_like(lc); new_o = np.empty_like(lc)
    prev_close = lc[0]
    for a, b in zip(starts[:-1], starts[1:]):
        gap = lo[a] - (lc[a - 1] if a > 0 else lo[a])
        moves = np.diff(np.r_[lo[a], lc[a:b]])
        p = rng.permutation(b - a)
        mv = moves[p]
        o0 = prev_close + gap
        cc = o0 + np.cumsum(mv)
        out_c[a:b] = cc
        oo = np.r_[o0, cc[:-1]]
        new_o[a:b] = oo
        new_h[a:b] = np.maximum(np.maximum(oo, cc), cc + rel_h[a:b][p])
        new_l[a:b] = np.minimum(np.minimum(oo, cc), cc + rel_l[a:b][p])
        prev_close = cc[-1]
    m["o"], m["h"], m["l"], m["c"] = np.exp(new_o), np.exp(new_h), np.exp(new_l), np.exp(out_c)
    return m


def daily_from_m5(m5):
    d = m5.groupby(m5.index.normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"),
                                              v=("v", "sum"))
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    syms = sorted(os.path.basename(f)[:-8] for f in glob.glob(f"{lib.DATA}/m5/*.parquet"))
    drows, irows = [], []
    for sym in syms:
        D0 = lib.load_daily(sym)
        if D0 is None or len(D0) < 400:
            continue
        D0 = D0[D0.index >= "2015-06-01"]
        Draw = scramble_daily(D0) if NOISE else D0[["o", "h", "l", "c", "v"]]
        D = lib.add_ind(Draw)
        OUTC = P.daily_outcomes(D)
        base = OUTC.groupby(OUTC.index.year).transform("mean")
        for name, fn in P.DAILY.items():
            s = fn(D).reindex(D.index).fillna(False).astype(bool)
            s &= D.index >= "2016-03-01"
            for d in D.index[s.values]:
                r = OUTC.loc[d]
                drows.append(dict(pattern=name, sym=sym, day=d, **r.to_dict(),
                                  **{"base_" + k: base.loc[d, k] for k in OUTC.columns}))
        # weekly sandwich
        W = lib.add_ind(lib.weekly(Draw), smas=(10, 20, 50))
        b = ((W.c - W.o) / W.atr).values
        for i in range(2, len(W)):
            if b[i - 2] <= -0.5 and 0 < b[i - 1] <= 0.4 and b[i] <= -1.0 and b[i] < b[i - 2]:
                wk_end = W.index[i]
                d = D.index[D.index <= wk_end]
                if len(d) and d[-1] >= pd.Timestamp("2016-03-01"):
                    r = OUTC.loc[d[-1]]
                    drows.append(dict(pattern="WEEKLY sandwich (red, small green, big red)", sym=sym, day=d[-1],
                                      **r.to_dict(), **{"base_" + k: base.loc[d[-1], k] for k in OUTC.columns}))
        # intraday
        m5 = lib.load_m5(sym)
        if m5 is None or len(m5) < 20000:
            print(sym, "daily only", flush=True); continue
        m5 = m5[m5.index >= "2016-01-01"]
        if NOISE:
            m5 = scramble_m5(m5)
            Di = lib.add_ind(daily_from_m5(m5))
        else:
            Di = D
        G = I.grid(m5, Di)
        OC = I.outcomes(G)
        B = I.baselines(OC, G["days"])
        SIG = I.signals(G)
        days = G["days"]
        for name, a in SIG.items():
            dd, ss = np.where(a)
            for d_, s_ in zip(dd, ss):
                if days[d_] < pd.Timestamp("2016-03-01"):
                    continue
                rec = dict(pattern=name, sym=sym, day=days[d_], slot=s_)
                for k in OC:
                    rec[k] = OC[k][d_, s_]
                    rec["base_" + k] = B[k][d_, s_]
                irows.append(rec)
        print(sym, "done", flush=True)
    tag = "_NOISE" if NOISE else ""
    dd = pd.DataFrame(drows); ii = pd.DataFrame(irows)
    dd.to_csv(f"{OUT}/pattern_signals_daily{tag}.csv.gz", index=False)
    ii.to_csv(f"{OUT}/pattern_signals_intraday{tag}.csv.gz", index=False)
    summarize(dd, ii, tag)


def summarize(dd, ii, tag=""):
    res = []
    for kind, df, cols, wcol, rcol in (
            ("daily", dd, ("ret_1d", "ret_3d", "ret_5d", "ret_10d", "atr_3d", "atr_5d", "win_1atr"), "win_1atr", "ret_5d"),
            ("intraday", ii, ("ret_close", "ret_next", "atr_close", "win_half_atr"), "win_half_atr", "ret_close")):
        if len(df) == 0:
            continue
        df = df.copy()
        df["day"] = pd.to_datetime(df.day)
        df["week"] = df.day.dt.to_period("W").astype(str)
        for name, g in df.groupby("pattern"):
            for per, gg in (("discovery", g[g.day < P.SPLIT]), ("holdout", g[g.day >= P.SPLIT])):
                st = P.score(gg, cols)
                res.append(dict(kind=kind, pattern=name, period=per, wcol=wcol, rcol=rcol, **st))
    R = pd.DataFrame(res)
    verdicts = []
    for (kind, name), g in R.groupby(["kind", "pattern"]):
        d = g[g.period == "discovery"].iloc[0]
        h = g[g.period == "holdout"].iloc[0] if (g.period == "holdout").any() else None
        w, rc = d.wcol, d.rcol
        ok_d = d.n >= 30 and d[w] > 0 and d[w + "_t"] >= 2.0 and d[rc] > 0
        ok_h = h is not None and h.n >= 30 and h[w] > 0 and h[w + "_t"] >= 1.5 and h[rc] > 0
        verdicts.append(dict(kind=kind, pattern=name, discovery_pass=ok_d, holdout_pass=ok_h, PASS=ok_d and ok_h))
    V = pd.DataFrame(verdicts)
    R.to_csv(f"{OUT}/pattern_scores{tag}.csv", index=False)
    V.to_csv(f"{OUT}/pattern_verdicts{tag}.csv", index=False)
    print(V.to_string())
    return R, V


if __name__ == "__main__":
    main()
