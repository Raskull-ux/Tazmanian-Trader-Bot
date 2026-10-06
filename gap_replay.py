"""
Gap replay — measure BEFORE building. How often would the gap alerts fire, and what happened next?
================================================================================================
Taz's gap rules (confirmed):
  - Gaps are BODY to BODY. Wicks never fill.
  - Every gap is tracked separately. The open part of a gap shrinks only where a later
    candle BODY covers it; the gap is FILLED when bodies have covered all of it.
  - SKIPPED gap: price later gapped clean across it without a body filling it (top priority).
  - Daily boxes from daily candles; weekly boxes from completed weeks only.

Setups measured over the last 6 months (daily bars, split-adjusted):
  A. WEEKLY RETEST — the week opens gapped away from last week's close, then a later day
     touches last week's close. Gap down -> puts (target: open boxes below). Gap up -> calls.
     Control: weeks that opened WITHOUT a gap and touched last week's close.
  B. DAILY GAP INTO A BOX — a day opens gapped up into or above an open (unfilled) box,
     i.e. into resistance -> fade back down (puts). Mirror: gap down into/below a box -> calls.
     Sized: 1-2%, 2-4%, 4%+. Control: same-size gaps with no box involved.

For each event: how many per day (alert load), and what the stock did next, in the trade's
direction: same-day close, 1/3/5-day close, and whether it reached the first target
(nearest open box edge in that direction) before reversing past the invalidation level.
Stock moves only, no option pricing. Free (Alpaca daily bars).

Env: ALPACA keys. Opt: MONTHS (6), MAX_SYMBOLS (1000)
Out: results/gap_replay/{report.md, events.csv}
"""
from __future__ import annotations
import os, math
import numpy as np, pandas as pd
import setup_backtest as sb

OUT = "results/gap_replay"
MONTHS = int(os.environ.get("MONTHS", 6))
PERIODS = [("2022-01 to 2026-03 (incl. the 2022 bear market)", "2022-01-01", "2026-03-31"),
           ("2026-04 to now (the original 6 months)", "2026-04-01", "2099-01-01")]
MAX_SYMBOLS = int(os.environ.get("MAX_SYMBOLS", 1000))


# ------------------------------------------------------------------ gap engine
class Gap:
    __slots__ = ("lo", "hi", "born", "kind", "open", "skipped", "filled_on", "born_i")

    def __init__(self, lo, hi, born, kind):
        self.lo, self.hi, self.born, self.kind = lo, hi, born, kind
        self.open = [(lo, hi)]          # uncovered pieces
        self.skipped = False
        self.filled_on = None

    def cover(self, a, b):
        """Remove the part covered by a body [a, b]."""
        out = []
        for lo, hi in self.open:
            if b <= lo or a >= hi:
                out.append((lo, hi)); continue
            if a > lo: out.append((lo, a))
            if b < hi: out.append((b, hi))
        self.open = [(lo, hi) for lo, hi in out if hi - lo > 1e-6]

    @property
    def is_open(self):
        return bool(self.open)

    def edges(self):
        return [x for p in self.open for x in p]


class Snap:
    __slots__ = ("open", "skipped")

    def __init__(self, open_, skipped):
        self.open, self.skipped = open_, skipped

    def edges(self):
        return [x for p in self.open for x in p]


def build_gaps(df, kind):
    """Walk candles in order; return per-bar snapshot of open gaps (list) BEFORE that bar."""
    gaps, snaps = [], []
    prev = None
    for i, r in enumerate(df.itertuples()):
        if kind == "daily":
            gaps = [g for g in gaps if g.is_open and (i - g.born_i) <= 260]
        # SNAPSHOT copies: the state of each open gap as of this bar. (Storing the live
        # objects would leak later fills into earlier bars = look-ahead.)
        snaps.append([Snap(list(g.open), g.skipped) for g in gaps if g.is_open])
        blo, bhi = min(r.o, r.c), max(r.o, r.c)
        if prev is not None:
            plo, phi = prev
            new = None
            if blo > phi:
                new = Gap(phi, blo, r.Index, kind); new.born_i = i
            elif bhi < plo:
                new = Gap(bhi, plo, r.Index, kind); new.born_i = i
            # bodies that jump clean across an open gap = skipped
            jlo, jhi = (phi, blo) if blo > phi else ((bhi, plo) if bhi < plo else (None, None))
            for g in gaps:
                if g.is_open and jlo is not None:
                    if any(jlo <= lo and hi <= jhi for lo, hi in g.open):
                        g.skipped = True
            for g in gaps:
                if g.is_open:
                    g.cover(blo, bhi)
                    if not g.is_open:
                        g.filled_on = r.Index
            if new is not None:
                gaps.append(new)
        prev = (blo, bhi)
    return snaps


# ------------------------------------------------------------------ events
def first_target(price, boxes, direction):
    """Nearest open box edge in the trade direction (puts: below price, calls: above)."""
    edges = [e for g in boxes for e in g.edges()]
    if direction < 0:
        cand = [e for e in edges if e < price * 0.999]
        return max(cand) if cand else np.nan
    cand = [e for e in edges if e > price * 1.001]
    return min(cand) if cand else np.nan


def outcome(d, i, entry, direction, target, invalid):
    """Moves in trade direction (%), and target-before-invalidation within 5 days."""
    r = {}
    for n, nm in ((0, "same_day"), (1, "d1"), (3, "d3"), (5, "d5")):
        j = i + n
        r[nm] = direction * (d.c.iloc[j] / entry - 1) * 100 if j < len(d) else np.nan
    hit = np.nan
    if target == target:
        hit = 0
        for j in range(i, min(i + 6, len(d))):
            hi_, lo_ = d.h.iloc[j], d.l.iloc[j]
            reach = lo_ <= target if direction < 0 else hi_ >= target
            fail = (d.c.iloc[j] > invalid) if direction < 0 else (d.c.iloc[j] < invalid)
            if reach:
                hit = 1; break
            if fail and j > i:
                break
    r["target_first"] = hit
    return r


def weekly_frame(d):
    w = d.copy()
    w["wk"] = w.index.to_period("W-FRI")
    g = w.groupby("wk")
    W = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(),
                      "start": g.apply(lambda x: x.index[0]), "end": g.apply(lambda x: x.index[-1])})
    return W


def events_for(sym, d, start):
    d = d.sort_index()
    if len(d) < 60:
        return []
    out = []
    dsnaps = build_gaps(d, "daily")
    W = weekly_frame(d)
    wsnaps = build_gaps(W.set_index("end")[["o", "h", "l", "c"]], "weekly")
    wk_of = d.index.to_period("W-FRI")
    wpos = {wk: k for k, wk in enumerate(W.index)}
    cur_wk, touched_before = None, False
    for i in range(1, len(d)):
        day = d.index[i]
        r = d.iloc[i]; prev_c = d.c.iloc[i - 1]
        if day < start:
            if wk_of[i] != cur_wk:
                cur_wk, touched_before = wk_of[i], False
            continue
        k = wpos[wk_of[i]]
        if k == 0:
            continue
        wboxes = wsnaps[k]                       # weekly gaps known before this week
        dboxes = dsnaps[i]                       # daily gaps known before this day
        boxes = wboxes + dboxes
        # ---------- A: weekly retest
        last_wc = W.c.iloc[k - 1]
        wk_open = W.o.iloc[k]
        first_day = d.index[i] == W.start.iloc[k]
        # only the first touch of the week counts (tracked incrementally)
        if wk_of[i] != cur_wk:
            cur_wk, touched_before = wk_of[i], False
        touch = (r.l <= last_wc <= r.h) and not touched_before
        if r.l <= last_wc <= r.h:
            touched_before = True
        if touch:
            gapped = abs(wk_open / last_wc - 1) >= 0.0025
            direction = -1 if wk_open < last_wc else 1     # gap down -> puts, gap up -> calls
            tgt = first_target(last_wc, boxes, direction)
            res = outcome(d, i, last_wc, direction, tgt, last_wc * (1 - 0.01 * direction))
            out.append(dict(symbol=sym, date=day, setup="A_weekly_retest" if gapped else "A_control_no_gap",
                            side="puts" if direction < 0 else "calls",
                            gap_pct=(wk_open / last_wc - 1) * 100, entry=last_wc, target=tgt,
                            skipped_target=any(g.skipped for g in boxes if any(abs(e - tgt) < 1e-6 for e in g.edges())) if tgt == tgt else False,
                            **res))
        # ---------- B: daily gap into / above a box
        gp = (r.o / prev_c - 1) * 100
        if abs(gp) >= 1.0:
            up = gp > 0
            into = False
            ref = None      # edge the close must stay beyond for the gap to "hold"
            for g in boxes:
                for lo, hi in g.open:
                    if up and lo > prev_c and r.o >= lo:      # opened into or above a box overhead
                        into = True
                        e = hi if r.o >= hi else lo
                        ref = e if ref is None else max(ref, e)
                    if not up and hi < prev_c and r.o <= hi:  # opened into or below a box underneath
                        into = True
                        e = lo if r.o <= lo else hi
                        ref = e if ref is None else min(ref, e)
            direction = -1 if up else 1                        # fade the gap
            tgt = prev_c                                       # gap fill = back to prior close
            res = outcome(d, i, r.o, direction, tgt, r.o * (1.01 if up else 0.99))
            size = "1-2%" if abs(gp) < 2 else ("2-4%" if abs(gp) < 4 else "4%+")
            out.append(dict(symbol=sym, date=day, setup="B_gap_into_box" if into else "B_control_no_box",
                            side="puts" if up else "calls", gap_pct=gp, size=size, entry=r.o, target=tgt, **res))
            # continuation from the open (the flip side of the fade)
            if into:
                cres = {k: (-v if isinstance(v, float) and k != "target_first" else v) for k, v in res.items()}
                cres["target_first"] = np.nan
                out.append(dict(symbol=sym, date=day, setup="C_continuation_from_open",
                                side="calls" if up else "puts", gap_pct=gp, size=size, entry=r.o, **cres))
                # held vs failed, decided at the close; trade entered at that close
                failed = (r.c < ref) if up else (r.c > ref)
                direction2 = (-1 if up else 1) if failed else (1 if up else -1)
                res2 = outcome(d, i, r.c, direction2, np.nan, r.c)
                res2["same_day"] = np.nan
                out.append(dict(symbol=sym, date=day, setup="D_failed_gap" if failed else "D_held_gap",
                                side=("puts" if up else "calls") if failed else ("calls" if up else "puts"),
                                gap_pct=gp, size=size, entry=r.c, **res2))
    return out


# ------------------------------------------------------------------ report
def cell(x, col):
    x = x[[col, "date"]].dropna()
    if len(x) < 3:
        return "—"
    dm = x.groupby("date")[col].mean()
    t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")
    return f"{x[col].mean():+.2f}% ({(x[col] > 0).mean():.0%} your way, t {t:.1f})"


def rows(E, label_col, labels):
    L = ["| Group | Events | Per trading day | Same-day close | Next day | 3 days | 5 days | Hit first target before invalidation |",
         "|---|---|---|---|---|---|---|---|"]
    ndays = E.date.nunique() or 1
    for lab, m in labels:
        x = E[m]
        if len(x) == 0:
            continue
        tf = x.target_first.dropna()
        L.append(f"| {lab} | {len(x)} | {len(x)/ndays:.1f} | {cell(x,'same_day')} | {cell(x,'d1')} | "
                 f"{cell(x,'d3')} | {cell(x,'d5')} | {tf.mean():.0%} (n {len(tf)}) |")
    return L


def tstat_day(x, col):
    x = x[[col, "date"]].dropna()
    if len(x) < 3:
        return np.nan, np.nan, 0
    dm = x.groupby("date")[col].mean()
    t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else np.nan
    return x[col].mean(), t, len(x)


def period_block(E, title):
    L = [f"\n# PERIOD: {title}\n"]
    for scope, X in (("Full universe", E), ("Your core tickers", E[E.core])):
        C = X[X.setup == "C_continuation_from_open"]; D = X[X.setup.str.startswith("D_")]
        L += [f"\n## {scope}\n", "### C. Gap into/over an open box — ride the gap (entered at the open)\n"]
        L += rows(C, "setup", [("Gap UP over box -> calls", C.side == "calls"),
                               ("Gap DOWN under box -> puts", C.side == "puts"),
                               ("Gap UP 4%+ -> calls", (C.side == "calls") & (C["size"] == "4%+")),
                               ("Gap UP 2-4% -> calls", (C.side == "calls") & (C["size"] == "2-4%")),
                               ("Gap UP 1-2% -> calls", (C.side == "calls") & (C["size"] == "1-2%"))])
        L += ["\n### D. Held vs failed at the close (entered at that day's close)\n"]
        L += rows(D, "setup", [("Gap UP held above box -> calls", (D.setup == "D_held_gap") & (D.side == "calls")),
                               ("Gap UP FAILED back into/below box -> puts (INTC trap)", (D.setup == "D_failed_gap") & (D.side == "puts")),
                               ("Gap DOWN held below box -> puts", (D.setup == "D_held_gap") & (D.side == "puts")),
                               ("Gap DOWN FAILED back into/above box -> calls", (D.setup == "D_failed_gap") & (D.side == "calls"))])
        B = X[X.setup == "B_control_no_box"]
        L += ["\n### Control: same-size gaps with no box, ride the gap (= minus the fade numbers)\n"]
        L += rows(B.assign(**{k: -B[k] for k in ["same_day", "d1", "d3", "d5"]}), "setup",
                  [("Gap UP, no box -> calls", B.side == "puts"), ("Gap DOWN, no box -> puts", B.side == "calls")])
    return L


def report(E, nsym, core_n):
    os.makedirs(OUT, exist_ok=True)
    E.to_csv(f"{OUT}/events.csv", index=False)
    days = E.date.nunique()
    L = ["# Gap replay — how often would it alert, and what happened next?",
         f"\n{nsym} names ({core_n} of them your core tickers), {days} trading days "
         f"({E.date.min():%b %d %Y} to {E.date.max():%b %d %Y}). Stock moves in the trade's direction; "
         "t clustered by day. 'Your way' = moved in the trade's direction.\n"]
    for scope, X in (("YOUR CORE TICKERS", E[E.core]), ("FULL UNIVERSE", E)):
        L.append(f"\n## {scope}\n")
        A = X[X.setup.str.startswith("A")]
        L.append("### A. Weekly retest (touch of last week's close)\n")
        L += rows(A, "setup", [("Gapped week, puts", (A.setup == "A_weekly_retest") & (A.side == "puts")),
                               ("Gapped week, calls", (A.setup == "A_weekly_retest") & (A.side == "calls")),
                               ("Gapped week, target is a SKIPPED gap", (A.setup == "A_weekly_retest") & A.skipped_target.astype(bool)),
                               ("Control: no gap at the week's open", A.setup == "A_control_no_gap")])
        B = X[X.setup.str.startswith("B")]
        L.append("\n### B. Daily gap into or beyond an open box (fade it)\n")
        lab = []
        for s in ("1-2%", "2-4%", "4%+"):
            lab.append((f"Gap {s} into box", (B.setup == "B_gap_into_box") & (B["size"] == s)))
        for s in ("1-2%", "2-4%", "4%+"):
            lab.append((f"Control: gap {s}, no box", (B.setup == "B_control_no_box") & (B["size"] == s)))
        lab += [("Into box, gap UP (puts)", (B.setup == "B_gap_into_box") & (B.side == "puts")),
                ("Into box, gap DOWN (calls)", (B.setup == "B_gap_into_box") & (B.side == "calls"))]
        L += rows(B, "setup", lab)
        a = X[X.setup == "A_weekly_retest"]; b = X[X.setup == "B_gap_into_box"]
        per = pd.concat([a, b]).groupby("date").size().reindex(sorted(X.date.unique()), fill_value=0)
        L += [f"\n**Alert load ({scope.lower()}):** A + B together: average {per.mean():.1f} per day, "
              f"median {per.median():.0f}, busiest day {per.max()}, quiet days (0 alerts): {(per == 0).mean():.0%}."]
    checks = []
    for title, a, b in PERIODS:
        X = E[(E.date >= pd.Timestamp(a)) & (E.date <= pd.Timestamp(b))]
        if X.empty:
            continue
        L += period_block(X, title)
        c = X[(X.setup == "C_continuation_from_open") & (X.side == "calls")]
        f = X[(X.setup == "D_failed_gap") & (X.side == "puts")]
        cm, ct, cn = tstat_day(c, "d3"); fm, ft, fn = tstat_day(f, "d3")
        checks.append((title, cm, ct, cn, fm, ft, fn))
    L += ["\n# PASS CHECKS (set before running, 3-day move, full universe)\n",
          "| Period | Gap-up-over-box calls (pass: t >= 3) | Failed gap-up puts, INTC trap (pass: t >= 2) |", "|---|---|---|"]
    for title, cm, ct, cn, fm, ft, fn in checks:
        L.append(f"| {title} | {cm:+.2f}%, t {ct:.1f}, n {cn} -> {'PASS' if ct >= 3 and cm > 0 else 'FAIL'} | "
                 f"{fm:+.2f}%, t {ft:.1f}, n {fn} -> {'PASS' if ft >= 2 and fm > 0 else 'FAIL'} |")
    L += ["\n## How to read\n",
          "- Per trading day = how many alerts that rule would have sent.",
          "- A setup is worth alerting if it beats its control and moves your way clearly (t >= 2 suggestive, >= 3 strong).",
          "- 'Hit first target' for A = reached the nearest open box edge before closing back 1% past the trigger; "
          "for B = filled the gap back to the prior close before closing 1% beyond the open."]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    u = pd.read_csv("universe/universe.csv")
    u = u[u.group != "gauge"].sort_values("avg_dollar_vol", ascending=False).head(MAX_SYMBOLS)
    core = set(u[u.group == "core"].symbol)
    syms = u.symbol.tolist()
    cap = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)
    start_hist = "2020-06-01"
    start = pd.Timestamp(PERIODS[0][1])
    E = []
    for i in range(0, len(syms), 100):
        ch = syms[i:i + 100]
        try:
            d = sb.fetch(ch, "1Day", start_hist, cap.isoformat())
        except Exception as ex:
            print("fetch", ch[:2], ex); continue
        for s in ch:
            x = d[d.symbol == s]
            if len(x) < 60:
                continue
            x = x.assign(day=x.t.dt.tz_localize(None).dt.normalize()).set_index("day")[["o", "h", "l", "c"]]
            try:
                E += events_for(s, x, start)
            except Exception as ex:
                print(f"  {s}: {ex}")
        print(f"  {min(i + 100, len(syms))}/{len(syms)} symbols, {len(E)} events", flush=True)
    E = pd.DataFrame(E)
    E["core"] = E.symbol.isin(core)
    report(E, len(syms), len(core))


if __name__ == "__main__":
    main()
