"""
Find the edge, honestly: stack conditions on the setups that showed a real (small) edge on 860 stocks,
choosing filters on 2016-2021 ONLY, then judging them on 2022-2026 (never seen while choosing).

Setups: staircase + green higher high under the top + RSI<50, long staircase at a top + RSI<50,
MACD cross down at a top. Outcomes: drop 2 ATR before rising 2 ATR in 20 days (swing) and
drop 1.5 ATR before rising 1.5 ATR in 5 days (short-dated puts).
"""
import os, itertools, time
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


def feats(x):
    c = x.c
    tr = pd.concat([x.h - x.l, (x.h - c.shift()).abs(), (x.l - c.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    x["e8"] = c.ewm(span=8, adjust=False).mean(); x["e10"] = c.ewm(span=10, adjust=False).mean()
    for n in (10, 20, 50, 200): x[f"s{n}"] = c.rolling(n).mean()
    d = c.diff(); g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean(); x["rsi"] = 100 - 100 / (1 + g / l)
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); x["macd"] = m; x["sig"] = m.ewm(span=9, adjust=False).mean()
    x["hh20"] = x.h.rolling(20).max(); x["r5"] = c.pct_change(5); x["v20"] = x.v.rolling(20).mean()
    return x


def race(h, l, c, a, e, k, days):
    ref = c[e]
    for j in range(e + 1, min(e + 1 + days, len(c))):
        dn = l[j] <= ref - k * a[e]; up = h[j] >= ref + k * a[e]
        if dn and up: return np.nan
        if dn: return 1.0
        if up: return 0.0
    return np.nan


def main():
    data = pull(sorted(set(U.symbol) | set(SECT)))
    F = {s: feats(x.copy()) for s, x in data.items()}
    q = F["QQQ"]; spy = F.get("SPY")
    smap = dict(zip(U.symbol, U.sector_etf))
    rows = []
    for s, x in F.items():
        if s in SECT and s not in set(U.symbol): continue
        o, h, l, c, v = (x[k].values for k in "ohlcv"); A = x.atr.values; e8 = x.e8.values; s10 = x.s10.values
        e10 = x.e10.values; s50 = x.s50.values; s200 = x.s200.values; R = x.rsi.values; M = x.macd.values; S = x.sig.values
        hh20 = x.hh20.values; r5 = x.r5.values; v20 = x.v20.values
        qq = q.reindex(x.index); q_c, q_o, q_e8, q_r5 = qq.c.values, qq.o.values, qq.e8.values, qq.r5.values
        sec = F.get(smap.get(s)); sec_r5 = sec.r5.reindex(x.index).values if sec is not None else None
        spy_r5 = spy.r5.reindex(x.index).values if spy is not None else None
        G = c > o; Rd = c < o
        run = np.zeros(len(c), int)
        for i in range(1, len(c)): run[i] = run[i - 1] + 1 if h[i] < h[i - 1] else 0
        for e in range(260, len(c) - 21):
            setups = []
            if G[e] and run[e - 1] >= 3:
                st = e - 1 - run[e - 1]
                if h[st] >= hh20[st] and c[st] > s50[st] and h[e - 1] < h[e] < h[st] and R[e] < 50: setups.append(("stairHH", st))
            if G[e]:
                for k in (4, 5):
                    st = e - k - 1
                    if G[st] and all(Rd[j] for j in range(st + 1, e)) and all(h[j + 1] < h[j] for j in range(st, e - 1)) and h[e] < h[st] and h[st] >= hh20[st] and R[e] < 50:
                        setups.append(("longstair", st)); break
            if M[e] < S[e] and M[e - 1] >= S[e - 1] and M[e] > 0 and (hh20[e] - h[e]) <= A[e]: setups.append(("macdtop", e))
            if not setups: continue
            y20 = race(h, l, c, A, e, 2.0, 20); y5 = race(h, l, c, A, e, 1.5, 5)
            base = dict(sym=s, date=x.index[e], y20=y20, y5=y5,
                        under8=float(c[e] < e8[e]), under50=float(c[e] < s50[e]), bear1010=float(e10[e] < s10[e]),
                        rsi=R[e], macd_above=float(M[e] > S[e]), atr_pct=A[e] / c[e] * 100,
                        weaker_qqq=float(r5[e] < q_r5[e]) if np.isfinite(q_r5[e]) else np.nan,
                        qqq_under8=float(q_c[e] < q_e8[e]), qqq_red=float(q_c[e] < q_o[e]), qqq_5d=q_r5[e] * 100,
                        sec_weaker_spy=float(sec_r5[e] < spy_r5[e]) if sec_r5 is not None and spy_r5 is not None and np.isfinite(sec_r5[e]) and np.isfinite(spy_r5[e]) else np.nan,
                        vol_ratio=v[e] / v20[e] if v20[e] else np.nan, gap_up=float(o[e] > c[e - 1]),
                        vs200=(c[e] - s200[e]) / A[e], body=(c[e] - o[e]) / max(h[e] - l[e], 1e-9))
            for nm, st in setups:
                rows.append(dict(base, setup=nm, stair_len=run[e - 1] if nm == "stairHH" else e - st - 1,
                                 below_top=(h[st] - c[e]) / A[e]))
    r = pd.DataFrame(rows); r["train"] = r.date < "2022-01-01"; r.to_csv(f"{OUT}/stack_rows.csv.gz", index=False)

    cond = {"stock under 8 EMA": r.under8 == 1, "stock under 50": r.under50 == 1, "10 EMA under 10 SMA": r.bear1010 == 1,
            "RSI < 40": r.rsi < 40, "MACD still above signal": r.macd_above == 1, "high volatility (ATR% top third)": r.atr_pct >= r.atr_pct.quantile(2 / 3),
            "low volatility (ATR% bottom third)": r.atr_pct <= r.atr_pct.quantile(1 / 3), "weaker than QQQ (5d)": r.weaker_qqq == 1,
            "QQQ under its 8 EMA": r.qqq_under8 == 1, "QQQ red that day": r.qqq_red == 1, "QQQ down over 5 days": r.qqq_5d < 0,
            "sector weaker than SPY (5d)": r.sec_weaker_spy == 1, "volume 1.3x+": r.vol_ratio >= 1.3, "light volume <0.8x": r.vol_ratio < 0.8,
            "gapped up": r.gap_up == 1, "within 2 ATR of the top": r.below_top <= 2, "3+ ATR under the top": r.below_top >= 3,
            "far over the 200 (8+ ATR)": r.vs200 >= 8, "near the 200 (<3 ATR)": r.vs200 < 3, "small body (<30%)": r.body.abs() < 0.3}
    lines = ["# Finding the edge: filters chosen on 2016-21, judged on 2022-26", ""]
    for setup in ["stairHH", "longstair", "macdtop"]:
        for y in ["y20", "y5"]:
            g = r[(r.setup == setup)].dropna(subset=[y])
            tr, te = g[g.train], g[~g.train]
            btr, bte = tr[y].mean(), te[y].mean()
            cands = []
            for k in (1, 2):
                for combo in itertools.combinations(cond, k):
                    m = np.logical_and.reduce([cond[c_].reindex(g.index).fillna(False).values for c_ in combo])
                    a = tr[m[g.train.values]]
                    if len(a) >= 150: cands.append((a[y].mean() - btr, combo, len(a), a[y].mean()))
            cands.sort(key=lambda z: -z[0]); pick = cands[:5]       # chosen on TRAIN only
            lines += [f"## {setup} | outcome {'2 ATR / 20 days' if y=='y20' else '1.5 ATR / 5 days'}",
                      f"Setup alone: train {btr*100:.1f}% (n {len(tr)}), test {bte*100:.1f}% (n {len(te)})", "",
                      "| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |", "|---|---|---|---|---|---|"]
            for lift, combo, n, p in pick:
                m = np.logical_and.reduce([cond[c_].reindex(g.index).fillna(False).values for c_ in combo])
                b = te[m[~g.train.values]]
                lines.append(f"| {' + '.join(combo)} | {n} | {p*100:.1f}% | {len(b)} | **{b[y].mean()*100:.1f}%** | {(b[y].mean()-bte)*100:+.1f} pts |")
            # model: trained on 2016-21 features, judged on 2022-26
            X = [c_ for c_ in ["under8", "under50", "bear1010", "rsi", "macd_above", "atr_pct", "weaker_qqq", "qqq_under8", "qqq_red", "qqq_5d",
                               "sec_weaker_spy", "vol_ratio", "gap_up", "vs200", "body", "stair_len", "below_top"]]
            if len(tr) > 500 and len(te) > 300:
                mdl = HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, min_samples_leaf=100).fit(tr[X], tr[y])
                p = mdl.predict_proba(te[X])[:, 1]; auc = roc_auc_score(te[y], p)
                top = te[p >= np.quantile(p, 0.8)]
                lines += ["", f"Model (trained 2016-21): test AUC {auc:.3f} | top 20% of model scores in 2022-26: {top[y].mean()*100:.1f}% (n {len(top)}) vs {bte*100:.1f}%"]
            lines.append("")
    open(f"{OUT}/STACK_REPORT.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
