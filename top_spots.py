"""
Find the bear spot: line up every big drop off a top (860 stocks), compare it with matched charts that did NOT drop,
learn on 2016-21, judge on 2022-26.

Candidate day = within 1 ATR of its 20-day high (a top area). Event ("DUMP") = the low over the next 10 days is 3+ ATR
under the candidate day's close BEFORE price trades 1.5 ATR above it. "RIP" = the mirror (3 ATR up before 1.5 down),
so a feature that only predicts big moves both ways can't pass as a bear signal.
Outputs results/expanded/TOP_SPOTS.md
"""
import os, time
import numpy as np, pandas as pd
import yfinance as yf
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

OUT = "results/expanded"; os.makedirs(OUT, exist_ok=True)
U = pd.read_csv("universe/expanded_universe.csv")
SECT = sorted(set(U.sector_etf.dropna()) | {"SPY", "QQQ"})


def pull(symbols):
    data = {}
    for i in range(0, len(symbols), 60):
        chunk = symbols[i:i + 60]
        for _ in range(3):
            try:
                df = yf.download(chunk, period="11y", interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False); break
            except Exception as e:
                print("retry", e); time.sleep(5)
        for s in chunk:
            try:
                x = (df[s] if len(chunk) > 1 else df).rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
                x.columns = ["o", "h", "l", "c", "v"]
                if len(x) > 300: data[s] = x
            except Exception:
                pass
        print(f"pulled {min(i+60, len(symbols))}/{len(symbols)}", flush=True)
    return data


def build(x):
    c, o, h, l, v = x.c, x.o, x.h, x.l, x.v
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    A = tr.ewm(alpha=1 / 14, adjust=False).mean()
    f = pd.DataFrame(index=x.index)
    ma = {"e8": c.ewm(span=8, adjust=False).mean(), "e21": c.ewm(span=21, adjust=False).mean(), "s10": c.rolling(10).mean(),
          "s20": c.rolling(20).mean(), "s50": c.rolling(50).mean(), "s200": c.rolling(200).mean()}
    for k, m in ma.items():
        f[f"vs_{k}"] = (c - m) / A; f[f"slope_{k}"] = (m - m.shift(5)) / A
    f["s50_vs_s200"] = (ma["s50"] - ma["s200"]) / A; f["s10_vs_s20"] = (ma["s10"] - ma["s20"]) / A
    d = c.diff(); g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean(); lo = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean()
    rsi = 100 - 100 / (1 + g / lo); f["rsi"] = rsi; f["rsi_chg5"] = rsi - rsi.shift(5); f["rsi_max10"] = rsi.rolling(10).max()
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); sg = m.ewm(span=9, adjust=False).mean()
    f["macd"] = m / A; f["macd_hist"] = (m - sg) / A; f["macd_hist_chg3"] = ((m - sg) - (m - sg).shift(3)) / A
    rng = (h - l).replace(0, np.nan)
    f["upwick"] = (h - np.maximum(o, c)) / rng; f["upwick_avg5"] = f.upwick.rolling(5).mean()
    f["body"] = (c - o) / rng; f["red_count10"] = (c < o).rolling(10).sum()
    lh = (h < h.shift()).astype(int); f["lower_highs10"] = lh.rolling(10).sum()
    f["range5_vs_atr"] = (h.rolling(5).max() - l.rolling(5).min()) / A; f["atr_chg20"] = A / A.shift(20)
    f["atr_pct"] = A / c * 100
    f["vol_ratio"] = v / v.rolling(20).mean(); f["vol_trend"] = v.rolling(5).mean() / v.rolling(20).mean()
    f["r5"] = c.pct_change(5) * 100; f["r20"] = c.pct_change(20) * 100; f["r60"] = c.pct_change(60) * 100
    f["from_hi20"] = (h.rolling(20).max() - c) / A; f["from_hi52"] = (h.rolling(252).max() - c) / A
    f["days_since_hi20"] = h.rolling(20).apply(lambda w: 19 - np.argmax(w), raw=True)
    f["gap"] = (o - c.shift()) / A; f["dow"] = x.index.dayofweek
    hv, lv, cv, Av = h.values, l.values, c.values, A.values
    n = len(cv); dump = np.full(n, np.nan); rip = np.full(n, np.nan)
    for e in range(n - 11):
        ref = cv[e]; a = Av[e]; d_, r_ = 0.0, 0.0
        for j in range(e + 1, e + 11):
            if lv[j] <= ref - 3 * a: d_ = 1.0; break
            if hv[j] >= ref + 1.5 * a: break
        for j in range(e + 1, e + 11):
            if hv[j] >= ref + 3 * a: r_ = 1.0; break
            if lv[j] <= ref - 1.5 * a: break
        dump[e] = d_; rip[e] = r_
    f["DUMP"] = dump; f["RIP"] = rip; f["A"] = A
    return f


def main():
    data = pull(sorted(set(U.symbol) | set(SECT)))
    q = build(data["QQQ"]); smap = dict(zip(U.symbol, U.sector_etf))
    secf = {s: build(data[s]) for s in SECT if s in data}
    frames = []
    for s in U.symbol:
        if s not in data or s in ("QQQ",): continue
        f = build(data[s])
        f = f[(f.from_hi20 <= 1.0) & f.DUMP.notna()].iloc[260:] if len(f) > 300 else f.iloc[0:0]
        if not len(f): continue
        qf = q.reindex(f.index)
        for k in ("vs_e8", "vs_s50", "r5", "rsi", "macd_hist"): f[f"qqq_{k}"] = qf[k].values
        sf = secf.get(smap.get(s))
        if sf is not None: f["sector_r5_vs_qqq"] = sf.r5.reindex(f.index).values - qf.r5.values
        f["rel_r5_vs_qqq"] = f.r5 - qf.r5.values; f["rel_r20_vs_qqq"] = f.r20 - q.r20.reindex(f.index).values
        f["sym"] = s; frames.append(f)
        print("built", s, flush=True)
    D = pd.concat(frames); D["train"] = D.index < "2022-01-01"
    D.to_parquet(f"{OUT}/top_spots_rows.parquet")
    X = [c for c in D.columns if c not in ("DUMP", "RIP", "A", "sym", "train")]
    tr, te = D[D.train], D[~D.train]
    L = ["# The bear spot: big drops off a top vs. matched charts that didn't drop", "",
         f"Top-area days (within 1 ATR of the 20-day high): {len(D):,}. DUMP = 3 ATR down before 1.5 ATR up within 10 days.",
         f"Base rates: DUMP train {tr.DUMP.mean()*100:.1f}% / test {te.DUMP.mean()*100:.1f}% | RIP train {tr.RIP.mean()*100:.1f}% / test {te.RIP.mean()*100:.1f}%", ""]
    # 1) what dumps look like vs the top days that did not dump (same top area = matched on location)
    L += ["## What was different the day before a dump (dumps vs top days that didn't dump)", "",
          "| Measure | Dumps (median) | No dump (median) | Holds in 2016-21 AND 2022-26? |", "|---|---|---|---|"]
    diffs = []
    for k in X:
        a1 = tr[tr.DUMP == 1][k].median(); a0 = tr[tr.DUMP == 0][k].median(); b1 = te[te.DUMP == 1][k].median(); b0 = te[te.DUMP == 0][k].median()
        sd = D[k].std() or 1
        same = np.sign(a1 - a0) == np.sign(b1 - b0)
        diffs.append((min(abs(a1 - a0), abs(b1 - b0)) / sd if same else 0, k, D[D.DUMP == 1][k].median(), D[D.DUMP == 0][k].median(), same))
    diffs.sort(key=lambda z: -z[0])
    for z in diffs[:15]:
        L.append(f"| {z[1]} | {z[2]:.2f} | {z[3]:.2f} | {'yes' if z[4] else 'no'} (effect {z[0]:.2f} sd) |")
    # 2) model trained 2016-21, judged on 2022-26 for DUMP, and the same score's RIP rate (direction check)
    mdl = HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300, min_samples_leaf=300, l2_regularization=1.0)
    mdl.fit(tr[X], tr.DUMP)
    p = mdl.predict_proba(te[X])[:, 1]; te = te.assign(p=p)
    L += ["", "## Model trained on 2016-21, judged on 2022-26", "",
          f"AUC for DUMP: {roc_auc_score(te.DUMP, p):.3f} (0.50 = no skill) | same score vs RIP: {roc_auc_score(te.RIP, p):.3f}", "",
          "| Model score bucket (2022-26) | Days | DUMP | RIP | Dump minus rip |", "|---|---|---|---|---|"]
    for lo_, hi_, lab in ((0, .5, "bottom 50%"), (.5, .8, "50-80%"), (.8, .9, "top 20-10%"), (.9, .95, "top 10-5%"), (.95, .99, "top 5-1%"), (.99, 1.01, "top 1%")):
        g = te[(te.p >= np.quantile(p, lo_)) & (te.p <= np.quantile(p, min(hi_, 1)))]
        L.append(f"| {lab} | {len(g):,} | {g.DUMP.mean()*100:.1f}% | {g.RIP.mean()*100:.1f}% | {(g.DUMP.mean()-g.RIP.mean())*100:+.1f} pts |")
    # 3) the simplest readable rules: top 3 features as thresholds, checked on test
    L += ["", "## Readable version: top measures as one-line rules (cut picked on 2016-21, judged on 2022-26)", "",
          "| Rule | 2016-21 days | DUMP 2016-21 | 2022-26 days | **DUMP 2022-26** | RIP 2022-26 |", "|---|---|---|---|---|---|"]
    for z in diffs[:8]:
        k = z[1]; hi_side = z[2] > z[3]
        cut = tr[k].quantile(0.8 if hi_side else 0.2)
        mtr = tr[k] >= cut if hi_side else tr[k] <= cut; mte = te[k] >= cut if hi_side else te[k] <= cut
        L.append(f"| {k} {'>=' if hi_side else '<='} {cut:.2f} | {mtr.sum():,} | {tr[mtr].DUMP.mean()*100:.1f}% | {mte.sum():,} | **{te[mte].DUMP.mean()*100:.1f}%** | {te[mte].RIP.mean()*100:.1f}% |")
    imp = pd.Series(dict(zip(X, np.zeros(len(X)))))
    open(f"{OUT}/TOP_SPOTS.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
