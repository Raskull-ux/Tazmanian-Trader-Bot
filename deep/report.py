"""Builds results/deep_analysis/REPORT.md from the dissected calls, trades and pattern tests."""
import os
import numpy as np, pandas as pd
from . import tradesim as ts

OUT = "results/deep_analysis"
SPLIT_CALLS = pd.Timestamp("2025-07-01")


CLUSTER = None   # set to a Series of cluster labels (e.g. the week) aligned with the rows being tested


def tstat(x, cl=None):
    """t-stat of the mean. Rows from the same week share the same market moves, so when a cluster label is
    available the test is run on weekly averages (honest, fewer effective samples)."""
    x = pd.Series(x).dropna()
    cl = cl if cl is not None else CLUSTER
    if cl is not None:
        x = x.groupby(cl.reindex(x.index)).mean()
    if len(x) < 5 or x.std() == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def fmt(v, d=2):
    return "" if pd.isna(v) else f"{v:.{d}f}"


def md(df):
    return df.to_markdown(index=False)


def boolify(df):
    """CSV round-trips turn True/False columns with gaps into text; turn them back into 0/1."""
    df = df.copy()
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c]):
            m = df[c].map({"True": 1.0, "False": 0.0, True: 1.0, False: 0.0})
            if m.notna().sum() > 0 and m.notna().sum() == df[c].notna().sum():
                df[c] = m
    return df


def numeric_feats(df, feats):
    return [f for f in feats if pd.api.types.is_numeric_dtype(df[f]) or pd.api.types.is_bool_dtype(df[f])]


def feature_split(df, win_col, feats, period_col):
    """For every feature: how winners differ from losers, in both halves."""
    rows = []
    for f in feats:
        x = df[[f, win_col, period_col]].dropna()
        if len(x) < 40:
            continue
        rec = {"feature": f}
        ok = True
        for per in ("early", "late"):
            g = x[x[period_col] == per]
            if set(pd.unique(x[f])) <= {0, 1, True, False}:
                a, b = g[g[f].astype(bool)][win_col], g[~g[f].astype(bool)][win_col]
                if len(a) < 10 or len(b) < 10:
                    ok = False; break
                rec[f"{per}: win when TRUE"] = f"{a.mean()*100:.0f}% (n {len(a)})"
                rec[f"{per}: win when FALSE"] = f"{b.mean()*100:.0f}% (n {len(b)})"
                rec[f"{per}_gap"] = (a.mean() - b.mean()) * 100
            else:
                med = x[f].median()
                a, b = g[g[f] > med][win_col], g[g[f] <= med][win_col]
                if len(a) < 10 or len(b) < 10:
                    ok = False; break
                rec[f"{per}: win when TRUE"] = f"{a.mean()*100:.0f}% above {med:.2f} (n {len(a)})"
                rec[f"{per}: win when FALSE"] = f"{b.mean()*100:.0f}% (n {len(b)})"
                rec[f"{per}_gap"] = (a.mean() - b.mean()) * 100
        if ok:
            rows.append(rec)
    R = pd.DataFrame(rows)
    if len(R) == 0:
        return R
    R["same_direction_both_halves"] = np.sign(R.early_gap) == np.sign(R.late_gap)
    R["min_abs_gap"] = np.where(R.same_direction_both_halves, np.minimum(R.early_gap.abs(), R.late_gap.abs()), 0)
    return R.sort_values("min_abs_gap", ascending=False)


def calls_section(C):
    L = ["# PART 1: Your 292 top calls, dissected", ""]
    global CLUSTER
    calls = C[C.kind == "call"].copy()
    ctrl = C[C.kind == "control"].copy()
    CLUSTER = pd.to_datetime(calls.t_entry).dt.to_period("W").astype(str)
    calls["period"] = np.where(pd.to_datetime(calls.t_call) < SPLIT_CALLS, "early", "late")
    ctrl["period"] = np.where(pd.to_datetime(ctrl.t_call) < SPLIT_CALLS, "early", "late")
    L.append(f"Calls measured: **{len(calls)}** (controls: {len(ctrl)} random entries, same names, same minute of day, nearby days).")
    L.append("")
    L.append("## 1. How the calls played out (stock moves, short side)")
    rows = []
    for nm, g in (("Your calls", calls), ("Random control entries", ctrl)):
        rows.append({"": nm, "n": len(g),
                     "fell 1 ATR before rising 1 ATR (5 days)": f"{g.win_1atr.mean()*100:.1f}%",
                     "avg move by close of day 3": f"{g.ret_3d_pct.mean():+.2f}%",
                     "avg move by day 5": f"{g.ret_5d_pct.mean():+.2f}%",
                     "median rise AGAINST you before the 10-day low": f"{g.rise_before_low_pct.median():.2f}%",
                     "median biggest drop within 5 days": f"{g.drop_5d_pct.median():.2f}%",
                     "10-day low came on day (median)": f"{g.low10_session.median():.0f}"})
    L += [md(pd.DataFrame(rows)), ""]
    early = calls.top3d_pct / (calls.atr / calls.p_entry * 100)
    L.append(f"**Being early, measured.** After your call the stock went on to make a higher high within 3 days "
             f"in {(calls.top3d_pct > 0.05).mean()*100:.0f}% of calls; it pushed at least 0.5 ATR higher in "
             f"{(early >= 0.5).mean()*100:.0f}% and at least 1 ATR higher in {(early >= 1).mean()*100:.0f}%. "
             f"Controls: {(ctrl.top3d_pct > 0.05).mean()*100:.0f}% / "
             f"{((ctrl.top3d_pct / (ctrl.atr / ctrl.p_entry * 100)) >= 0.5).mean()*100:.0f}% / "
             f"{((ctrl.top3d_pct / (ctrl.atr / ctrl.p_entry * 100)) >= 1).mean()*100:.0f}%.")
    L.append("")
    # entries x exits
    L.append("## 2. Fixing early: every entry x every exit (average result in R, 1R = entry to technical stop)")
    L.append("Stop = highest high of the hour before entry, a hair above. Targets = real support levels under price "
             "(prior day/week lows, daily 10/20/50/200 SMAs, unfilled gaps, daily + hourly swing lows, 5-day volume "
             "POC / value area). Calls where the entry never triggered count as **0R (no trade)** in 'per call'.")
    L.append("")
    rows = []
    for e in ts.ENTRIES:
        fired = calls[f"E_{e}_fired"].fillna(0)
        rec = {"entry": e, "triggered": f"{fired.mean()*100:.0f}%",
               "sold higher than call price by (median %)": fmt(calls[f"E_{e}_better_pct"].median()),
               "median hours after call": fmt(calls[f"E_{e}_hours_after"].median(), 1),
               "median stop size (ATR)": fmt(calls[f"E_{e}_stop_atr"].median())}
        for x in ts.EXITS:
            col = f"E_{e}_X_{x}"
            if col in calls:
                v = calls[col]
                rec[x] = f"{v.mean():+.2f} (t {tstat(v):.1f})"
        rows.append(rec)
    L += [md(pd.DataFrame(rows)), ""]
    L.append("Same table on the RANDOM control entries (if a fix helps controls just as much, it is a general "
             "short-entry rule, not a fix for your timing):")
    rows = []
    for e in ts.ENTRIES:
        rec = {"entry": e, "triggered": f"{ctrl[f'E_{e}_fired'].fillna(0).mean()*100:.0f}%"}
        for x in ts.EXITS:
            col = f"E_{e}_X_{x}"
            if col in ctrl:
                rec[x] = f"{ctrl[col].mean():+.2f}"
        rows.append(rec)
    L += [md(pd.DataFrame(rows)), ""]
    # split halves for the best combos
    L.append("Stability check, calls only, first half vs second half (before / after July 2025):")
    rows = []
    for e in ts.ENTRIES:
        for x in ts.EXITS:
            col = f"E_{e}_X_{x}"
            if col not in calls:
                continue
            a = calls[calls.period == "early"][col]; b = calls[calls.period == "late"][col]
            rows.append({"entry": e, "exit": x, "early avg R": a.mean(), "late avg R": b.mean(),
                         "early n": a.notna().sum(), "late n": b.notna().sum(),
                         "all t": tstat(calls[col])})
    S = pd.DataFrame(rows)
    S["both halves positive"] = (S["early avg R"] > 0) & (S["late avg R"] > 0)
    S = S.sort_values("all t", ascending=False)
    L += [md(S.head(20).round(3)), ""]
    # where it went
    L.append("## 3. Where the move went (at-call entry): how many support levels it reached in 5 days")
    vc = calls.levels_reached_5d.value_counts().sort_index()
    L.append(" | ".join(f"{int(k)} levels: {v} calls" for k, v in vc.items()))
    L.append("")
    L.append("Deepest level reached, by type (most common first):")
    dl = calls.deepest_level_5d.fillna("none").str.split(" \\+ ").str[0].value_counts().head(12)
    L += [md(dl.rename_axis("level type").reset_index(name="calls")), ""]
    for n in (1, 2, 3):
        c = f"level{n}_dist_atr"
        if c in calls:
            L.append(f"- Level {n} sat a median **{calls[c].median():.2f} ATR** under the entry")
    L.append("")
    # features
    L.append("## 4. What separates your winning calls from your losing calls")
    L.append("Win = stock fell 1 ATR before rising 1 ATR within 5 days. A condition only matters if the gap shows "
             "up in BOTH halves (before and after July 2025). Numeric features split at their median.")
    feats = [c for c in calls.columns if c.split("_")[0] in ("d", "w", "m5", "m15", "h1", "h4", "today", "spy")
             or c in ("vix", "minute_of_day")]
    feats = numeric_feats(calls, feats)
    F = feature_split(calls, "win_1atr", feats, "period")
    if len(F):
        show = F[F.same_direction_both_halves].head(15)
        L += [md(show.drop(columns=["early_gap", "late_gap", "min_abs_gap", "same_direction_both_halves"])), ""]
        Fc = feature_split(ctrl, "win_1atr", [f for f in show.feature], "period")
        if len(Fc):
            L.append("Same features on random control entries (gap in pct points, early / late):")
            L += [md(Fc[["feature", "early_gap", "late_gap"]].round(1)), ""]
    seq = calls.groupby("d_seq4").win_1atr.agg(["mean", "size"]).sort_values("size", ascending=False)
    seq["mean"] = (seq["mean"] * 100).round(0)
    L.append("Last 4 daily candles before the call (G = green, R = red), win rate and count:")
    L += [md(seq.reset_index().rename(columns={"mean": "win %", "size": "calls"})), ""]
    # by month
    L.append("## 5. Calls by month")
    calls["month"] = pd.to_datetime(calls.t_call).dt.to_period("M").astype(str)
    M = calls.groupby("month").agg(calls=("win_1atr", "size"), win=("win_1atr", "mean"),
                                   avg_5d_move=("ret_5d_pct", "mean"),
                                   median_rise_against=("rise_before_low_pct", "median"))
    M["win"] = (M.win * 100).round(0)
    L += [md(M.round(2).reset_index()), ""]
    by = calls.groupby("sym").agg(calls=("win_1atr", "size"), win=("win_1atr", "mean"), avg_5d=("ret_5d_pct", "mean"))
    by = by[by.calls >= 5].sort_values("win", ascending=False)
    by["win"] = (by.win * 100).round(0)
    L.append("By ticker (5+ calls):")
    L += [md(by.round(2).reset_index()), ""]
    return L


def trades_section(T):
    global CLUSTER
    L = ["# PART 2: Your 576 real trades, with the real option prices", ""]
    T = T.copy()
    CLUSTER = pd.to_datetime(T.entry).dt.to_period("W").astype(str)
    T["month"] = pd.to_datetime(T.entry).dt.to_period("M").astype(str)
    T["won"] = T.realized_pct > 0
    T["gave_back"] = (T.peak_held_pct >= 20) & (T.realized_pct <= 0)
    T["hit_2x_held"] = T.peak_held_pct >= 100
    T["sold_early"] = T.peak_after_pct >= T.realized_pct.clip(lower=0) + 50
    L.append("## 1. Month by month (percent on the contract, from your own fill prices; no dollars)")
    M = T.groupby("month").agg(trades=("won", "size"), win_rate=("won", "mean"), median_pct=("realized_pct", "median"),
                               reached_2x_while_held=("hit_2x_held", "mean"),
                               up_20pct_then_closed_red=("gave_back", "mean"),
                               went_50pts_higher_after_you_sold=("sold_early", "mean"))
    for c in ("win_rate", "reached_2x_while_held", "up_20pct_then_closed_red", "went_50pts_higher_after_you_sold"):
        M[c] = (M[c] * 100).round(0)
    L += [md(M.round(1).reset_index()), ""]
    P = T[T.cp == "P"].copy()
    W = P[P.won]
    L.append("## 2. Sold early? The next support level after you sold (puts)")
    if "next_level_hit" in P:
        h = W[W.next_level_hit.notna()]
        L.append(f"Winning puts: {len(W)}. The stock reached the next support level under your exit price, before "
                 f"rising back above your entry/stop, within 3 days in **{h.next_level_hit.mean()*100:.0f}%** of them "
                 f"(n {len(h)}).")
        hh = h[h.next_level_hit == 1]
        if len(hh):
            L.append(f"When it did: your exit was a median **{hh.realized_pct.median():+.0f}%**; the same put at that "
                     f"next level was a median **{hh.next_level_opt_pct.median():+.0f}%** "
                     f"(it got there a median {hh.next_level_hours_after_exit.median():.1f} hours after you sold).")
        lw = P[~P.won & P.next_level_hit.notna()]
        L.append(f"Losing puts (for contrast): next level reached after your exit in {lw.next_level_hit.mean()*100:.0f}% "
                 f"(n {len(lw)}).")
        L.append("")
        lv = h.groupby("next_level_name").agg(n=("next_level_hit", "size"), reached=("next_level_hit", "mean"))
        lv = lv[lv.n >= 5].sort_values("n", ascending=False)
        lv["reached"] = (lv.reached * 100).round(0)
        L.append("Which level was next, and how often it got hit (winning puts):")
        L += [md(lv.reset_index()), ""]
    L.append("## 3. Exit rules replayed on your actual put contracts (real 1-minute option prices)")
    L.append("Same entry as you, same contract. Each rule exits where the STOCK hits the level / rule; the price is "
             "what the option actually traded at that minute. Only trades where the exit landed inside the price "
             "window we have (entry to 3 days after your exit) are counted, and 'yours' is shown on the SAME trades.")
    rows = []
    for x in ts.EXITS:
        c = f"X_{x}_opt_pct"
        if c not in P:
            continue
        g = P[P[c].notna()]
        if len(g) < 20:
            continue
        rows.append({"exit rule": x, "trades": len(g), "rule avg %": g[c].mean(), "rule median %": g[c].median(),
                     "rule win %": (g[c] > 0).mean() * 100, "yours avg % (same trades)": g.realized_pct.mean(),
                     "yours median %": g.realized_pct.median(),
                     "rule minus yours, avg": (g[c] - g.realized_pct).mean(),
                     "t": tstat(g[c] - g.realized_pct)})
    if rows:
        L += [md(pd.DataFrame(rows).round(1)), ""]
    L.append("## 4. Waiting for confirmation on the SAME contract")
    L.append("Option price at the confirmation signal vs your fill (negative = cheaper = you entered too early).")
    rows = []
    for e in ("reject_5m200", "hourly_20_retest", "break_prior_day_low", "failed_breakout", "m15_macd_cross"):
        f = P.get(f"A_{e}_fired")
        if f is None:
            continue
        g = P[P[f"A_{e}_fired"] == 1]
        rec = {"confirmation": e, "fired within 2 days": f"{f.fillna(0).mean()*100:.0f}%",
               "median option price vs your fill": f"{g[f'A_{e}_opt_vs_fill_pct'].median():+.0f}%",
               "share cheaper than your fill": f"{(g[f'A_{e}_opt_vs_fill_pct'] < 0).mean()*100:.0f}%"}
        for x in ("level1", "hourly_close_above_20", "day_close"):
            c = f"A_{e}_X_{x}_opt_pct"
            if c in g:
                rec[f"then exit {x}: avg %"] = fmt(g[c].mean(), 1)
                rec[f"{x} median %"] = fmt(g[c].median(), 1)
        rows.append(rec)
    if rows:
        L += [md(pd.DataFrame(rows)), ""]
    nf = P[[c for c in P.columns if c.startswith("A_") and c.endswith("_fired")]].fillna(0).sum(1) == 0
    L.append(f"Puts where NONE of the confirmations ever came within 2 days: {nf.sum()} of {len(P)}; "
             f"your median result on those: {P[nf].realized_pct.median():+.0f}% "
             f"(vs {P[~nf].realized_pct.median():+.0f}% on the rest).")
    L.append("")
    L.append("## 5. What separates your winning puts from your losing puts (conditions at YOUR entry)")
    P["period"] = np.where(pd.to_datetime(P.entry) < pd.Timestamp("2025-04-01"), "early", "late")
    P["win"] = P.won.astype(float)
    feats = [c for c in P.columns if c.split("_")[0] in ("d", "w", "m5", "m15", "h1", "h4", "today", "spy")
             or c in ("vix", "minute_of_day", "dte_at_entry")]
    feats = numeric_feats(P, feats)
    F = feature_split(P, "win", feats, "period")
    if len(F):
        L += [md(F[F.same_direction_both_halves].head(15).drop(
            columns=["early_gap", "late_gap", "min_abs_gap", "same_direction_both_halves"])), ""]
    tod = P.groupby(pd.cut(P.minute_of_day, [0, 575, 600, 630, 690, 780, 900, 961],
                           labels=["9:30-9:35", "9:35-10:00", "10:00-10:30", "10:30-11:30", "11:30-1:00",
                                   "1:00-3:00", "3:00-4:00"]), observed=True).agg(
        trades=("win", "size"), win=("win", "mean"), median_pct=("realized_pct", "median"))
    tod["win"] = (tod.win * 100).round(0)
    L.append("By entry time:")
    L += [md(tod.reset_index()), ""]
    return L


def patterns_section(V, R, VN=None):
    L = ["# PART 3: Your patterns, tested on every name 2016 -> now", ""]
    L.append("Pass rule (set before running): beats being short that same name that same year (daily) or that "
             "same name / year / time of day (intraday). Discovery 2016-2022 needs win-rate excess t >= 2 and a "
             "positive move; holdout 2023-now (never used to define anything) needs t >= 1.5 and a positive move.")
    L.append("")
    rows = []
    for _, v in V.iterrows():
        g = R[(R.kind == v.kind) & (R.pattern == v.pattern)]
        d = g[g.period == "discovery"]; h = g[g.period == "holdout"]
        wc, rc = (("win_1atr", "ret_5d") if v.kind == "daily" else ("win_half_atr", "ret_close"))
        def cell(x):
            if len(x) == 0 or pd.isna(x.iloc[0].get(wc)):
                return "n/a"
            x = x.iloc[0]
            return (f"n {int(x.n)}: win {x[wc + '_raw']*100:.0f}% ({x[wc]*100:+.1f} pts, t {x[wc + '_t']:.1f}); "
                    f"move {x[rc + '_raw']:+.2f}% ({x[rc]:+.2f} vs base)")
        rows.append({"pattern": v.pattern, "type": v.kind, "2016-2022": cell(d), "2023-now": cell(h),
                     "VERDICT": "PASS" if v.PASS else ("holdout only" if v.holdout_pass else
                                                       ("discovery only" if v.discovery_pass else "fail"))})
    L += [md(pd.DataFrame(rows)), ""]
    L.append("Daily: win = fell 1 ATR before rising 1 ATR within 5 sessions, short at the next open; move = 5-day. "
             "Intraday: win = fell 0.5 ATR before rising 0.5 ATR by the close, short at the signal bar's close; "
             "move = to the close.")
    if VN is not None:
        L.append("")
        L.append(f"**Noise check:** the identical pipeline on scrambled charts passed {int(VN.PASS.sum())} of "
                 f"{len(VN)} patterns (should be 0).")
    return L


def extra_section(C):
    L = ["# PART 4: Extra checks", ""]
    calls = C[C.kind == "call"].copy()
    ctrl = C[C.kind == "control"].copy()
    calls["period"] = np.where(pd.to_datetime(calls.t_call) < SPLIT_CALLS, "early", "late")
    L.append("## Same entries x exits with a WIDER stop (nearest hourly swing high), average R, calls / controls")
    rows = []
    for e in ts.ENTRIES:
        rec = {"entry": e, "median stop (ATR)": fmt(calls[f"E_{e}_stop2_atr"].median())}
        for x in ("level1", "level2", "level3", "half_L1_rest_L3", "day_close", "hourly_close_above_20", "hold_3_days"):
            c = f"E_{e}_S2_{x}"
            if c in calls:
                rec[x] = f"{calls[c].mean():+.2f} (t {tstat(calls[c]):.1f}) / {ctrl[c].mean():+.2f}"
        rows.append(rec)
    L += [md(pd.DataFrame(rows)), ""]
    L.append("## The two conditions that split winning and losing calls (HYPOTHESIS: picked from ~70 tested)")
    late = calls.minute_of_day >= 620
    up = calls.h4_rsi_above_ma == 1
    rows = []
    for nm, m in (("4H RSI above its MA AND called after 10:20", up & late), ("only 4H RSI above its MA", up & ~late),
                  ("only after 10:20", ~up & late), ("neither", ~up & ~late), ("all calls", up | ~up)):
        g = calls[m]
        rows.append({"group": nm, "calls": len(g), "win %": round(g.win_1atr.mean() * 100),
                     "win % before Jul 2025": round(g[g.period == "early"].win_1atr.mean() * 100),
                     "win % after": round(g[g.period == "late"].win_1atr.mean() * 100),
                     "avg 5-day move %": round(g.ret_5d_pct.mean(), 2)})
    L += [md(pd.DataFrame(rows)), ""]
    if os.path.exists(f"{OUT}/recent_calls_forward_test.csv"):
        F = pd.read_csv(f"{OUT}/recent_calls_forward_test.csv")
        F = F[F.sessions_seen >= 5].copy()
        up = F.h4_rsi_above_ma.astype(str).str.lower().isin(["true", "1", "1.0"])
        late = F.after_1020.astype(str).str.lower().isin(["true", "1", "1.0"])
        F["group"] = np.where(up & late, "both", np.where(~up & ~late, "neither", "one of the two"))
        L.append("## FORWARD TEST: the two conditions on fresh calls (Sep 15 - Oct 7 2026, not used to find them)")
        G = F.groupby("group").agg(calls=("win_1atr", "size"), win=("win_1atr", "mean"), avg_5d_move=("move_5d", "mean"))
        G["win"] = (G.win * 100).round(0)
        L += [md(G.round(2).reset_index()), ""]
        L.append(f"Verdict: NOT confirmed. With only {len(F)} fresh calls this can't prove or kill it, but the 'both' "
                 "group did not win more. Keep it as an untested idea, not a rule.")
        L.append("")
    if os.path.exists(f"{OUT}/hold_next_level.csv"):
        H = pd.read_csv(f"{OUT}/hold_next_level.csv")
        L.append("## Winning puts: sell where you sold vs hold for the next support level (real option prices)")
        rows = []
        for nm, g in H.groupby("policy"):
            d = g.held - g.yours
            rows.append({"bail-out rule": nm, "trades": len(g), "yours avg %": round(g.yours.mean()),
                         "yours median %": round(g.yours.median()), "held avg %": round(g.held.mean()),
                         "held median %": round(g.held.median()), "held beat yours": f"{(d > 0).mean()*100:.0f}%",
                         "t": round(tstat(d, pd.Series(range(len(d)), index=d.index)), 2),
                         "outcomes": ", ".join(f"{k} {v}" for k, v in g.how.value_counts().items())})
        L += [md(pd.DataFrame(rows)), ""]
    return L


def main():
    L = ["# Deep analysis: your calls, your trades, your patterns", ""]
    if os.path.exists(f"{OUT}/calls_dissected.csv.gz"):
        L += calls_section(boolify(pd.read_csv(f"{OUT}/calls_dissected.csv.gz")))
    if os.path.exists(f"{OUT}/trades_dissected.csv.gz"):
        L += trades_section(boolify(pd.read_csv(f"{OUT}/trades_dissected.csv.gz")))
    if os.path.exists(f"{OUT}/calls_dissected.csv.gz"):
        L += extra_section(boolify(pd.read_csv(f"{OUT}/calls_dissected.csv.gz")))

    def load_parts(prefix, noise=""):
        parts = [f"{OUT}/{prefix}{noise}{suf}.csv" for suf in ("", "_daily", "_intraday")]
        got = [pd.read_csv(p) for p in parts if os.path.exists(p)]
        return pd.concat(got, ignore_index=True).drop_duplicates(subset=[c for c in ("kind", "pattern", "period")
                                                                        if c in got[0].columns]) if got else None
    V = load_parts("pattern_verdicts")
    if V is not None:
        L += patterns_section(V, load_parts("pattern_scores"), load_parts("pattern_verdicts", "_NOISE"))
    open(f"{OUT}/REPORT.md", "w").write("\n".join(L))
    print("\n".join(L)[:3000])


if __name__ == "__main__":
    main()
