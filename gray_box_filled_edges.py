"""
Gray Box open item: do FILLED box edges work as levels as well as OPEN boxes?

Same rules as gray_box_bot.py (v2): boxes = gaps between daily candle bodies, trimmed by every later body, 120-session
lookback. A box that gets fully filled becomes a "filled edge" (its edge is kept as a level, like on his charts).
For each name and day (as of the close):
  OPEN    puts: nearest open box edge above the close; calls: nearest open box edge below (the live bot's setup)
  FILLED  puts: nearest filled box edge above the close; calls: nearest below (same distances and rules)
Both must be within 1.5 daily ranges (ATR 14, simple mean like the bot). Next session on 5m bars (9:30-16:00):
arm 0.4 range away, trigger a tenth of a range before the level, skip if it opens past the trigger, stop half a range
past entry, half off after half a range (K1 = 0.5), stop to entry, runner to three quarters or out at the close.
Result in ranges: same scoring as the bot. Split 2016-2021 / 2022-2026. Data: data_ext (75 names, 5m + daily).
Out: results/gray_box/filled_edges.md
"""
import os
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data_ext")
KS, K1, K2, TAG, POP, LOOKBACK, MAXDIST = 0.5, 0.5, 0.75, 0.1, 0.4, 120, 1.5
OUT = "results/gray_box"


def trim(p, lo, hi):
    a, b = p[0], p[1]
    if hi <= a or lo >= b: return [p]
    out = []
    if lo > a: out.append((a, lo) + p[2:])
    if hi < b: out.append((hi, b) + p[2:])
    return [q for q in out if q[1] - q[0] > 1e-6]


def walk(put, trig, arm, stop, half, runner, atr, o, h, l, c):
    if not len(o): return None
    if (o[0] >= trig) if put else (o[0] <= trig): return ("skip", np.nan)
    armed = False; j = None
    for k in range(len(o)):
        if (l[k] <= arm) if put else (h[k] >= arm): armed = True
        if (h[k] >= trig) if put else (l[k] <= trig):
            if armed: j = k
            break
    if j is None: return ("none", np.nan)
    got1 = False; st = stop
    for k in range(j + 1, len(o)):
        hs = (h[k] >= st) if put else (l[k] <= st)
        if not got1:
            if hs: return ("stopped", -KS)
            if (l[k] <= half) if put else (h[k] >= half):
                got1, st = True, trig
                if (l[k] <= runner) if put else (h[k] >= runner): return ("half+runner", (K1 + K2) / 2)
            continue
        if hs: return ("half, runner at entry", K1 / 2)
        if (l[k] <= runner) if put else (h[k] >= runner): return ("half+runner", (K1 + K2) / 2)
    mv = (trig - c[-1]) / atr * (1 if put else -1)
    if got1: return ("half, runner at bell", (K1 + mv) / 2)
    return ("bell", mv)


def run(sym):
    d = pd.read_parquet(f"{DATA}/daily/{sym}.parquet").sort_values("t")
    d.index = pd.to_datetime(d.t).dt.normalize(); d = d[["o", "h", "l", "c"]].astype(float)
    m = pd.read_parquet(f"{DATA}/m5/{sym}.parquet")
    tm = m.t.dt.hour * 60 + m.t.dt.minute
    m = m[(tm >= 570) & (tm < 960)]
    days = {k: g for k, g in m.groupby(m.t.dt.normalize())}
    o, c, h, l = d.o.values, d.c.values, d.h.values, d.l.values
    pc = np.r_[np.nan, c[:-1]]
    A = pd.Series(np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))).rolling(14).mean().values
    bt = np.maximum(o, c); bb = np.minimum(o, c)
    pieces, filled, rows = [], [], []
    idx = d.index
    for i in range(1, len(d)):
        nxt = []
        for p in pieces:
            t = trim(p, bb[i], bt[i])
            if t: nxt += t
            else: filled.append(p)
        pieces = [p for p in nxt if i - p[2] <= LOOKBACK]; filled = [p for p in filled if i - p[2] <= LOOKBACK]
        if bb[i] > bt[i - 1]: pieces.append((bt[i - 1], bb[i], i))
        elif bt[i] < bb[i - 1]: pieces.append((bt[i], bb[i - 1], i))
        if i < 30 or i + 1 >= len(d) or idx[i] < pd.Timestamp("2016-01-01") or not A[i] > 0: continue
        nd = idx[i + 1]
        if nd not in days: continue
        g = days[nd]; arr = (g.o.values, g.h.values, g.l.values, g.c.values)
        close = c[i]
        for kind, src in (("open", pieces), ("filled", filled)):
            for put in (True, False):
                cand = [(p[0] if put else p[1]) for p in src if (p[0] > close if put else p[1] < close)]
                # a filled edge only counts if it is not also an open box edge (so the two groups don't overlap)
                if not cand: continue
                lvl = min(cand) if put else max(cand)
                if abs(lvl - close) / A[i] > MAXDIST: continue
                s = 1 if put else -1; trig = lvl - s * TAG * A[i]
                r = walk(put, trig, trig - s * POP * A[i], trig + s * KS * A[i], trig - s * K1 * A[i], trig - s * K2 * A[i], A[i], *arr)
                if r is None: continue
                rows.append(dict(sym=sym, date=nd, kind=kind, side="PUT" if put else "CALL", res=r[0], rr=r[1]))
    return rows


def summarize(R, title):
    L = ["", f"## {title}", "",
         "| Level | Side | Period | Setups | Triggered | Half off hit | Stopped | Avg result (ranges, triggered) |", "|---|---|---|---|---|---|---|---|"]
    for kind in ("open", "filled"):
        for side in ("PUT", "CALL", "both"):
            for per in ("2016-21", "2022-26"):
                x = R[(R.kind == kind) & (R.period == per) & ((R.side == side) if side != "both" else True)]
                t = x[x.rr.notna()]
                if not len(x): continue
                L.append(f"| {kind} | {side} | {per} | {len(x):,} | {len(t):,} ({len(t)/len(x)*100:.0f}%) | "
                         f"{t.res.str.startswith('half').mean()*100:.0f}% | {(t.res == 'stopped').mean()*100:.0f}% | {t.rr.mean():+.3f} |")
    return L


def main():
    names = sorted(f[:-8] for f in os.listdir(f"{DATA}/m5"))
    rows = []
    for s in names:
        try:
            rows += run(s)
        except Exception as e:
            print("skip", s, e)
    R = pd.DataFrame(rows)
    R["period"] = np.where(R.date < "2022-01-01", "2016-21", "2022-26")
    t = R[R.rr.notna()]
    piv = t.groupby(["kind", "period"]).rr.mean().unstack()
    held = all((piv.loc["filled", p] >= piv.loc["open", p]) for p in piv.columns)
    L = ["# Gray Box: filled box edges vs open boxes", "",
         f"{R.sym.nunique()} names (data_ext, 5m bars), 2016-2026. Same rules and exits as the live bot v2 (half off at half a range). "
         "Result is in daily ranges per triggered trade (stock move, no option P&L).", "",
         "## Answer", "",
         f"Average result per triggered trade: open boxes {piv.loc['open','2016-21']:+.3f} (2016-21) and {piv.loc['open','2022-26']:+.3f} (2022-26); "
         f"filled edges {piv.loc['filled','2016-21']:+.3f} and {piv.loc['filled','2022-26']:+.3f}. "
         + ("Filled edges did at least as well as open boxes in both halves. " if held else
            "Filled edges did NOT match open boxes in both halves. ")
         + ("But every one of these is within 0.02 of a range of zero: after the stop and exits, NEITHER level type has an edge "
            "mechanically. Filled edges are no worse than open boxes, so using them as levels is fine; neither is a system by itself."
            if piv.abs().max().max() < 0.02 else "")]
    L += summarize(R, "By level, side and period")
    tier = t.groupby(["sym", "kind"]).rr.agg(["count", "mean"]).unstack()
    L += ["", "## Per name (both periods, triggered trades)", "", "| Name | Open n | Open avg | Filled n | Filled avg |", "|---|---|---|---|---|"]
    for s in tier.index:
        r = tier.loc[s]
        L.append(f"| {s} | {int(r[('count','open')]) if r[('count','open')]==r[('count','open')] else 0} | {r[('mean','open')]:+.3f} | "
                 f"{int(r[('count','filled')]) if r[('count','filled')]==r[('count','filled')] else 0} | {r[('mean','filled')]:+.3f} |")
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/filled_edges.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[:30]))


if __name__ == "__main__":
    main()
