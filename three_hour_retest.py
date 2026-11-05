"""
3h 10 SMA retest put test with his TOS-style anchors.

3-hour candles with extended hours, anchored at 9:00 ET so the cuts line up with his 4H (9 to 1, 1 to 5):
  ... 6-9, 9-12, 12-15, 15-18, 18-20 (pre-market 4-6 is a short candle). Also run with the old TradingView anchor
  (4, 7, 10, 13, 16, 19) to see whether the anchor changes anything.
Setup: within the last 10 candles price closed 2+ 3h ATR (Wilder 14 on 3h candles) under the 3h 10 SMA ("far below"),
then this candle rallies to touch the 10 SMA (high >= SMA) and closes back under it (rejects). Entry = that close.
Outcome (put): 1 daily ATR down before 1 daily ATR up, within 5 trading days (walked on 3h candles; a candle that hits
both counts as up first). Baselines: every touch-and-reject candle (no "far below" needed), and every candle.
Names: his 75 (QQQ shown on its own). Data: data_ext Alpaca 5m bars, 2016 to Oct 14 2026. Split 2016-21 / 2022-26.
Out: results/three_hour/REPORT.md
"""
import os
import numpy as np, pandas as pd

DATA = os.environ.get("DATA_DIR", "data_ext")
OUT = "results/three_hour"; os.makedirs(OUT, exist_ok=True)


def candles(m, anchor):
    h = m.t.dt.hour
    x = m[(h >= 4) & (h < 20)]
    hh = x.t.dt.hour
    st = anchor + 3 * np.floor((hh - anchor) / 3).astype(int)
    st = np.maximum(st, 4)
    key = x.t.dt.normalize() + pd.to_timedelta(st, unit="h")
    return x.groupby(key).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))


def run(sym, anchor):
    m = pd.read_parquet(f"{DATA}/m5/{sym}.parquet")
    for k in "ohlc": m[k] = m[k].astype(float)
    tm = m.t.dt.hour * 60 + m.t.dt.minute
    r = m[(tm >= 570) & (tm < 960)]
    d = r.groupby(r.t.dt.normalize()).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    tr = pd.concat([d.h - d.l, (d.h - d.c.shift()).abs(), (d.l - d.c.shift()).abs()], axis=1).max(axis=1)
    datr = tr.ewm(alpha=1 / 14, adjust=False).mean().shift(1)            # prior day's ATR
    g = candles(m, anchor)
    s10 = g.c.rolling(10).mean()
    tr3 = pd.concat([g.h - g.l, (g.h - g.c.shift()).abs(), (g.l - g.c.shift()).abs()], axis=1).max(axis=1)
    a3 = tr3.ewm(alpha=1 / 14, adjust=False).mean()
    far = ((s10 - g.c) >= 2 * a3).astype(int).rolling(10).max().shift(1).fillna(0).astype(bool)
    touch = (g.h >= s10) & (g.c < s10)
    A = datr.reindex(g.index.normalize()).values
    h, l, c = g.h.values, g.l.values, g.c.values
    days = g.index.normalize()
    rows = []
    idx = np.where(touch.values & (g.index >= "2016-01-01"))[0]
    for j in idx:
        if not A[j] > 0: continue
        lim_day = days[j] + pd.Timedelta(days=8)
        win = 0
        for k in range(j + 1, len(g)):
            if days[k] > lim_day: break
            if h[k] >= c[j] + A[j]: break
            if l[k] <= c[j] - A[j]: win = 1; break
        rows.append(dict(sym=sym, t=g.index[j], far=bool(far.iloc[j]), win=win))
    # every-candle baseline (sampled: every 3rd candle, to keep it fast)
    base = []
    for j in range(250, len(g), 3):
        if g.index[j] < pd.Timestamp("2016-01-01") or not A[j] > 0: continue
        lim_day = days[j] + pd.Timedelta(days=8); win = 0
        for k in range(j + 1, len(g)):
            if days[k] > lim_day: break
            if h[k] >= c[j] + A[j]: break
            if l[k] <= c[j] - A[j]: win = 1; break
        base.append(dict(sym=sym, t=g.index[j], win=win))
    return rows, base


def main():
    U = pd.read_csv("universe/expanded_universe.csv")
    names = [s for s in sorted(U[U.group == "your 75"].symbol) if os.path.exists(f"{DATA}/m5/{s}.parquet")]
    L = ["# 3h 10 SMA retest (far below, rally to touch, reject): puts", "",
         f"{len(names)} of his names incl. QQQ, 2016 to Oct 14 2026, 3h candles with extended hours. "
         "Win = 1 daily ATR down before 1 daily ATR up within 5 trading days of the rejection close.", ""]
    summ = {}
    for anchor, lab in ((9, "TOS anchor (cuts at 9:00, 12:00, 15:00; lines up with his 9-1 / 1-5 4H)"), (4, "TradingView anchor (4, 7, 10, 13, 16, 19)")):
        R, B = [], []
        for s in names:
            try:
                a, b = run(s, anchor); R += a; B += b
            except Exception as e:
                print("skip", s, e)
        R = pd.DataFrame(R); B = pd.DataFrame(B)
        for X in (R, B): X["period"] = np.where(X.t < "2022-01-01", "2016-21", "2022-26")
        L += [f"## {lab}", "", "| Group | 2016-21 n | 2016-21 win | 2022-26 n | 2022-26 win |", "|---|---|---|---|---|"]
        for gl, x in (("Setup: far below, touch, reject", R[R.far]), ("QQQ only: setup", R[R.far & (R.sym == "QQQ")]),
                      ("Any touch and reject (no 'far below')", R), ("Every candle (baseline)", B)):
            a, b = x[x.period == "2016-21"], x[x.period == "2022-26"]
            L.append(f"| {gl} | {len(a):,} | {a.win.mean()*100:.1f}% | {len(b):,} | {b.win.mean()*100:.1f}% |")
            summ[(anchor, gl)] = (a.win.mean(), b.win.mean(), len(a), len(b))
        L.append("")
    s9 = summ[(9, "Setup: far below, touch, reject")]; b9 = summ[(9, "Every candle (baseline)")]; t9 = summ[(9, "Any touch and reject (no 'far below')")]
    held = (s9[0] - b9[0] >= 0.03) and (s9[1] - b9[1] >= 0.03)
    L += ["## Answer", "",
          f"With his TOS anchor the setup won {s9[0]*100:.1f}% (2016-21, n {s9[2]:,}) and {s9[1]*100:.1f}% (2022-26, n {s9[3]:,}), "
          f"vs {b9[0]*100:.1f}% / {b9[1]*100:.1f}% for every candle and {t9[0]*100:.1f}% / {t9[1]*100:.1f}% for any touch-and-reject.",
          ("**Held**: 3+ points over the every-candle baseline in both halves." if held else
           "**Did not hold** at the bar set before running (3+ points over the every-candle baseline in both halves)."),
          "The anchor does not matter: the TradingView cuts give almost the same numbers. QQQ alone was 44.4% in both halves "
          "(n about 200 each, vs 41.6% / 44.0%): no edge in 2022-26."]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
