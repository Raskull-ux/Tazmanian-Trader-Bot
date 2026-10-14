"""Winning puts: what if you had held for the NEXT support level instead of selling? Real option prices.
Two bail-out rules: stock back to your entry price (or the stop), or 0.25 ATR above where you sold."""
import numpy as np, pandas as pd
from .symdata import SymData
from . import lib, tradesim as ts
from .options_cache import price_at

OUT = "results/deep_analysis"


def main():
    T = pd.read_csv(f"{OUT}/trades_dissected.csv.gz", parse_dates=["entry", "exit"])
    T = T[(T.cp == "P") & (T.realized_pct > 0)].copy()
    T["exp"] = pd.to_datetime("20" + T.occ.str[-15:-9], format="%Y%m%d")
    res, cache = [], {}
    for r in T.itertuples():
        S = cache.get(r.sym) or SymData(r.sym)
        cache[r.sym] = S
        a = S.D.atr[S.D.index < r.entry.normalize()].iloc[-1]
        p_in, p_out = r.stock_in, r.stock_out
        stop = ts.stop_for(S, r.entry, p_in, a)
        opt_end = min(r.exit + pd.Timedelta(days=3), r.exp + pd.Timedelta(hours=16))
        s_out = S.session_of(r.exit) or r.exit.normalize()
        lv = lib.levels_below(p_out, s_out, S.D, S.m5x, S.tf["h1"], min_gap=0.25 * a)
        m5 = S.rth["m5"]
        P = m5[(m5.index > r.exit) & (m5.index <= opt_end)]
        if not lv or len(P) == 0:
            continue
        nxt = lv[0][0]
        for nm, bail in (("bail at your entry price", max(p_in, stop)), ("bail 0.25 ATR above your exit", p_out + 0.25 * a)):
            hit = np.where(P.l.values <= nxt)[0]
            bad = np.where(P.h.values >= bail)[0]
            fh = hit[0] if len(hit) else 10 ** 9
            fb = bad[0] if len(bad) else 10 ** 9
            if fh < fb:
                tt, how = P.index[fh], "reached next level"
            elif fb < 10 ** 9:
                tt, how = P.index[fb], "bailed"
            else:
                tt, how = P.index[-1], "window ended"
            op = price_at(r.occ, tt)
            res.append(dict(policy=nm, occ=r.occ, entry=r.entry, yours=r.realized_pct,
                            held=(op / r.px_in - 1) * 100 if pd.notna(op) else np.nan, how=how))
    R = pd.DataFrame(res).dropna()
    R.to_csv(f"{OUT}/hold_next_level.csv", index=False)
    print(R.groupby("policy")[["yours", "held"]].agg(["mean", "median"]))


if __name__ == "__main__":
    main()
