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
MAX_SYMBOLS = int(os.environ.get("MAX_SYMBOLS", 1000))


# ------------------------------------------------------------------ gap engine
class Gap:
    __slots__ = ("lo", "hi", "born", "kind", "open", "skipped", "filled_on")

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


def build_gaps(df, kind):
    """Walk candles in order; return per-bar snapshot of open gaps (list) BEFORE that bar."""
    gaps, snaps = [], []
    prev = None
    for i, r in enumerate(df.itertuples()):
        snaps.append([g for g in gaps if g.is_open])
        blo, bhi = min(r.o, r.c), max(r.o, r.c)
        if prev is not None:
            plo, phi = prev
            new = None
            if blo > phi:
                new = Gap(phi, blo, r.Index, kind)
            elif bhi < plo:
                new = Gap(bhi, plo, r.Index, kind)
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
    for i in range(1, len(d)):
        day = d.index[i]
        if day < start:
            continue
        r = d.iloc[i]; prev_c = d.c.iloc[i - 1]
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
        # only the first touch of the week counts
        wk_days = d[(wk_of == wk_of[i]) & (d.index < day)]
        touched_before = ((wk_days.l <= last_wc) & (wk_days.h >= last_wc)).any() if len(wk_days) else False
        touch = (r.l <= last_wc <= r.h) and not touched_before
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
            for g in boxes:
                for lo, hi in g.open:
                    if up and lo > prev_c and r.o >= lo:      # opened into or above a box overhead
                        into = True
                    if not up and hi < prev_c and r.o <= hi:  # opened into or below a box underneath
                        into = True
            direction = -1 if up else 1                        # fade the gap
            tgt = prev_c                                       # gap fill = back to prior close
            res = outcome(d, i, r.o, direction, tgt, r.o * (1.01 if up else 0.99))
            size = "1-2%" if abs(gp) < 2 else ("2-4%" if abs(gp) < 4 else "4%+")
            out.append(dict(symbol=sym, date=day, setup="B_gap_into_box" if into else "B_control_no_box",
                            side="puts" if up else "calls", gap_pct=gp, size=size, entry=r.o, target=tgt, **res))
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
    start_hist = (cap - pd.Timedelta(days=540)).date().isoformat()
    start = (cap - pd.Timedelta(days=int(MONTHS * 30.5))).tz_localize(None).normalize()
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
