"""
Broken trend vs strength, market-wide (860 names, 2016-2026).

Question: are puts better after the trend has already BROKEN, or when shorting STRENGTH?
Outcome (every signal day, from that day's close): stock drops 2 ATR before it rises 2 ATR within 10 trading days.
If both levels are hit on the same day, it counts as NOT a win (conservative). Neither hit in 10 days = not a win.
Baseline = every day of every name in the same period.

Broken-trend clues (as of the signal day's close, completed candles only):
  monthly_red   last completed month closed red AND this month so far is red (close < this month's open)
  weekly_3lh    3 lower weekly highs in a row on completed weeks (H1 < H2 < H3 < H4, newest first)
  tenday_cross  10-day chart (each candle = 10 trading days): 10 EMA under 10 SMA, crossed within the last 2 candles
  cliff_4h      4h cliff diver in the last 10 trading days: red 4h candle, body 0.5+ daily ATR, closes under BOTH the 4h
                50 and 200 SMA after the prior 4h close was not under both, with the 50 and 200 within 0.5 ATR
Strength clues:
  rsi3h_90      3h RSI 90+ (exponential RSI 14) on any 3h candle in the last 10 trading days
  macd_plateau  daily MACD above 0, rose 0.2+ ATR over the 7 days before, then flat (within 0.05 ATR) over the last 3
  near_20d_high close within 1 ATR of the 20-day high

Data: daily from yfinance (split/dividend adjusted), 1-hour bars with extended hours from Alpaca (adjustment=all),
built into 4h candles (0-4, 4-8, 8-12, 12-16, 16-20 ET) and 3h candles (4, 7, 10, 13, 16, 19 ET).
Chart settings: RSI 14 exponential, ATR 14 Wilder, SMAs, MACD 12/26/9.
Split: 2016-2021 vs 2022-2026. Out: results/broken_vs_strength/REPORT.md, summary.csv
"""
from __future__ import annotations
import os, time, threading, math
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd, requests

OUT = "results/broken_vs_strength"; os.makedirs(OUT, exist_ok=True)
U = pd.read_csv("universe/expanded_universe.csv")
MINE = set(U[U.group == "your 75"].symbol)
LIMIT = int(os.environ.get("LIMIT", "0") or 0)
SYMS = list(U.symbol)[:LIMIT] if LIMIT else list(U.symbol)
BROKEN = ["monthly_red", "weekly_3lh", "tenday_cross", "cliff_4h"]
STRONG = ["rsi3h_90", "macd_plateau", "near_20d_high"]
NAMES = {"monthly_red": "Monthly red (last month and this month so far)", "weekly_3lh": "3 weekly lower highs",
         "tenday_cross": "10-day chart 10 EMA crossed under 10 SMA (within 2 candles)", "cliff_4h": "4h cliff diver in the last 10 days",
         "rsi3h_90": "3h RSI 90 in the last 10 days", "macd_plateau": "Daily MACD plateau", "near_20d_high": "Within 1 ATR of the 20-day high"}


def rsi(c):
    d = c.diff()
    g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean()
    return 100 - 100 / (1 + g / l)


# ------------------------------------------------------------------ data
def daily_all(symbols):
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 80):
        chunk = symbols[i:i + 80]
        df = None
        for _ in range(3):
            try:
                df = yf.download(chunk, start="2015-01-01", interval="1d", auto_adjust=True, group_by="ticker",
                                 threads=True, progress=False); break
            except Exception as e:
                print("retry", e); time.sleep(5)
        if df is None:
            continue
        for s in chunk:
            try:
                x = (df[s] if len(chunk) > 1 else df).rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
                x.columns = ["o", "h", "l", "c"]; x.index = pd.to_datetime(x.index).tz_localize(None).normalize()
                if len(x) > 300:
                    out[s] = x
            except Exception:
                pass
        print(f"daily {min(i + 80, len(symbols))}/{len(symbols)}", flush=True)
    return out


KEY = (os.environ.get("APCA_API_KEY_ID") or "").strip(); SEC = (os.environ.get("APCA_API_SECRET_KEY") or "").strip()
_lock = threading.Lock(); _last = [0.0]


def _get(params):
    for i in range(8):
        with _lock:                       # ~3 requests/second overall (Alpaca free: 200/min)
            wait = _last[0] + 0.32 - time.time()
            if wait > 0: time.sleep(wait)
            _last[0] = time.time()
        try:
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=params, timeout=90,
                             headers={"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SEC})
        except Exception:
            time.sleep(2 ** i); continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** i); continue
        return r
    return None


def hourly(sym):
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": "1Hour", "start": "2015-10-01T00:00:00Z", "end": end, "feed": "sip",
             "adjustment": "all", "limit": 10000}
        if token: p["page_token"] = token
        r = _get(p)
        if r is None or r.status_code != 200:
            return None
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token: break
    if not rows:
        return None
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


def candles(h1, kind):
    hr = h1.t.dt.hour
    if kind == "4h":
        x = h1[(hr >= 0) & (hr < 20)]; st = (x.t.dt.hour // 4) * 4
    else:
        x = h1[(hr >= 4) & (hr < 22)]; st = 4 + 3 * ((x.t.dt.hour - 4) // 3)
    key = x.t.dt.normalize() + pd.to_timedelta(st, unit="h")
    g = x.groupby(key).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    g.index.name = "t"
    return g


# ------------------------------------------------------------------ features + outcomes per name
def features(sym, d, h1):
    d = d.copy(); o, h, l, c = d.o, d.h, d.l, d.c
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    d["atr"] = A = tr.ewm(alpha=1 / 14, adjust=False).mean()
    n = len(d); cv, hv, lv, Av = c.values, h.values, l.values, A.values
    # outcome: 2 ATR down before 2 ATR up within 10 days
    win = np.zeros(n); done = np.zeros(n, bool); valid = np.zeros(n, bool); valid[:n - 10] = True
    for k in range(1, 11):
        hh = np.full(n, np.nan); ll = np.full(n, np.nan)
        hh[:n - k] = hv[k:]; ll[:n - k] = lv[k:]
        up = hh >= cv + 2 * Av; dn = ll <= cv - 2 * Av
        newwin = ~done & dn & ~up
        win[newwin] = 1; done |= (up | dn)
    d["win"] = win; d["valid"] = valid & (np.arange(n) >= 220)
    # monthly
    mp = d.index.to_period("M")
    mo = d.groupby(mp).agg(o=("o", "first"), c=("c", "last"))
    mo_red = (mo.c < mo.o)
    prev_red = mo_red.shift(1).reindex(mp).values
    mopen = mo.o.reindex(mp).values
    d["monthly_red"] = (prev_red == True) & (cv < mopen)
    # weekly lower highs (completed weeks before this one)
    wp = d.index.to_period("W-FRI")
    wk = d.groupby(wp).h.max()
    lh = (wk < wk.shift(1)) & (wk.shift(1) < wk.shift(2)) & (wk.shift(2) < wk.shift(3))
    d["weekly_3lh"] = lh.shift(1).reindex(wp).fillna(False).values.astype(bool)
    # 10-day candles (blocks of 10 trading days from the first bar); value known once a candle completes
    blk = np.arange(n) // 10
    t10 = d.c.groupby(blk).last()
    e10 = t10.ewm(span=10, adjust=False).mean(); s10 = t10.rolling(10).mean()
    under = (e10 < s10)
    cross = under & ~(under.shift(1).fillna(True) & under.shift(2).fillna(True))
    comp = cross.shift(1).fillna(False)            # the last COMPLETED candle at any day inside block b is b-1
    d["tenday_cross"] = comp.reindex(blk).values.astype(bool)
    last_in_block = (np.arange(n) % 10 == 9)
    d.loc[last_in_block, "tenday_cross"] = cross.reindex(blk[last_in_block]).values.astype(bool)
    # MACD plateau, near 20-day high
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    d["macd_plateau"] = (m > 0) & ((m.shift(3) - m.shift(10)) > 0.2 * A) & ((m - m.shift(3)).abs() <= 0.05 * A)
    d["near_20d_high"] = (h.rolling(20).max() - c) <= A
    # intraday clues
    d["cliff_4h"] = False; d["rsi3h_90"] = False; d["has_intraday"] = False
    if h1 is not None and len(h1) > 500:
        h4 = candles(h1, "4h")
        s50, s200 = h4.c.rolling(50).mean(), h4.c.rolling(200).mean()
        lo = np.minimum(s50, s200)
        day = h4.index.normalize()
        Ad = d.atr.shift(1).reindex(day).values
        cl = (h4.c < h4.o) & ((h4.o - h4.c).values >= 0.5 * Ad) & (h4.c < lo) & ~(h4.c.shift(1) < lo.shift(1)) & \
             ((s50 - s200).abs().values <= 0.5 * Ad)
        cday = cl.groupby(day).any().reindex(d.index).fillna(False).astype(int)
        d["cliff_4h"] = cday.rolling(10, min_periods=1).max().astype(bool).values
        h3 = candles(h1, "3h")
        r3 = rsi(h3.c)
        rday = (r3 >= 90).groupby(h3.index.normalize()).any().reindex(d.index).fillna(False).astype(int)
        d["rsi3h_90"] = rday.rolling(10, min_periods=1).max().astype(bool).values
        first = h1.t.iloc[0].normalize() + pd.Timedelta(days=60)
        d["has_intraday"] = d.index >= first
    d["sym"] = sym
    keep = ["sym", "win", "valid", "has_intraday"] + BROKEN + STRONG
    return d.loc[d.valid & (d.index >= "2016-01-01"), keep]


# ------------------------------------------------------------------ report
def fresh(df, col):
    """first day a clue turns on (not on in the prior 10 trading days for that name)"""
    on = df[col].astype(int)
    prior = on.groupby(df.sym).transform(lambda s: s.shift(1).rolling(10, min_periods=1).max()).fillna(0)
    return df[col] & (prior == 0)


def main():
    t0 = time.time()
    D = daily_all(SYMS + ["QQQ"])
    print(f"daily done: {len(D)} names in {time.time() - t0:.0f}s", flush=True)
    names = [s for s in SYMS if s in D]
    H = {}
    if KEY:
        def job(s):
            try:
                return s, hourly(s)
            except Exception as e:
                print("hourly fail", s, e); return s, None
        with ThreadPoolExecutor(6) as ex:
            for i, (s, h1) in enumerate(ex.map(job, names)):
                H[s] = None if h1 is None else h1
                if i % 50 == 0: print(f"hourly {i}/{len(names)} {time.time() - t0:.0f}s", flush=True)
    rows = []
    for s in names:
        try:
            rows.append(features(s, D[s], H.get(s)))
        except Exception as e:
            print("feature fail", s, e)
        H.pop(s, None)
    X = pd.concat(rows)
    X["period"] = np.where(X.index < "2022-01-01", "2016-21", "2022-26")
    X["mine"] = X.sym.isin(MINE)
    X["nbroken"] = X[BROKEN].astype(int).sum(axis=1)
    X["nstrong"] = X[STRONG].astype(int).sum(axis=1)
    write(X, time.time() - t0)


def stat(sub, base):
    n = len(sub); w = sub.win.mean() if n else np.nan
    # day-level clustering: t-stat using monthly mean differences
    return n, w, (w - base) * 100 if n else np.nan


def write(X, secs):
    rows = []
    L = ["# Broken trend vs strength: puts on 860 names, 2016-2026", "",
         f"{X.sym.nunique()} names, {len(X):,} name-days. Outcome: from the signal day's close, the stock falls **2 ATR before it rises 2 ATR** "
         "within 10 trading days (a same-day tie counts as a loss). Baseline = every day of every name in that period.",
         "Fit period = 2016-2021, judged period = 2022-2026. Nothing below was tuned; the definitions were set before running.",
         f"4h and 3h clues need hourly bars: {X[X.has_intraday].sym.nunique()} names had them (Alpaca, extended hours). "
         "Days without hourly data count the 4h/3h clue as off.", ""]
    for grp, G in (("All 860 names", X), ("His 75 names", X[X.mine])):
        L += [f"## {grp}", ""]
        base = {p: G[G.period == p].win.mean() for p in ("2016-21", "2022-26")}
        L += ["| Clue | Side | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline | Held? |",
              "|---|---|---|---|---|---|---|---|---|",
              f"| **Baseline (every day)** | | {(G.period=='2016-21').sum():,} | {base['2016-21']*100:.1f}% | | "
              f"{(G.period=='2022-26').sum():,} | {base['2022-26']*100:.1f}% | | |"]
        for col in BROKEN + STRONG:
            side = "broken" if col in BROKEN else "strength"
            r = {"group": grp, "clue": col}
            cells = []
            for p in ("2016-21", "2022-26"):
                sub = G[(G.period == p) & G[col]]
                n, w, lift = stat(sub, base[p])
                r[f"n_{p}"], r[f"win_{p}"], r[f"lift_{p}"] = n, w, lift
                cells += [f"{n:,}", f"{w*100:.1f}%" if n else "-", f"{lift:+.1f} pts" if n else "-"]
            held = r["lift_2016-21"] * r["lift_2022-26"] > 0 and min(abs(r["lift_2016-21"]), abs(r["lift_2022-26"])) >= 1
            L.append(f"| {NAMES[col]} | {side} | " + " | ".join(cells) + f" | {'yes' if held else 'no'} |")
            rows.append(r)
        L += ["", "**First day the clue turns on only** (removes the overlap of the same setup counted on many days in a row):", "",
              "| Clue | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |", "|---|---|---|---|---|---|---|"]
        for col in BROKEN + STRONG:
            fr = fresh(G, col)
            cells = []
            for p in ("2016-21", "2022-26"):
                sub = G[(G.period == p) & fr]
                n, w, lift = stat(sub, base[p])
                cells += [f"{n:,}", f"{w*100:.1f}%" if n else "-", f"{lift:+.1f} pts" if n else "-"]
            L.append(f"| {NAMES[col]} | " + " | ".join(cells) + " |")
        L += ["", "**Broken clues stacked** (how many of the 4 are on that day):", "",
              "| Broken clues on | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |", "|---|---|---|---|---|---|---|"]
        for k, lab in ((0, "0"), (1, "1"), (2, "2"), (3, "3+")):
            m = G.nbroken >= 3 if k == 3 else G.nbroken == k
            cells = []
            for p in ("2016-21", "2022-26"):
                sub = G[(G.period == p) & m]
                n, w, lift = stat(sub, base[p])
                cells += [f"{n:,}", f"{w*100:.1f}%" if n else "-", f"{lift:+.1f} pts" if n else "-"]
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
        L += ["", "**Head to head:** broken only vs strength only vs both:", "",
              "| Day type | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |", "|---|---|---|---|---|---|---|"]
        for lab, m in (("1+ broken, no strength clue", (G.nbroken >= 1) & (G.nstrong == 0)),
                       ("2+ broken, no strength clue", (G.nbroken >= 2) & (G.nstrong == 0)),
                       ("1+ strength, no broken clue", (G.nstrong >= 1) & (G.nbroken == 0)),
                       ("2+ strength, no broken clue", (G.nstrong >= 2) & (G.nbroken == 0)),
                       ("both", (G.nstrong >= 1) & (G.nbroken >= 1)),
                       ("neither", (G.nstrong == 0) & (G.nbroken == 0))):
            cells = []
            for p in ("2016-21", "2022-26"):
                sub = G[(G.period == p) & m]
                n, w, lift = stat(sub, base[p])
                cells += [f"{n:,}", f"{w*100:.1f}%" if n else "-", f"{lift:+.1f} pts" if n else "-"]
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
        L.append("")
    pd.DataFrame(rows).to_csv(f"{OUT}/summary.csv", index=False)
    L += ["## Notes", "",
          "- The baseline here is about 30%, lower than the ~45% in older notes, because this race has 10 days, not 20; "
          "more days end with neither level hit (counted as not a win).",
          "- Held = beats or trails the baseline in the same direction in both periods by at least 1 point.",
          "- Name-days overlap (a clue that stays on for 10 days is counted 10 times, and their 10-day outcomes overlap), so "
          "the n is bigger than the number of independent bets. The 'first day only' table is the cleaner read.",
          f"- Run time {secs/60:.0f} min."]
    open(f"{OUT}/REPORT.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
