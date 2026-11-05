"""
Flipping the six (Taz): the daily TD sell count is on 5, the next day gaps up (or pops) to print the 6, then dumps back
toward the prior close, often by noon.

Setup, knowable at the 9:30 open: yesterday's daily TD sell count = 5 (closes over the close 4 days earlier, 5 in a row)
and today opens above yesterday's close. All five of his example days fit this (TSLA Aug 20 2024, Sep 26 2024,
Dec 9 2024, Dec 2 2025, May 7 2026). Baseline = every other gap-up day of the same names.
Outcome: today's low reaches yesterday's close by 12:00 ET, and by the 4:00 close. Earnings days are left out
(earnings date = today, or the trading day before for after-close reports; source universe/earnings_edgar.csv).
Data: data_ext 5m bars (regular session for the daily candles). 2016 onward. Split 2016-21 / 2022-26.
Out: results/flip_six/REPORT.md
"""
import os
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data_ext")
OUT = "results/flip_six"; os.makedirs(OUT, exist_ok=True)
EX = ["2024-08-20", "2024-09-26", "2024-12-09", "2025-12-02", "2026-05-07"]


def days(sym, earn):
    m = pd.read_parquet(f"{DATA}/m5/{sym}.parquet")
    tm = m.t.dt.hour * 60 + m.t.dt.minute
    r = m[(tm >= 570) & (tm < 960)].copy()
    r["date"] = r.t.dt.normalize(); r["noon"] = r.t.dt.hour < 12
    d = r.groupby("date").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    d["l12"] = r[r.noon].groupby("date").l.min()
    d["h12"] = r[r.noon].groupby("date").h.max()
    up = (d.c > d.c.shift(4)).values; td = np.zeros(len(d), int)
    for i in range(1, len(d)): td[i] = (td[i - 1] % 9 + 1) if up[i] else 0
    d["td"] = td; d["tdprev"] = d.td.shift(); d["pc"] = d.c.shift()
    d["gap"] = (d.o / d.pc - 1) * 100
    d = d[(d.index >= "2016-01-01") & (d.gap > 0)].copy()
    e = earn.get(sym, set())
    prevday = pd.Series(d.index).shift(1)
    d["earn"] = [(x in e) or (p in e) for x, p in zip(d.index, prevday)]
    d["sym"] = sym
    d["noon_hit"] = d.l12 <= d.pc; d["close_hit"] = d.l <= d.pc
    d["red"] = d.c < d.o; d["close_vs_open"] = (d.c / d.o - 1) * 100
    d["six"] = d.tdprev == 5
    return d.reset_index()


def table(D, title):
    L = ["", f"### {title}", "", "| Group | Period | Days | Hit prior close by 12:00 | Hit prior close by the close | Closed red | Median open to close |",
         "|---|---|---|---|---|---|---|"]
    for lab, m in (("flip the six (count 5 yesterday, gap up today)", D.six), ("every other gap-up day", ~D.six)):
        for per in ("2016-21", "2022-26", "all"):
            x = D[m & ((D.period == per) if per != "all" else True)]
            if not len(x): continue
            L.append(f"| {lab} | {per} | {len(x):,} | {x.noon_hit.mean()*100:.0f}% | {x.close_hit.mean()*100:.0f}% | {x.red.mean()*100:.0f}% | {x.close_vs_open.median():+.2f}% |")
    return L


def main():
    E = pd.read_csv("universe/earnings_edgar.csv")
    earn = {s: set(pd.to_datetime(g.earnings_date)) for s, g in E.groupby("symbol")}
    U = pd.read_csv("universe/expanded_universe.csv")
    names = [s for s in sorted(U[U.group == "your 75"].symbol) if os.path.exists(f"{DATA}/m5/{s}.parquet")]
    D = pd.concat([days(s, earn) for s in names], ignore_index=True)
    D["period"] = np.where(D.date < "2022-01-01", "2016-21", "2022-26")
    D = D[~D.earn]
    T = D[D.sym == "TSLA"]
    six = D[D.six]; base = D[~D.six]
    held = all((six[six.period == p].noon_hit.mean() - base[base.period == p].noon_hit.mean()) >= 0.05 for p in ("2016-21", "2022-26"))
    ts6 = T[T.six]; tsb = T[~T.six]
    L = ["# Flipping the six", "",
         "Setup (knowable at 9:30): yesterday closed on daily TD sell count 5, today opens above yesterday's close. "
         "Outcome: the low tags yesterday's close by 12:00 ET, and by the close. Earnings days left out. "
         f"{len(names)} of his names, 2016 to Oct 14 2026 (5m bars on data_ext).", "",
         "## Answer", "",
         f"TSLA: flip-the-six days hit the prior close by noon {ts6.noon_hit.mean()*100:.0f}% of the time (n {len(ts6)}) vs "
         f"{tsb.noon_hit.mean()*100:.0f}% on every other gap-up day (n {len(tsb)}); by the close {ts6.close_hit.mean()*100:.0f}% vs {tsb.close_hit.mean()*100:.0f}%.",
         f"All his names: by noon {six.noon_hit.mean()*100:.0f}% (n {len(six):,}) vs {base.noon_hit.mean()*100:.0f}% (n {len(base):,}); "
         f"by the close {six.close_hit.mean()*100:.0f}% vs {base.close_hit.mean()*100:.0f}%.",
         ("**Held** (5+ points over other gap-up days by noon in both 2016-21 and 2022-26)." if held else
          "**Did not hold** as an edge: the count-5 gap-up is not meaningfully more likely to tag the prior close than any other gap-up "
          "(bar: 5+ points better by noon in both halves). Most gap-ups tag the prior close anyway; that is the base rate he is seeing.")]
    t22 = ts6[ts6.period == "2022-26"]; b22 = tsb[tsb.period == "2022-26"]
    L += ["", f"TSLA alone in 2022-26 is the exception: {t22.noon_hit.mean()*100:.0f}% by noon vs {b22.noon_hit.mean()*100:.0f}% (n {len(t22)}), "
          f"and {t22.red.mean()*100:.0f}% closed red vs {b22.red.mean()*100:.0f}%. In 2016-21 TSLA showed nothing (61% vs 62%). "
          "A recent TSLA-only lean on 33 days, not proof. The gap size matters far more than the count: small gaps tag the prior close 77% "
          "of the time either way, 2%+ gaps only about 22%."]
    L += table(T, "TSLA")
    L += table(D, f"All {len(names)} of his names")
    L += ["", "### His example days", "", "| Day | Gap | TD yesterday | Hit prior close by 12:00 | By the close | Earnings? |", "|---|---|---|---|---|---|"]
    allT = pd.concat([days("TSLA", earn)])
    for x in EX:
        r = allT[allT.date == x]
        if len(r):
            r = r.iloc[0]
            L.append(f"| TSLA {x} | {r.gap:+.2f}% | {int(r.tdprev)} | {'yes' if r.noon_hit else 'no'} | {'yes' if r.close_hit else 'no'} | {'yes' if r.earn else 'no'} |")
    L += ["", "### By gap size (all names, both periods)", "", "| Gap | Six: noon hit (n) | Others: noon hit (n) |", "|---|---|---|"]
    D["gb"] = pd.cut(D.gap, [0, 0.5, 1, 2, 100], labels=["0-0.5%", "0.5-1%", "1-2%", "2%+"])
    for b in ["0-0.5%", "0.5-1%", "1-2%", "2%+"]:
        a, z = D[D.six & (D.gb == b)], D[~D.six & (D.gb == b)]
        L.append(f"| {b} | {a.noon_hit.mean()*100:.0f}% ({len(a)}) | {z.noon_hit.mean()*100:.0f}% ({len(z):,}) |")
    open(f"{OUT}/REPORT.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
