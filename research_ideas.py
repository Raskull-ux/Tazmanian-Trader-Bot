"""
Effects with published evidence, tested on ~860 stocks (Taz's 75 + sector peers), puts-side.
Outcomes from the signal day's close:
  short = drops 1.5 ATR before rising 1.5 ATR within 5 days
  swing = drops 2 ATR before rising 2 ATR within 20 days
  r10 / r20 = forward % return; vs_mkt20 = 20-day return minus QQQ's (negative = underperformed)
Every row split 2016-21 vs 2022-26 (earnings rows exist only for 2024-26).
"""
import os, time
import numpy as np, pandas as pd
import yfinance as yf

OUT = "results/expanded"; os.makedirs(OUT, exist_ok=True)
U = pd.read_csv("universe/expanded_universe.csv")
E = pd.read_csv("universe/earnings_edgar.csv", parse_dates=["earnings_date"])


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


def outcomes(h, l, c, a):
    n = len(c); sh = np.full(n, np.nan); sw = np.full(n, np.nan)
    for e in range(n - 1):
        for arr, k, days in ((sh, 1.5, 5), (sw, 2.0, 20)):
            ref = c[e]
            for j in range(e + 1, min(e + 1 + days, n)):
                dn = l[j] <= ref - k * a[e]; up = h[j] >= ref + k * a[e]
                if dn and up: break
                if dn: arr[e] = 1.0; break
                if up: arr[e] = 0.0; break
    return sh, sw


def main():
    data = pull(sorted(set(U.symbol) | {"QQQ"}))
    q = data["QQQ"].c
    panel = {}
    for s, x in data.items():
        c = x.c
        tr = pd.concat([x.h - x.l, (x.h - c.shift()).abs(), (x.l - c.shift()).abs()], axis=1).max(axis=1)
        x["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
        x["e8"] = c.ewm(span=8, adjust=False).mean()
        for n in (10, 20, 50, 200): x[f"s{n}"] = c.rolling(n).mean()
        x["r126"] = c.pct_change(126); x["r5"] = c.pct_change(5)
        x["hi52"] = x.h.rolling(252).max(); x["lo52"] = x.l.rolling(252).min()
        sh, sw = outcomes(x.h.values, x.l.values, c.values, x.atr.values)
        x["short"] = sh; x["swing"] = sw
        x["r10"] = c.shift(-10) / c - 1; x["r20"] = c.shift(-20) / c - 1
        qq = q.reindex(x.index); x["vs_mkt20"] = x.r20 - (qq.shift(-20) / qq - 1)
        panel[s] = x
    # cross-sectional ranks by date (momentum deciles, weekly winners)
    r126 = pd.DataFrame({s: x.r126 for s, x in panel.items()}); r5 = pd.DataFrame({s: x.r5 for s, x in panel.items()})
    mom_rank = r126.rank(axis=1, pct=True); wk_rank = r5.rank(axis=1, pct=True)
    rows = []
    for s, x in panel.items():
        if s == "QQQ": continue
        o, h, l, c = x.o.values, x.h.values, x.l.values, x.c.values; A = x.atr.values
        mr = mom_rank[s].reindex(x.index).values; wr = wk_rank[s].reindex(x.index).values
        ed = set(E[E.symbol == s].earnings_date.dt.normalize())
        idx = x.index
        for e in range(260, len(c) - 21):
            t = idx[e]; tags = []
            if e % 5 == 0: tags.append("baseline")
            # 1) earnings reaction: the first session that trades on the news (bmo = same day, amc = next day)
            if t in ed or (e > 0 and idx[e - 1] in ed):
                move = (c[e] - c[e - 1]) / A[e - 1]
                if move <= -2: tags.append("earnings: day-1 drop 2+ ATR (drift?)")
                elif move >= 2: tags.append("earnings: day-1 pop 2+ ATR")
            # 2) momentum losers (bottom 10% over 6 months) that pop into the 10/20 SMA and close under
            if np.isfinite(mr[e]) and mr[e] <= 0.10:
                tags.append("6-month loser (bottom 10%)")
                if h[e] >= min(x.s10.values[e], x.s20.values[e]) and c[e] < max(x.s10.values[e], x.s20.values[e]):
                    tags.append("6-month loser + pop into 10/20 SMA, closed under")
            if np.isfinite(mr[e]) and mr[e] >= 0.90: tags.append("6-month winner (top 10%)")
            # 3) short-term reversal: biggest 1-week gainers
            if np.isfinite(wr[e]) and wr[e] >= 0.95: tags.append("top 5% 1-week gainer")
            if np.isfinite(wr[e]) and wr[e] >= 0.95 and c[e] < x.s200.values[e]: tags.append("top 5% 1-week gainer, under the 200")
            # 4) gap-up fail: opens above yesterday's high, closes red under yesterday's close
            if o[e] > h[e - 1] and c[e] < c[e - 1]: tags.append("gap-up fail (open > prior high, close < prior close)")
            # 5) 52-week location
            if (c[e] - x.lo52.values[e]) / A[e] <= 2: tags.append("within 2 ATR of the 52-week low")
            if (x.hi52.values[e] - c[e]) / A[e] <= 2: tags.append("within 2 ATR of the 52-week high")
            if not tags: continue
            for tg in tags:
                rows.append((s, t, tg, x.short.values[e], x.swing.values[e], x.r10.values[e] * 100, x.r20.values[e] * 100, x.vs_mkt20.values[e] * 100))
    r = pd.DataFrame(rows, columns=["sym", "date", "setup", "short", "swing", "r10", "r20", "vs_mkt20"])
    r["era"] = np.where(r.date < "2022-01-01", "2016-21", "2022-26"); r.to_csv(f"{OUT}/ideas_rows.csv.gz", index=False)
    b = r[r.setup == "baseline"]
    def stat(g, col): return g[col].dropna().mean() * 100
    lines = ["# Published-effect tests (puts side), 860 stocks", "",
             "| Setup | Signals | Short puts: drop first (5d) | 2016-21 / 2022-26 | Swing: drop first (20d) | 20d median | 20d vs QQQ (mean) |", "|---|---|---|---|---|---|---|"]
    for s_, g in r.groupby("setup"):
        a = g[g.era == "2016-21"]; z = g[g.era == "2022-26"]
        lines.append(f"| {s_} | {len(g):,} | {stat(g,'short'):.1f}% | {stat(a,'short'):.1f}% / {stat(z,'short'):.1f}% | {stat(g,'swing'):.1f}% | {g.r20.median():+.2f}% | {g.vs_mkt20.mean():+.2f}% |")
    eb = b[b.date >= "2024-01-01"]
    lines += ["", f"Baseline 2024-26 only (compare earnings rows to this): short {stat(eb,'short'):.1f}% | swing {stat(eb,'swing'):.1f}% | 20d median {eb.r20.median():+.2f}% | vs QQQ {eb.vs_mkt20.mean():+.2f}%"]
    open(f"{OUT}/IDEAS_REPORT.md", "w").write("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
