"""
Confirmation test — do Taz's DAILY confirmations make the failed gap-up (INTC trap) work?
=====================================================================================
Base event (same engine as gap_replay.py, look-ahead fixed): a day gaps UP into or over an
open body-gap box and CLOSES back into/below it. Trade: puts, entered at that day's close.
On its own this lost money since 2022 (-0.71% over 3 days, t -4.0). Question: does it work
when Taz's daily confirmations line up, the way they did on INTC?

Confirmations, measured with data up to and including the event day's close only:
  1. rsi_div      price high in the last 5 days >= the high of days 6-25 back (within 1%),
                  but RSI(14) peak in the last 5 days is at least 3 points lower
  2. rsi_under_ma RSI(14) below its 14-day average
  3. macd_roll    MACD(12,26,9) line below its signal line (histogram negative)
  4. macd_div     same as rsi_div but with the MACD line's peaks
  5. under_10sma  close below the 10-day SMA
  6. lower_highs  the last two confirmed swing highs are descending
                  (swing high = high above the 2 days on each side, confirmed 2 days later)
  7. td_9         Taz's TD count (consecutive closes above the close 4 days earlier) reached 8+
                  within the last 3 days (his TradingView script, exact logic)
  score = how many of the 7 are true

PASS (set before running): puts with score >= 4 positive over 3 days with t >= 2 in BOTH
periods, and better than all failed gap-ups.

Free (Alpaca daily bars). Out: results/confirm_test/{report.md, events.csv.gz}
"""
from __future__ import annotations
import os, math
import numpy as np, pandas as pd
import setup_backtest as sb
import gap_replay as gr

OUT = "results/confirm_test"
PERIODS = gr.PERIODS
CONF = ["rsi_div", "rsi_under_ma", "macd_roll", "macd_div", "under_10sma", "lower_highs", "td_9"]


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(100)


def indicators(d):
    x = d.copy()
    x["rsi"] = rsi(x.c); x["rsi_ma"] = x.rsi.rolling(14).mean()
    e12, e26 = x.c.ewm(span=12, adjust=False).mean(), x.c.ewm(span=26, adjust=False).mean()
    x["macd"] = e12 - e26; x["sig"] = x.macd.ewm(span=9, adjust=False).mean()
    x["sma10"] = x.c.rolling(10).mean()
    # Taz's TD count: consecutive closes above the close 4 bars earlier
    up = (x.c > x.c.shift(4)).astype(int)
    x["td"] = up.groupby((up == 0).cumsum()).cumsum()
    h = x.h.values
    sw = np.zeros(len(x), bool)
    for j in range(2, len(x) - 2):
        sw[j] = h[j] > max(h[j - 2], h[j - 1], h[j + 1], h[j + 2])
    x["swing"] = sw
    return x


def features(x, i):
    if i < 30:
        return None
    hi_recent, hi_prior = x.h.iloc[i - 4:i + 1].max(), x.h.iloc[i - 25:i - 5].max()
    price_ok = hi_recent >= hi_prior * 0.99
    f = {}
    f["rsi_div"] = bool(price_ok and x.rsi.iloc[i - 4:i + 1].max() <= x.rsi.iloc[i - 25:i - 5].max() - 3)
    f["rsi_under_ma"] = bool(x.rsi.iloc[i] < x.rsi_ma.iloc[i])
    f["macd_roll"] = bool(x.macd.iloc[i] < x.sig.iloc[i])
    f["macd_div"] = bool(price_ok and x.macd.iloc[i - 4:i + 1].max() < x.macd.iloc[i - 25:i - 5].max())
    f["under_10sma"] = bool(x.c.iloc[i] < x.sma10.iloc[i])
    conf_sw = [j for j in range(max(2, i - 60), i - 1) if x.swing.iloc[j]]   # confirmed by day i
    f["lower_highs"] = bool(len(conf_sw) >= 2 and x.h.iloc[conf_sw[-1]] < x.h.iloc[conf_sw[-2]])
    f["td_9"] = bool(x.td.iloc[i - 2:i + 1].max() >= 8)
    f["score"] = sum(f[k] for k in CONF)
    return f


def events_for(sym, d, start):
    d = d.sort_index()
    if len(d) < 80:
        return []
    x = indicators(d)
    snaps = gr.build_gaps(d, "daily")
    W = gr.weekly_frame(d)
    wsnaps = gr.build_gaps(W.set_index("end")[["o", "h", "l", "c"]], "weekly")
    wk_of = d.index.to_period("W-FRI"); wpos = {wk: k for k, wk in enumerate(W.index)}
    out = []
    for i in range(1, len(d)):
        day = d.index[i]
        if day < start:
            continue
        r = d.iloc[i]; prev_c = d.c.iloc[i - 1]
        gp = (r.o / prev_c - 1) * 100
        if gp < 1.0:
            continue
        k = wpos[wk_of[i]]
        boxes = (wsnaps[k] if k > 0 else []) + snaps[i]
        ref = None
        for g in boxes:
            for lo, hi in g.open:
                if lo > prev_c and r.o >= lo:
                    e = hi if r.o >= hi else lo
                    ref = e if ref is None else max(ref, e)
        if ref is None or not r.c < ref:          # need a gap UP into/over a box that FAILED
            continue
        f = features(x, i)
        if f is None:
            continue
        res = {}
        for n, nm in ((1, "d1"), (3, "d3"), (5, "d5")):
            res[nm] = -(d.c.iloc[i + n] / r.c - 1) * 100 if i + n < len(d) else np.nan   # puts
        out.append(dict(symbol=sym, date=day, gap_pct=gp, **f, **res))
    return out


def cell(x, col="d3"):
    x = x[[col, "date"]].dropna()
    if len(x) < 10:
        return "— (n %d)" % len(x)
    dm = x.groupby("date")[col].mean()
    t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")
    return f"{x[col].mean():+.2f}% ({(x[col] > 0).mean():.0%} your way, t {t:.1f}, n {len(x)})"


def block(E, title):
    L = [f"\n# {title}\n", "## Each confirmation on its own (puts, 3-day move)\n",
         "| Confirmation | When TRUE | When FALSE |", "|---|---|---|",
         f"| (all failed gap-ups) | {cell(E)} | |"]
    for c in CONF:
        L.append(f"| {c} | {cell(E[E[c]])} | {cell(E[~E[c]])} |")
    L += ["\n## Stacked: number of confirmations (puts)\n",
          "| Score | Next day | 3 days | 5 days |", "|---|---|---|---|"]
    for lab, m in (("0-1", E.score <= 1), ("2-3", E.score.between(2, 3)), ("4-5", E.score.between(4, 5)),
                   ("6-7", E.score >= 6), ("4 or more", E.score >= 4)):
        x = E[m]
        L.append(f"| {lab} | {cell(x,'d1')} | {cell(x,'d3')} | {cell(x,'d5')} |")
    return L


def main():
    os.makedirs(OUT, exist_ok=True)
    u = pd.read_csv("universe/universe.csv")
    u = u[u.group != "gauge"].sort_values("avg_dollar_vol", ascending=False).head(gr.MAX_SYMBOLS)
    core = set(u[u.group == "core"].symbol); syms = u.symbol.tolist()
    cap = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)
    start = pd.Timestamp(PERIODS[0][1])
    E = []
    for i in range(0, len(syms), 100):
        ch = syms[i:i + 100]
        try:
            dd = sb.fetch(ch, "1Day", "2020-06-01", cap.isoformat())
        except Exception as ex:
            print("fetch", ch[:2], ex); continue
        for s in ch:
            x = dd[dd.symbol == s]
            if len(x) < 80:
                continue
            x = x.assign(day=x.t.dt.tz_localize(None).dt.normalize()).set_index("day")[["o", "h", "l", "c"]]
            try:
                E += events_for(s, x, start)
            except Exception as ex:
                print(f"  {s}: {ex}")
        print(f"  {min(i + 100, len(syms))}/{len(syms)} symbols, {len(E)} failed gap-ups", flush=True)
    E = pd.DataFrame(E); E["core"] = E.symbol.isin(core)
    E.to_csv(f"{OUT}/events.csv.gz", index=False, compression="gzip")
    L = ["# Confirmation test — failed gap-up (INTC trap) + daily confirmations",
         f"\n{len(E)} failed gap-ups, {E.date.min():%b %Y} to {E.date.max():%b %Y}, {len(syms)} names. "
         "Puts entered at the failed day's close; moves in the puts' direction; t clustered by day."]
    checks = []
    for title, a, b in PERIODS:
        X = E[(E.date >= pd.Timestamp(a)) & (E.date <= pd.Timestamp(b))]
        if X.empty:
            continue
        L += block(X, f"PERIOD {title} — full universe") + block(X[X.core], f"PERIOD {title} — your core tickers")
        s4 = X[X.score >= 4][["d3", "date"]].dropna(); al = X[["d3", "date"]].dropna()
        dm = s4.groupby("date").d3.mean()
        t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 else float("nan")
        checks.append((title, s4.d3.mean(), t, len(s4), al.d3.mean()))
    L += ["\n# PASS CHECK (set before running): score >= 4 puts, 3-day move, full universe\n",
          "| Period | Score >= 4 | All failed gap-ups | Verdict |", "|---|---|---|---|"]
    for title, m, t, n, base in checks:
        ok = m > 0 and t >= 2 and m > base
        L.append(f"| {title} | {m:+.2f}%, t {t:.1f}, n {n} | {base:+.2f}% | {'PASS' if ok else 'FAIL'} |")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
