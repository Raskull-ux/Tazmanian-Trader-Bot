"""
Expanded universe test: every mechanical setup from the Oct 22-23 2026 research, rerun on
~860 stocks (Taz's 75 + same-industry peers + liquid names), with results by sector.

Data: Yahoo daily bars (free), regular session, unadjusted OHLC. Settings match Taz's charts:
RSI 14 exponential, ATR 14 Wilder, 8 EMA, SMAs 10/20/50/200, MACD 12/26/9 exponential.

Outcome used everywhere unless noted ("drop first"): from the signal day's close, does price
fall 2 ATR before it rises 2 ATR within 20 trading days. A coin-flip setup scores about the
baseline rate. Every result is split into 2016-21 and 2022-26 so one lucky stretch can't pass.

Output: results/expanded/REPORT.md and results/expanded/by_sector.csv
"""
import os, time
import numpy as np, pandas as pd
import yfinance as yf

OUT = "results/expanded"; os.makedirs(OUT, exist_ok=True)
U = pd.read_csv("universe/expanded_universe.csv")


def pull(symbols):
    data = {}
    for i in range(0, len(symbols), 60):
        chunk = symbols[i:i + 60]
        for attempt in range(3):
            try:
                df = yf.download(chunk, period="11y", interval="1d", auto_adjust=False, group_by="ticker",
                                 threads=True, progress=False)
                break
            except Exception as e:
                print("retry", e); time.sleep(5)
        for s in chunk:
            try:
                x = df[s] if len(chunk) > 1 else df
                x = x.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
                x.columns = ["o", "h", "l", "c"]
                if len(x) > 300: data[s] = x
            except Exception:
                pass
        print(f"pulled {min(i + 60, len(symbols))}/{len(symbols)} | usable {len(data)}", flush=True)
    return data


def feats(x):
    c = x.c
    tr = pd.concat([x.h - x.l, (x.h - c.shift()).abs(), (x.l - c.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    x["e8"] = c.ewm(span=8, adjust=False).mean(); x["e10"] = c.ewm(span=10, adjust=False).mean()
    for n in (10, 20, 50, 200): x[f"s{n}"] = c.rolling(n).mean()
    d = c.diff(); g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean(); x["rsi"] = 100 - 100 / (1 + g / l)
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    x["macd"] = m; x["sig"] = m.ewm(span=9, adjust=False).mean()
    x["hh20"] = x.h.rolling(20).max(); x["r5"] = c.pct_change(5)
    return x


def race(h, l, c, a, e, k=2.0, days=20):
    ref = c[e]
    for j in range(e + 1, min(e + 1 + days, len(c))):
        dn = l[j] <= ref - k * a[e]; up = h[j] >= ref + k * a[e]
        if dn and up: return np.nan
        if dn: return 1.0
        if up: return 0.0
    return np.nan


def scan(sym, x, q):
    o, h, l, c = (x[k].values for k in "ohlc")
    A = x.atr.values; e8 = x.e8.values; e10 = x.e10.values; s10 = x.s10.values; s20 = x.s20.values
    s50 = x.s50.values; s200 = x.s200.values; R = x.rsi.values; M = x.macd.values; S = x.sig.values; hh20 = x.hh20.values
    qr5 = q.r5.reindex(x.index).values; r5 = x.r5.values
    G = c > o; Rd = c < o
    run = np.zeros(len(c), int)
    for i in range(1, len(c)): run[i] = run[i - 1] + 1 if h[i] < h[i - 1] else 0
    rows = []
    for e in range(260, len(c) - 21):
        tags = []
        if e % 5 == 0: tags.append("baseline")
        # pocket: 10 falling into the 200 (within 1.5 ATR), price between them; + sideways + 8 EMA tag
        if s10[e] > s200[e] and s10[e] - s200[e] <= 1.5 * A[e] and s10[e] < s10[e - 3] and s200[e] - 0.25 * A[e] <= c[e] < s10[e]:
            tags.append("pocket")
            if (h[e - 3:e + 1].max() - l[e - 3:e + 1].min()) <= 2 * A[e] and h[e] >= e8[e] > c[e]:
                tags.append("pocket+sideways+8EMA tag")
        # crosses
        for nm, f in (("10/20 cross", s10), ("8/20 cross", e8)):
            if f[e] < s20[e] and f[e - 1] >= s20[e - 1]: tags.append(nm)
        for nm, f in (("10/200 cross", s10), ("20/200 cross", s20), ("8/200 cross", e8)):
            if f[e] < s200[e] and f[e - 1] >= s200[e - 1]: tags.append(nm)
        # pre-cross state, first day
        pc = lambda i: c[i] < e8[i] and c[i] < s10[i] and s10[i] > s20[i] and s10[i] < s10[i - 1]
        if pc(e) and not pc(e - 1): tags.append("pre-cross (first day)")
        # MACD: cross down while above zero, near a 20-day high
        if M[e] < S[e] and M[e - 1] >= S[e - 1] and M[e] > 0 and (hh20[e] - h[e]) <= A[e]: tags.append("MACD cross down at top")
        # long staircase at a top: green, 4-5 reds with lower highs, green under the first green's high, RSI < 50
        if G[e]:
            for k in (4, 5):
                st = e - k - 1
                if G[st] and all(Rd[j] for j in range(st + 1, e)) and all(h[j + 1] < h[j] for j in range(st, e - 1)) \
                        and h[e] < h[st] and h[st] >= hh20[st] and R[e] < 50:
                    tags.append("long staircase at top, RSI<50"); break
        # staircase (3+ lower highs off a top), then a green higher high still under the top, RSI < 50
        if G[e] and run[e - 1] >= 3:
            st = e - 1 - run[e - 1]
            if h[st] >= hh20[st] and c[st] > s50[st] and h[e - 1] < h[e] < h[st] and R[e] < 50:
                tags.append("staircase, green higher high under top, RSI<50")
        # mechanical version of the setup grade
        pop = h[e] >= min(e8[e], s10[e]) and c[e] < max(e8[e], s10[e]) and c[e - 1] < max(e8[e - 1], s10[e - 1])
        hug = sum(abs(c[k] - s10[k]) <= 0.5 * A[k] for k in range(e - 4, e + 1)) >= 3
        score = 2 * (c[e] < e8[e]) + (e10[e] < s10[e]) + hug + (r5[e] < qr5[e] if np.isfinite(qr5[e]) else 0) + pop
        if score >= 5: tags.append("grade A/A- (mechanical)")
        elif score == 4: tags.append("grade B (mechanical)")
        if not tags: continue
        y = race(h, l, c, A, e)
        for t in tags:
            rows.append((sym, x.index[e], t, y, (c[e + 10] / c[e] - 1) * 100))
    return rows


def main():
    syms = U.symbol.tolist()
    data = pull(syms)
    q = feats(data["QQQ"].copy()) if "QQQ" in data else None
    allrows = []
    for i, (s, x) in enumerate(data.items()):
        try:
            allrows += scan(s, feats(x.copy()), q)
        except Exception as ex:
            print("skip", s, ex)
        if i % 100 == 0: print(f"scanned {i}/{len(data)}", flush=True)
    r = pd.DataFrame(allrows, columns=["sym", "date", "setup", "drop_first", "r10"])
    r = r.merge(U[["symbol", "industry", "sector_etf", "group"]], left_on="sym", right_on="symbol", how="left")
    r["era"] = np.where(r.date < "2022-01-01", "2016-21", "2022-26")
    r.to_csv(f"{OUT}/signals.csv.gz", index=False)

    base = r[r.setup == "baseline"]
    lines = ["# Expanded universe test (Taz's 75 + sector peers + liquid names)", "",
             f"Stocks with data: {r.sym.nunique()} | signal rows: {len(r):,}", "",
             "Drop first = price falls 2 ATR before rising 2 ATR within 20 days. Compare every row to the baseline.", "",
             "| Setup | Signals | Drop first | 2016-21 | 2022-26 | vs baseline | 10d median |", "|---|---|---|---|---|---|---|"]
    b = base.drop_first.mean()
    for s, g in r.groupby("setup"):
        gg = g.dropna(subset=["drop_first"])
        a = gg[gg.era == "2016-21"].drop_first.mean(); z = gg[gg.era == "2022-26"].drop_first.mean()
        p = gg.drop_first.mean(); se = np.sqrt(b * (1 - b) / max(len(gg), 1))
        lines.append(f"| {s} | {len(gg):,} | {p*100:.1f}% | {a*100:.1f}% | {z*100:.1f}% | {(p-b)*100:+.1f} pts (z {(p-b)/se:+.1f}) | {g.r10.median():+.2f}% |")
    lines += ["", "## Your 75 vs the peers", "", "| Setup | Your 75: drop first (n) | Peers: drop first (n) |", "|---|---|---|"]
    for s, g in r.groupby("setup"):
        gg = g.dropna(subset=["drop_first"]); m = gg[gg.group == "your 75"]; p = gg[gg.group == "peer"]
        lines.append(f"| {s} | {m.drop_first.mean()*100:.1f}% ({len(m):,}) | {p.drop_first.mean()*100:.1f}% ({len(p):,}) |")
    sec = (r.dropna(subset=["drop_first"]).groupby(["setup", "sector_etf"]).agg(n=("drop_first", "size"), drop_first=("drop_first", "mean"))
           .reset_index())
    bsec = base.dropna(subset=["drop_first"]).groupby("sector_etf").drop_first.mean().rename("sector_baseline")
    sec = sec.merge(bsec, on="sector_etf", how="left"); sec["edge_pts"] = (sec.drop_first - sec.sector_baseline) * 100
    sec.to_csv(f"{OUT}/by_sector.csv", index=False)
    lines += ["", "## Best setup by sector (100+ signals, vs that sector's own baseline)", "",
              "| Setup | Sector ETF | Signals | Drop first | Sector baseline | Edge |", "|---|---|---|---|---|---|"]
    top = sec[sec.n >= 100].sort_values("edge_pts", ascending=False).head(15)
    for t in top.itertuples():
        lines.append(f"| {t.setup} | {t.sector_etf} | {t.n:,} | {t.drop_first*100:.1f}% | {t.sector_baseline*100:.1f}% | {t.edge_pts:+.1f} pts |")
    open(f"{OUT}/REPORT.md", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
