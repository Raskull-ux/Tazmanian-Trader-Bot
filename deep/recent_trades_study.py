"""Sep-Oct 2026 trades from Taz's Discord posts, replayed on REAL 1-minute option prices (Alpaca).
Per trade: what the contract traded at when he got in and out, the best it traded at after he sold
(before expiry), what it was worth if held to the next support level (bail if the stock gets back to his entry),
and what it was worth at expiration. Percentages only, from the real prints."""
import os
import numpy as np, pandas as pd
from .symdata import SymData
from . import lib, tradesim as ts

SRC = "results/recent_options"
OUT = "results/deep_analysis"


def px_at(b, t, how="after"):
    if how == "after":
        x = b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=30))]
        return (float(x.c.iloc[0]), x.t.iloc[0]) if len(x) else (np.nan, None)
    x = b[(b.t <= t) & (b.t >= t - pd.Timedelta(minutes=30))]
    return (float(x.c.iloc[-1]), x.t.iloc[-1]) if len(x) else (np.nan, None)


def main():
    T = pd.read_csv("deep/recent_trades.csv", parse_dates=["entry", "exit"])
    rows, cache = [], {}
    for r in T.itertuples():
        f = f"{SRC}/{r.occ}.csv"
        sym = r.occ[:-15]
        cp = r.occ[-9]
        strike = int(r.occ[-8:]) / 1000
        exp = pd.Timestamp("20" + r.occ[-15:-9])
        rec = dict(occ=r.occ, entry=r.entry, exit=r.exit, posted=r.posted)
        if not os.path.exists(f):
            rec["status"] = "no option bars"; rows.append(rec); continue
        b = pd.read_csv(f, parse_dates=["t"])
        p_in, t_in = px_at(b, r.entry)
        rec["opt_in"] = p_in
        end = min(exp + pd.Timedelta(hours=16), b.t.max())
        if pd.notna(r.exit):
            p_out, t_out = px_at(b, r.exit, "before")
            if np.isnan(p_out):
                p_out, t_out = px_at(b, r.exit)
            rec["opt_out"] = p_out
            rec["your_pct"] = (p_out / p_in - 1) * 100
            after = b[(b.t > r.exit) & (b.t <= end)]
            if len(after):
                k = after.c.idxmax()
                rec["best_after_pct"] = (after.c[k] / p_in - 1) * 100
                rec["best_after_at"] = after.t[k]
        last = b[b.t <= end]
        rec["at_expiry_or_now_pct"] = (last.c.iloc[-1] / p_in - 1) * 100 if len(last) else np.nan
        rec["expired"] = exp + pd.Timedelta(hours=16) <= b.t.max() + pd.Timedelta(minutes=30)
        # stock: next support level under the stock price at his exit (puts) / resistance above (calls)
        S = cache.get(sym) or SymData(sym)
        cache[sym] = S
        if S.ok and pd.notna(r.exit) and cp == "P":
            m = S.m5
            s_in = float(m.c.iloc[m.index.searchsorted(r.entry, side="right") - 1])
            s_out = float(m.c.iloc[m.index.searchsorted(r.exit, side="right") - 1])
            a = S.D.atr[S.D.index < r.exit.normalize()].iloc[-1]
            sess = S.session_of(r.exit) or r.exit.normalize()
            lv = lib.levels_below(s_out, sess, S.D, S.m5x, S.tf["h1"], min_gap=0.25 * a)
            if lv:
                nxt = lv[0][0]
                rec["next_level"] = f"{nxt:.2f} ({lv[0][1]})"
                P = S.rth["m5"]
                P = P[(P.index > r.exit) & (P.index <= end)]
                hit = np.where(P.l.values <= nxt)[0]
                bad = np.where(P.h.values >= s_in)[0]
                fh = hit[0] if len(hit) else 10 ** 9
                fb = bad[0] if len(bad) else 10 ** 9
                if fh < fb:
                    tt, how = P.index[fh], "reached next level"
                elif fb < 10 ** 9:
                    tt, how = P.index[fb], "stock back to your entry: bail"
                else:
                    tt, how = end, "neither before expiry/now"
                w = b[(b.t >= tt - pd.Timedelta(minutes=5)) & (b.t <= tt)]
                op = float(w.c.max()) if len(w) else px_at(b, tt, "before")[0]
                rec["hold_next_level_pct"] = (op / p_in - 1) * 100 if pd.notna(op) else np.nan
                rec["hold_next_level_how"] = how
                rec["hold_next_level_at"] = tt
        rows.append(rec)
    D = pd.DataFrame(rows)
    D.to_csv(f"{OUT}/recent_trades_replay.csv", index=False)
    pd.set_option("display.width", 250)
    cols = [c for c in ("occ", "entry", "opt_in", "opt_out", "your_pct", "best_after_pct", "best_after_at",
                        "hold_next_level_pct", "hold_next_level_how", "at_expiry_or_now_pct") if c in D]
    print(D[cols].round(2).to_string())


if __name__ == "__main__":
    main()
