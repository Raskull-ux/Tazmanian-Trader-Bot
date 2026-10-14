"""
ANSWER KEY, part 1: every Tier A top call (bearish) Taz posted, dissected.
For each call: what the chart looked like on every timeframe, what happened next, how early it was,
which entry would have been better, which exit would have been better.
Every call gets 3 CONTROL entries (same name, same minute of day, random nearby day) run through the
exact same machinery, so we can tell 'this helps YOUR calls' from 'this helps any short'.
"""
import os, sys, random
import numpy as np, pandas as pd
from .symdata import SymData
from . import lib, tradesim as ts

OUT = "results/deep_analysis"
random.seed(7)


def run_one(S, t_call, label, cid):
    t0, p0 = S.entry_point(t_call)
    if t0 is None:
        return None
    f = S.features_at(t0, p0)
    if f is None:
        return None
    o = S.outcome_short(t0, p0, f["atr"])
    if o is None:
        return None
    row = dict(cid=cid, kind=label, sym=S.sym, t_call=t_call, t_entry=t0, p_entry=p0, **f, **o)
    sess = S.session_of(t0 - pd.Timedelta(minutes=1)) or t0.normalize()
    for e in ts.ENTRIES:
        try:
            r = ts.find_entry(S, e, t0, p0)
        except Exception:
            r = None
        if r is None:
            row[f"E_{e}_fired"] = 0
            continue
        te, pe = r
        row[f"E_{e}_fired"] = 1
        row[f"E_{e}_better_pct"] = (pe - p0) / p0 * 100           # + = sold higher than at the call
        row[f"E_{e}_hours_after"] = (te - t0).total_seconds() / 3600
        stop = ts.stop_for(S, te, pe, f["atr"])
        row[f"E_{e}_stop_atr"] = (stop - pe) / f["atr"]
        s_e = S.session_of(te) or te.normalize()
        lv = lib.levels_below(pe, s_e if te.hour * 60 + te.minute < 960 else s_e, S.D, S.m5, S.tf["h1"], min_gap=0.25 * f["atr"])
        sim = ts.simulate(S, te, pe, stop, lv)
        if sim is None:
            continue
        for x, (rv, _) in sim.items():
            row[f"E_{e}_X_{x}"] = rv
        if e == "at_call":
            row["levels_n"] = len(lv)
            for n in range(min(4, len(lv))):
                row[f"level{n+1}"] = lv[n][0]
                row[f"level{n+1}_name"] = lv[n][1]
                row[f"level{n+1}_dist_atr"] = (pe - lv[n][0]) / f["atr"]
            low5 = pe * (1 - o["drop_5d_pct"] / 100)
            row["levels_reached_5d"] = ts.levels_reached(lv, low5)
            # the level the 5-day move stopped at (deepest level reached)
            reached = [x for x in lv if low5 <= x[0]]
            row["deepest_level_5d"] = reached[-1][1] if reached else "none"
            row["deepest_level_5d_dist_atr"] = (pe - reached[-1][0]) / f["atr"] if reached else 0.0
    return row


def main():
    os.makedirs(OUT, exist_ok=True)
    g = pd.read_csv("results/call_grades/graded_calls.csv")
    g = g[(g.tier == "A") & (g.dir == "bear")].copy()
    g["t"] = pd.to_datetime(g.ts_utc, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    spy = SymData("SPY")
    spyD = spy.D if spy.ok else None
    vix = lib.load_vix()
    rows = []
    for sym, gg in g.groupby("ticker"):
        S = SymData(sym, spy=spyD, vix=vix)
        if not S.ok:
            print(sym, "no data", flush=True); continue
        for r in gg.itertuples():
            row = run_one(S, r.t, "call", r.Index)
            if row is None:
                continue
            rows.append(row)
            # controls: same name, same minute of day, random day within +-60 sessions
            s = S.session_of(r.t)
            if s is None:
                continue
            i = S.sessions.searchsorted(s)
            tod = pd.Timedelta(hours=r.t.hour, minutes=r.t.minute)
            for k in range(3):
                j = i + random.choice([x for x in range(-60, 61) if abs(x) > 5])
                if 220 <= j < len(S.sessions) - 11:
                    tc = S.sessions[j] + tod
                    cr = run_one(S, tc, "control", r.Index)
                    if cr is not None:
                        rows.append(cr)
        print(sym, len(gg), "calls done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/calls_dissected.csv.gz", index=False)
    print("saved", df.kind.value_counts().to_dict())


if __name__ == "__main__":
    main()
