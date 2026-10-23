"""
Full moving-average cross grid on ~860 stocks: every EMA and SMA pair, bearish (fast crosses under slow)
and bullish (fast crosses over slow). Ranked on 2016-21, then judged on 2022-26 (never used to rank).

MAs: EMA 5, 8, 9, 10, 13, 20, 21, 50, 200 and SMA 5, 10, 20, 50, 100, 200 (close, daily, regular session).
Outcomes from the cross day's close:
  swing: moves 2 ATR in the cross direction before 2 ATR against, within 20 days
  short: moves 1.5 ATR in the cross direction before 1.5 ATR against, within 5 days
Each cross is also tested with QQQ agreeing (QQQ under its 8 EMA for bear crosses, over it for bull).
"""
import os, time, itertools
import numpy as np, pandas as pd
import yfinance as yf

OUT = "results/expanded"; os.makedirs(OUT, exist_ok=True)
U = pd.read_csv("universe/expanded_universe.csv")
MAS = [("EMA", n) for n in (5, 8, 9, 10, 13, 20, 21, 50, 200)] + [("SMA", n) for n in (5, 10, 20, 50, 100, 200)]


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
                x = (df[s] if len(chunk) > 1 else df).rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
                x.columns = ["o", "h", "l", "c"]
                if len(x) > 300: data[s] = x
            except Exception:
                pass
        print(f"pulled {min(i+60, len(symbols))}/{len(symbols)}", flush=True)
    return data


def first_hit(h, l, c, a, idx, k, days, sign):
    """sign=+1 bear (want down), -1 bull (want up). 1 = moved our way first, 0 = against first."""
    out = np.full(len(idx), np.nan)
    for n, e in enumerate(idx):
        if e + 1 >= len(c): continue
        ref = c[e]; A = a[e]
        for j in range(e + 1, min(e + 1 + days, len(c))):
            dn = l[j] <= ref - k * A; up = h[j] >= ref + k * A
            if dn and up: break
            if dn: out[n] = 1.0 if sign == 1 else 0.0; break
            if up: out[n] = 0.0 if sign == 1 else 1.0; break
    return out


def main():
    data = pull(sorted(set(U.symbol) | {"QQQ"}))
    q = data["QQQ"]; q_e8 = q.c.ewm(span=8, adjust=False).mean()
    q_bear = (q.c < q_e8)
    rec = []          # (pair, direction, date, swing, short, qqq_agrees)
    base = []
    for s, x in data.items():
        c = x.c; h, l, cv = x.h.values, x.l.values, c.values
        tr = pd.concat([x.h - x.l, (x.h - c.shift()).abs(), (x.l - c.shift()).abs()], axis=1).max(axis=1)
        a = tr.ewm(alpha=1 / 14, adjust=False).mean().values
        ma = {f"{t}{n}": (c.ewm(span=n, adjust=False).mean() if t == "EMA" else c.rolling(n).mean()).values for t, n in MAS}
        qb = q_bear.reindex(x.index).values
        valid = np.arange(len(c)) >= 210
        allidx = np.arange(len(c))
        OUTC = {sign: (first_hit(h, l, cv, a, allidx, 2.0, 20, sign), first_hit(h, l, cv, a, allidx, 1.5, 5, sign)) for sign in (1, -1)}
        bidx = np.where(valid & (allidx % 5 == 0) & (allidx < len(c) - 21))[0]
        for sign in (1, -1):
            sw, sh = OUTC[sign][0][bidx], OUTC[sign][1][bidx]
            for e, y1, y2 in zip(bidx, sw, sh): base.append(("bear" if sign == 1 else "bull", x.index[e], y1, y2))
        for (t1, n1), (t2, n2) in itertools.product(MAS, MAS):
            if n1 >= n2: continue
            f, sl = ma[f"{t1}{n1}"], ma[f"{t2}{n2}"]
            d = f - sl
            bear = np.where(valid[1:] & (d[1:] < 0) & (d[:-1] >= 0))[0] + 1
            bull = np.where(valid[1:] & (d[1:] > 0) & (d[:-1] <= 0))[0] + 1
            for sign, idx in ((1, bear), (-1, bull)):
                idx = idx[idx < len(c) - 21]
                if not len(idx): continue
                sw, sh = OUTC[sign][0][idx], OUTC[sign][1][idx]
                agree = (qb[idx] == True) if sign == 1 else (qb[idx] == False)
                for e, y1, y2, ag in zip(idx, sw, sh, agree):
                    rec.append((f"{t1} {n1} x {t2} {n2}", "bear" if sign == 1 else "bull", x.index[e], y1, y2, bool(ag)))
        print(f"scanned {s} | cross rows {len(rec):,}", flush=True)
    r = pd.DataFrame(rec, columns=["pair", "dir", "date", "swing", "short", "qqq_agrees"]); r["train"] = r.date < "2022-01-01"
    b = pd.DataFrame(base, columns=["dir", "date", "swing", "short"]); b["train"] = b.date < "2022-01-01"
    r.to_csv(f"{OUT}/cross_grid_rows.csv.gz", index=False)
    lines = ["# Full MA cross grid (860 stocks): ranked on 2016-21, judged on 2022-26", "",
             "Baseline = any day, same outcome, same direction. 'Lift' = cross minus baseline.", ""]
    for dr in ("bear", "bull"):
        for y, nm in (("swing", "2 ATR / 20 days"), ("short", "1.5 ATR / 5 days")):
            bt = b[(b.dir == dr) & b.train][y].mean(); be = b[(b.dir == dr) & ~b.train][y].mean()
            rows = []
            for pair, g in r[r.dir == dr].groupby("pair"):
                for lab, gg in ((pair, g), (pair + " + QQQ agrees", g[g.qqq_agrees])):
                    tr = gg[gg.train][y].dropna(); te = gg[~gg.train][y].dropna()
                    if len(tr) >= 300 and len(te) >= 200:
                        rows.append((tr.mean() - bt, lab, len(tr), tr.mean(), len(te), te.mean(), te.mean() - be))
            rows.sort(key=lambda z: -z[0])
            lines += [f"## {dr.upper()} crosses | {nm} | baseline train {bt*100:.1f}% test {be*100:.1f}%", "",
                      "| Rank (by 2016-21) | Cross | Train n | Train | Test n | **Test 2022-26** | **Test lift** |", "|---|---|---|---|---|---|---|"]
            for i, z in enumerate(rows[:12], 1):
                lines.append(f"| {i} | {z[1]} | {z[2]:,} | {z[3]*100:.1f}% | {z[4]:,} | **{z[5]*100:.1f}%** | **{z[6]*100:+.1f} pts** |")
            lines += ["", f"Crosses tested: {len(rows)}. Worst in train: " + ", ".join(f"{z[1]} ({z[3]*100:.0f}%)" for z in rows[-3:]), ""]
    open(f"{OUT}/CROSS_GRID.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
