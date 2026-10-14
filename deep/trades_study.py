"""
ANSWER KEY, part 2: Taz's 576 exact-time trades (Robinhood timestamps), dissected with REAL option prices.
Per trade: chart conditions at entry on every timeframe; what the stock did after; where the next support
levels were; what the SAME contract was worth if he had exited at each level / rule instead
(real 1-minute OPRA prices, window = entry to 3 days after his exit or expiry); and what waiting for a
confirmation entry would have cost or saved on the same contract.
Percentages only, from his own recorded fill prices. No dollar P&L, no balances.
"""
import os
import numpy as np, pandas as pd
from .symdata import SymData
from . import lib, tradesim as ts
from .options_cache import option_minutes, price_at, window

OUT = "results/deep_analysis"
ALT_ENTRIES = ["reject_5m200", "hourly_20_retest", "break_prior_day_low", "failed_breakout", "m15_macd_cross"]


def stock_px(S, t):
    m = S.m5
    i = m.index.searchsorted(t, side="right") - 1
    return float(m.c.iloc[i]) if i >= 0 else np.nan


def main():
    os.makedirs(OUT, exist_ok=True)
    T = pd.read_csv("results_minute/minute_trades.csv")
    T["entry"] = pd.to_datetime(T.entry.str[:19])
    T["exit"] = pd.to_datetime(T.exit.str[:19])
    T["cp"] = T.occ.str[-9]
    T["exp"] = pd.to_datetime("20" + T.occ.str[-15:-9], format="%Y%m%d")
    OM = option_minutes()
    spy = SymData("SPY")
    vix = lib.load_vix()
    rows = []
    for sym, tt in T.groupby("sym"):
        S = SymData(sym, spy=spy.D if spy.ok else None, vix=vix)
        if not S.ok:
            print(sym, "no data", flush=True); continue
        for r in tt.itertuples():
            row = dict(idx=r.Index, sym=sym, occ=r.occ, cp=r.cp, entry=r.entry, exit=r.exit, px_in=r.px_in,
                       px_out=r.px_out, realized_pct=r.realized * 100, peak_held_pct=r.peak_held * 100,
                       peak_after_pct=r.peak_after * 100, hold_min=r.hold_min,
                       dte_at_entry=(r.exp - r.entry.normalize()).days)
            p_in = stock_px(S, r.entry)
            p_out = stock_px(S, r.exit)
            row["stock_in"], row["stock_out"] = p_in, p_out
            f = S.features_at(r.entry, p_in)
            if f is None:
                rows.append(row); continue
            row.update(f)
            a = f["atr"]
            sign = 1 if r.cp == "P" else -1
            row["stock_move_held_atr"] = sign * (p_in - p_out) / a
            if r.cp != "P":
                rows.append(row); continue
            o = S.outcome_short(r.entry, p_in, a)
            if o:
                row.update(o)
            # window of real option prices we have
            opt_end = min(r.exit + pd.Timedelta(days=3), r.exp + pd.Timedelta(hours=16))
            # ---------- exits: same contract, real prices ----------
            stop = ts.stop_for(S, r.entry, p_in, a)
            row["stop_atr"] = (stop - p_in) / a
            s_in = S.session_of(r.entry) or r.entry.normalize()
            lv = lib.levels_below(p_in, s_in, S.D, S.m5x, S.tf["h1"], min_gap=0.25 * a)
            row["levels_n"] = len(lv)
            for n in range(min(4, len(lv))):
                row[f"level{n+1}_name"] = lv[n][1]
                row[f"level{n+1}_dist_atr"] = (p_in - lv[n][0]) / a
            # which level was he out at? (count of levels between entry and his exit price)
            row["levels_passed_at_exit"] = sum(1 for p, _ in lv if p_out <= p)
            stop2 = ts.stop_for(S, r.entry, p_in, a, "hourly_swing")
            row["stop2_atr"] = (stop2 - p_in) / a
            for pre, stp in (("X", stop), ("Y", stop2)):     # X = tight stop (hour high), Y = hourly swing high
                sim = ts.simulate(S, r.entry, p_in, stp, lv)
                if not sim:
                    continue
                for x, (rv, tx) in sim.items():
                    row[f"{pre}_{x}_R"] = rv
                    if tx is not None:
                        if tx <= opt_end:
                            op = price_at(r.occ, tx)
                            row[f"{pre}_{x}_opt_pct"] = (op / r.px_in - 1) * 100 if pd.notna(op) else np.nan
                        else:
                            row[f"{pre}_{x}_opt_pct"] = np.nan
                            row[f"{pre}_{x}_beyond_window"] = 1
            # next level below HIS exit: did it get there before the stock rose back above his entry price?
            s_out = S.session_of(r.exit) or r.exit.normalize()
            lv_out = [x for x in lib.levels_below(p_out, s_out, S.D, S.m5x, S.tf["h1"], min_gap=0.25 * a)]
            if lv_out:
                nxt = lv_out[0][0]
                row["next_level_name"] = lv_out[0][1]
                row["next_level_dist_atr"] = (p_out - nxt) / a
                m5 = S.tf["m5"]
                P = m5[(m5.index > r.exit) & (m5.index <= opt_end)]
                hit = np.where(P.l.values <= nxt)[0]
                bad = np.where(P.h.values >= max(p_in, stop))[0]
                fh = hit[0] if len(hit) else 10 ** 9
                fb = bad[0] if len(bad) else 10 ** 9
                if fh < fb and fh < 10 ** 9:
                    row["next_level_hit"] = 1
                    tt_ = P.index[fh]
                    op = price_at(r.occ, tt_ - pd.Timedelta(minutes=5))
                    w = window(r.occ, tt_ - pd.Timedelta(minutes=5), tt_)
                    if w is not None and len(w):
                        op = float(w.c.max())
                    row["next_level_opt_pct"] = (op / r.px_in - 1) * 100 if pd.notna(op) else np.nan
                    row["next_level_hours_after_exit"] = (tt_ - r.exit).total_seconds() / 3600
                else:
                    row["next_level_hit"] = 0
            # ---------- entries: waiting for confirmation on the same contract ----------
            for e in ALT_ENTRIES:
                try:
                    alt = ts.find_entry(S, e, r.entry, p_in, window_sessions=2)
                except Exception:
                    alt = None
                if alt is None or alt[0] > opt_end:
                    row[f"A_{e}_fired"] = 0; continue
                te, pe = alt
                op = price_at(r.occ, te)
                row[f"A_{e}_fired"] = 1
                row[f"A_{e}_stock_better_atr"] = (pe - p_in) / a
                row[f"A_{e}_opt_vs_fill_pct"] = (op / r.px_in - 1) * 100 if pd.notna(op) else np.nan
                row[f"A_{e}_before_his_exit"] = int(te < r.exit)
                # result from the alt entry, exit at level1 / hourly trail, real option prices
                st2 = ts.stop_for(S, te, pe, a)
                s2 = S.session_of(te) or te.normalize()
                lv2 = lib.levels_below(pe, s2, S.D, S.m5x, S.tf["h1"], min_gap=0.25 * a)
                sim2 = ts.simulate(S, te, pe, st2, lv2)
                if sim2 and pd.notna(op) and op > 0:
                    for x in ("level1", "hourly_close_above_20", "day_close"):
                        rv, tx = sim2[x]
                        row[f"A_{e}_X_{x}_R"] = rv
                        if tx is not None and tx <= opt_end:
                            ox = price_at(r.occ, tx)
                            row[f"A_{e}_X_{x}_opt_pct"] = (ox / op - 1) * 100 if pd.notna(ox) else np.nan
            rows.append(row)
        print(sym, len(tt), "trades done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/trades_dissected.csv.gz", index=False)
    print("saved", len(df))


if __name__ == "__main__":
    main()
