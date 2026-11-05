"""
Gap-up run day vs dump day: what is knowable by 9:45 that separates a red close from a run?

Names: QQQ, AAPL, TSLA, NVDA, META, AMD, HOOD. 5m bars with extended hours (data_ext branch, DATA_DIR).
Gap up = 9:30 open is 0.3%+ over the prior regular-session close (the 15:55 bar's close).
Dump day = the 4:00 close is under the 9:30 open (red day). Run day = the close is over the open.
Also shown: close under the prior close (gap fully given back).

Knowable by 9:45 (first 15m candle = the 9:30, 9:35, 9:40 5m bars):
  gap size; first 15m close over/under the prior close, the daily 50 and the daily 10 SMA; first 15m colour;
  upper and lower wick share of the 15m range; whether the 9:30-9:45 low printed in the 9:30 bar;
  pre-market TD sell count (5m and 15m, extended hours, at 9:25); where the open sits vs the daily 10 SMA.
Daily MAs/ATR are as of the prior close (regular-session candles built from the 5m bars).
Rule picked on 2016-2021 only, judged on 2022-2026. Out: results/gap_up_945/REPORT.md, days.csv
"""
from __future__ import annotations
import os, itertools, math
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data_ext")
OUT = "results/gap_up_945"; os.makedirs(OUT, exist_ok=True)
NAMES = ["QQQ", "AAPL", "TSLA", "NVDA", "META", "AMD", "HOOD"]


def td_sell(c):
    up = (c > c.shift(4)).values; out = np.zeros(len(c), int)
    for i in range(1, len(c)):
        out[i] = (out[i - 1] % 9 + 1) if up[i] else 0
    return out


def build(sym):
    m = pd.read_parquet(f"{DATA}/m5/{sym}.parquet").sort_values("t").reset_index(drop=True)
    for k in "ohlcv": m[k] = m[k].astype(float)
    m["date"] = m.t.dt.normalize(); m["tm"] = m.t.dt.hour * 60 + m.t.dt.minute
    m["td5"] = td_sell(m.c)
    q = m.groupby(m.t.dt.floor("15min")).agg(c=("c", "last")); q["td15"] = td_sell(q.c)
    reg = m[(m.tm >= 570) & (m.tm < 960)]
    d = reg.groupby("date").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), first=("tm", "min"))
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    d["s10"] = d.c.rolling(10).mean(); d["s50"] = d.c.rolling(50).mean()
    P = d.shift(1)                                       # prior-day values
    rows = []
    g = dict(tuple(m[(m.tm >= 240) & (m.tm < 960)].groupby("date")))
    for day in d.index[60:]:
        if d.loc[day, "first"] != 570 or day not in g:
            continue
        pc, A, s10, s50 = P.loc[day, "c"], P.loc[day, "atr"], P.loc[day, "s10"], P.loc[day, "s50"]
        op = d.loc[day, "o"]; gap = (op / pc - 1) * 100
        if gap < 0.3:
            continue
        x = g[day]
        f15 = x[(x.tm >= 570) & (x.tm < 585)]
        pre = x[x.tm < 570]
        if len(f15) < 3:
            continue
        hi, lo, cl = f15.h.max(), f15.l.min(), f15.c.iloc[-1]; rng = max(hi - lo, 1e-9)
        q15 = q[q.index < day + pd.Timedelta(minutes=570)]
        rest = x[(x.tm >= 585) & (x.tm < 960)]
        race = np.nan
        for _, b in rest.iterrows():
            dn, up = b.l <= cl - 0.5 * A, b.h >= cl + 0.5 * A
            if dn or up:
                race = 1.0 if (dn and not up) else 0.0
                break
        rows.append(dict(
            sym=sym, date=day, gap=gap, gap_atr=(op - pc) / A,
            red=d.loc[day, "c"] < op, under_pc=d.loc[day, "c"] < pc,
            close_ret=(d.loc[day, "c"] / op - 1) * 100,
            down_after945=d.loc[day, "c"] < cl, race945=race,
            race_win=race == 1.0, ret945=(d.loc[day, "c"] / cl - 1) * 100,
            f15_over_pc=cl > pc, f15_over_s50=cl > s50, f15_over_s10=cl > s10, f15_green=cl > op,
            f15_upper=(hi - max(op, cl)) / rng, f15_lower=(min(op, cl) - lo) / rng, f15_ret=(cl / op - 1) * 100,
            low_at_930=bool(f15.l.iloc[0] <= lo), high_at_930=bool(f15.h.iloc[0] >= hi),
            pm_td5=int(pre.td5.iloc[-1]) if len(pre) else -1,
            pm_td15=int(q15.td15.iloc[-1]) if len(q15) else -1,
            open_vs_s10_atr=(op - s10) / A, open_over_s10=op > s10, open_over_s50=op > s50,
            hod_first30=None))
    return pd.DataFrame(rows)


def row4(x):
    if not len(x):
        return "- | - | - | -"
    return (f"{x.red.mean()*100:.0f}% ({len(x)}) | {x.down_after945.mean()*100:.0f}% | {x.race_win.mean()*100:.0f}% | "
            f"{x.ret945.median():+.2f}%")


def rate(x, col="red"):
    return f"{x[col].mean()*100:.0f}% ({len(x)})" if len(x) else "-"


def main():
    D = pd.concat([build(s) for s in NAMES], ignore_index=True)
    D["period"] = np.where(D.date < "2022-01-01", "2016-21", "2022-26")
    D.to_csv(f"{OUT}/days.csv", index=False)
    fit, jud = D[D.period == "2016-21"], D[D.period == "2022-26"]
    C = {
        "Gap 0.3-1%": (D.gap < 1), "Gap 1-2%": (D.gap >= 1) & (D.gap < 2), "Gap 2%+": D.gap >= 2,
        "Gap 1 ATR+": D.gap_atr >= 1,
        "First 15m closed back UNDER the prior close": ~D.f15_over_pc,
        "First 15m closed OVER the prior close": D.f15_over_pc,
        "First 15m closed under the daily 50": ~D.f15_over_s50,
        "First 15m closed under the daily 10 SMA": ~D.f15_over_s10,
        "First 15m candle red": ~D.f15_green, "First 15m candle green": D.f15_green,
        "First 15m upper wick 40%+ of range": D.f15_upper >= 0.4,
        "First 15m lower wick 40%+ of range": D.f15_lower >= 0.4,
        "Low of 9:30-9:45 printed in the 9:30 bar": D.low_at_930,
        "High of 9:30-9:45 printed in the 9:30 bar": D.high_at_930,
        "Pre-market 5m TD sell count 7-9": D.pm_td5 >= 7, "Pre-market 15m TD sell count 7-9": D.pm_td15 >= 7,
        "Open under the daily 10 SMA": ~D.open_over_s10, "Open over the daily 10 SMA by 2+ ATR": D.open_vs_s10_atr >= 2,
        "Open under the daily 50": ~D.open_over_s50,
    }
    H = ("| {} | 2016-21: closed red (n) | under 9:45 price | 0.5 ATR down first | median 9:45 to close "
         "| 2022-26: closed red (n) | under 9:45 price | 0.5 ATR down first | median 9:45 to close |")
    SEP = "|---|---|---|---|---|---|---|---|---|"
    rr = lambda m: f"{row4(D[m & (D.period == '2016-21')])} | {row4(D[m & (D.period == '2022-26')])}"
    allm = pd.Series(True, index=D.index)

    # ---------------- simple rules: single clues and pairs, picked on 2016-21 (n >= 60)
    keys = list(C); cand = []
    for combo in [(k,) for k in keys] + list(itertools.combinations(keys, 2)):
        m = C[combo[0]] if len(combo) == 1 else C[combo[0]] & C[combo[1]]
        f = D[m & (D.period == "2016-21")]; j = D[m & (D.period == "2022-26")]
        if len(f) < 60:
            continue
        cand.append(dict(rule=" + ".join(combo), fn=len(f), fr=f.red.mean(), jn=len(j), jr=j.red.mean() if len(j) else np.nan,
                         f945=f.down_after945.mean(), j945=j.down_after945.mean() if len(j) else np.nan,
                         frace=f.race_win.mean(), jrace=j.race_win.mean() if len(j) else np.nan))
    K = pd.DataFrame(cand); K.to_csv(f"{OUT}/rules.csv", index=False)
    fb, jb = fit.red.mean(), jud.red.mean()
    dump = K.sort_values("fr", ascending=False).head(8)
    run = K.sort_values("fr").head(8)
    best_d = dump.iloc[0]; simple = "First 15m closed back UNDER the prior close"
    sd = C[simple]; sr = C["First 15m candle green"] & C["Low of 9:30-9:45 printed in the 9:30 bar"]

    L = ["# Gap-up run day vs dump day, decided by 9:45", "",
         f"Names: {', '.join(NAMES)}. 5m bars with extended hours. Every gap up of 0.3%+ over the prior close: "
         f"{len(D):,} days ({len(fit):,} in 2016-2021 = fit, {len(jud):,} in 2022-2026 = judged; HOOD from Aug 2021).",
         "**Dump day** = closes red (4:00 close under the 9:30 open). **Run day** = closes green.",
         "Because the first 15 minutes are already inside the day's candle, every clue is also measured **from the 9:45 price**, "
         "which is what a trade placed at 9:45 actually gets: did it close under the 9:45 price, and did it fall 0.5 ATR before it rose 0.5 ATR "
         "(rest of the session).", "",
         "## The answer in plain English", "",
         f"**The 9:45 rule:** on a gap up of 0.3%+, if the first 15-minute candle closes back under yesterday's close, it is a dump day: "
         f"it closed red {D[sd & (D.period=='2016-21')].red.mean()*100:.0f}% of the time in 2016-21 and "
         f"{D[sd & (D.period=='2022-26')].red.mean()*100:.0f}% in 2022-26 (baseline {fb*100:.0f}% / {jb*100:.0f}%). "
         f"If instead the first 15m candle is green and its low was the 9:30 print, it is a run day: closed green "
         f"{(1-D[sr & (D.period=='2016-21')].red.mean())*100:.0f}% / {(1-D[sr & (D.period=='2022-26')].red.mean())*100:.0f}%.", "",
         f"**The catch, said straight:** most of that is the first 15 minutes already being in the candle. Measured from the 9:45 price, "
         f"the dump-day rule closed lower than 9:45 only {D[sd & (D.period=='2016-21')].down_after945.mean()*100:.0f}% / "
         f"{D[sd & (D.period=='2022-26')].down_after945.mean()*100:.0f}% of the time and fell 0.5 ATR before rising 0.5 ATR "
         f"{D[sd & (D.period=='2016-21')].race_win.mean()*100:.0f}% / {D[sd & (D.period=='2022-26')].race_win.mean()*100:.0f}% "
         f"(all gap-ups: {fit.race_win.mean()*100:.0f}% / {jud.race_win.mean()*100:.0f}%). So the 9:45 read tells you what kind of day it is, "
         "but a put bought at the 9:45 price has no real edge to the close on these 7 names. The edge, if any, is in the entry after 9:45 "
         "(the pop back into the prior close or the 9:30 high), which this test does not cover.", "",
         f"The best pair found on 2016-21 was **{best_d.rule}**: closed red {best_d.fr*100:.0f}% (n {best_d.fn}) then "
         f"{best_d.jr*100:.0f}% (n {best_d.jn}) in 2022-26; from 9:45 it went lower {best_d.f945*100:.0f}% then {best_d.j945*100:.0f}%. "
         "Small sample; the judged half did not keep the 9:45 edge.", "",
         "## Baseline", "", H.format("Period"), SEP,
         f"| All gap-ups | {rr(allm)} |", "",
         "| Name | Gap-up days | 2016-21 closed red | 2022-26 closed red | Rule days (2016-26) | Rule: closed red | Rule: under 9:45 price |", "|---|---|---|---|---|---|---|"]
    for s in NAMES:
        x = D[D.sym == s]; y = D[(D.sym == s) & sd]
        L.append(f"| {s} | {len(x)} | {rate(x[x.period=='2016-21'])} | {rate(x[x.period=='2022-26'])} | {len(y)} | "
                 f"{y.red.mean()*100:.0f}% | {y.down_after945.mean()*100:.0f}% |")
    L += ["", "## Each 9:45 clue on its own", "", H.format("Clue (known by 9:45)"), SEP]
    for k, m in C.items():
        L.append(f"| {k} | {rr(m)} |")
    for title, tab, word in (("dump-day", dump, "closed red"), ("run-day", run, "closed red (low = run)")):
        L += ["", f"## Best {title} rules (picked on 2016-21 by how often the day {word}, 60+ days)", "",
              "| Rule | 2016-21 closed red (n) | 2016-21 under 9:45 price | 2022-26 closed red (n) | 2022-26 under 9:45 price |", "|---|---|---|---|---|"]
        for _, r in tab.iterrows():
            L.append(f"| {r.rule} | {r.fr*100:.0f}% ({r.fn}) | {r.f945*100:.0f}% | {r.jr*100:.0f}% ({r.jn}) | {r.j945*100:.0f}% |")
    L += ["", "## Notes", "", "- Daily 10 SMA, 50 and ATR are as of the prior close. Pre-market TD count = TD sell setup count on the "
          "5m and 15m extended-hours bars at 9:25.", "- 0.5 ATR race: from the 9:45 price, using 5m highs and lows to 4:00; a bar that hits both "
          "counts as up first; neither by the close counts as not down first."]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
