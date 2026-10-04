"""
Tazmanian Trader — Setup Backtest (v1)
======================================
Tests Taz's two intraday put setups on real 5-minute bars across the universe.

  HOD   — price holds at the high of day, RSI diverges, rejection + MA cross
  SMA200— price holds under the 5-min 200 SMA, RSI diverges, rejection + MA
          cross, and the trigger bar closes under the 200

Approved definitions (Oct 3 2026; every number is a setting below):
  ceiling        HOD: within 0.3% of RTH high of day | SMA200: within 0.2% of 5m 200 SMA
  consolidation  the 12 bars before the trigger all close inside the ceiling zone
  divergence     price retests its high (last 6 bars vs the 18 before) but RSI(14)
                 peaks >= 3 points lower
  trigger        bar closes below prior bar's low AND below SMA10, RSI < its MA,
                 SMA10 crossed below SMA20 within the last 3 bars
  entry          trigger bar close (09:45-15:30 ET), first signal per name per day
  stop           5-min close above the 50 SMA. If entry is still ABOVE the 50, the
                 stop is a close above the setup high until price first closes
                 under the 50 (otherwise every HOD entry stops out instantly).
  targets        levels below entry: low of day, yesterday's low, yesterday's close
                 (gap fill), daily 8 SMA, hourly 50/100/200 SMA. T1 nearest, T2 next.
  management     half off at T1, stop on the rest moves to breakeven, rest off at T2,
                 anything left exits at 15:55. (Stock-move test, not option P&L yet.)

Indicators use extended-hours bars (matches Taz's TradingView charts, which show
pre/post market). Set EXTENDED=0 for regular-hours-only indicators.

Env:  ALPACA_API_KEY_ID, ALPACA_API_SECRET_KEY
Opt:  MONTHS (9), MAX_SYMBOLS (1000), SYMBOLS (comma list overrides universe),
      EXTENDED (1), CHUNK (40)
Out:  results/setup_backtest/{report.md, signals.csv}
"""
from __future__ import annotations
import os, sys, time, math
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import requests

DATA = "https://data.alpaca.markets/v2/stocks/bars"
NY = "America/New_York"

P = dict(
    HOD_ZONE=0.003, SMA_ZONE=0.002, CONSOL_BARS=12,
    DIV_RECENT=6, DIV_PRIOR=18, DIV_RSI_PTS=3.0, RETEST_TOL=0.001,
    CROSS_LOOKBACK=3, RSI_LEN=14, RSI_MA=14,
    ENTRY_START="09:45", ENTRY_END="15:30", EOD_EXIT="15:55",
    MIN_TARGET_GAP=0.001,
)
MONTHS = int(os.environ.get("MONTHS", 9))
MAX_SYMBOLS = int(os.environ.get("MAX_SYMBOLS", 1000))
EXTENDED = os.environ.get("EXTENDED", "1") == "1"
CHUNK = int(os.environ.get("CHUNK", 40))
OUT = "results/setup_backtest"


# ----------------------------------------------------------------- data
def _hdr():
    k = (os.environ.get("ALPACA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        sys.exit("Alpaca keys missing.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


def fetch(symbols, tf, start, end):
    rows, token = [], None
    while True:
        p = {"symbols": ",".join(symbols), "timeframe": tf, "start": start, "end": end,
             "feed": "sip", "adjustment": "split", "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get(DATA, headers=_hdr(), params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            raise RuntimeError(f"{tf} {r.status_code}: {r.text[:300]}")
        j = r.json()
        for sym, bars in (j.get("bars") or {}).items():
            for b in bars:
                rows.append((sym, b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]))
        token = j.get("next_page_token")
        if not token:
            break
    df = pd.DataFrame(rows, columns=["symbol", "t", "o", "h", "l", "c", "v"])
    if len(df):
        df["t"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert(NY)
    return df


# ----------------------------------------------------------------- indicators
def rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def prep_5m(b: pd.DataFrame) -> pd.DataFrame:
    b = b.sort_values("t").reset_index(drop=True)
    tod = b["t"].dt.strftime("%H:%M")
    b["rth"] = (tod >= "09:30") & (tod < "16:00")
    if not EXTENDED:
        b = b[b["rth"]].reset_index(drop=True)
    for n in (10, 20, 50, 200):
        b[f"sma{n}"] = b["c"].rolling(n).mean()
    b["rsi"] = rsi(b["c"], P["RSI_LEN"])
    b["rsima"] = b["rsi"].rolling(P["RSI_MA"]).mean()
    b["day"] = b["t"].dt.date
    b["tod"] = b["t"].dt.strftime("%H:%M")
    return b


# ----------------------------------------------------------------- signals
def signals_for_symbol(sym, b5, b1h, b1d):
    out = []
    if len(b5) < 300:
        return out
    b = prep_5m(b5)
    c, h, l = b["c"].values, b["h"].values, b["l"].values
    s10, s20, s50, s200 = (b[f"sma{n}"].values for n in (10, 20, 50, 200))
    r, rma = b["rsi"].values, b["rsima"].values
    cross_dn = (s10 < s20) & (np.roll(s10, 1) >= np.roll(s20, 1))

    # daily context: prior-day low/close, daily 8 SMA as of prior close
    d = b1d.sort_values("t").copy()
    d["day"] = d["t"].dt.date
    d["sma8"] = d["c"].rolling(8).mean()
    dctx = {row.day: (pl, pc, ps8) for row, pl, pc, ps8 in
            zip(d.itertuples(), d["l"].shift(), d["c"].shift(), d["sma8"].shift())}
    # hourly SMAs (completed hours only)
    hh = b1h.sort_values("t").copy()
    for n in (50, 100, 200):
        hh[f"h{n}"] = hh["c"].rolling(n).mean()
    hh["avail"] = hh["t"] + pd.Timedelta(hours=1)
    h_t = hh["avail"].values

    K, R, PR = P["CONSOL_BARS"], P["DIV_RECENT"], P["DIV_PRIOR"]
    for day, idx in b[b["rth"]].groupby("day").groups.items():
        idx = np.asarray(idx)
        if day not in dctx:
            continue
        hod_run = np.maximum.accumulate(h[idx])
        lod_run = np.minimum.accumulate(l[idx])
        fired = False
        for j in range(len(idx)):
            i = idx[j]
            tod = b["tod"].iat[i]
            if fired or tod < P["ENTRY_START"] or tod > P["ENTRY_END"]:
                continue
            if i < K + PR + 2 or j < K:
                continue
            # trigger
            if not (c[i] < l[i - 1] and c[i] < s10[i] and r[i] < rma[i]
                    and cross_dn[max(i - P["CROSS_LOOKBACK"] + 1, 0):i + 1].any()):
                continue
            # divergence (retest of high with weaker RSI)
            rec = slice(i - R, i); pri = slice(i - R - PR, i - R)
            if not (h[rec].max() >= h[pri].max() * (1 - P["RETEST_TOL"])
                    and r[rec].max() <= r[pri].max() - P["DIV_RSI_PTS"]):
                continue
            cons = idx[j - K:j]
            hod_prev = hod_run[j - 1]
            setup = None
            if (c[cons] >= hod_prev * (1 - P["HOD_ZONE"])).all():
                setup = "HOD"
            elif (not np.isnan(s200[i]) and c[i] < s200[i]
                  and (np.abs(c[cons] / s200[cons] - 1) <= P["SMA_ZONE"]).all()):
                setup = "SMA200"
            if setup is None:
                continue
            fired = True
            entry = c[i]
            pl, pc, ps8 = dctx[day]
            hk = np.searchsorted(h_t, b["t"].values[i], side="right") - 1
            levels = {"low_of_day": lod_run[j - 1] if j else np.nan,
                      "yday_low": pl, "gap_fill_yday_close": pc, "daily_sma8": ps8}
            if hk >= 0:
                for n in (50, 100, 200):
                    levels[f"hourly_sma{n}"] = hh[f"h{n}"].iat[hk]
            below = sorted([(v, k) for k, v in levels.items()
                            if v == v and v < entry * (1 - P["MIN_TARGET_GAP"])], reverse=True)
            t1 = below[0] if below else (np.nan, None)
            t2 = below[1] if len(below) > 1 else (np.nan, None)
            res = manage(b, idx, j, entry, t1[0], t2[0], s50,
                         setup_high=h[cons].max())
            out.append(dict(symbol=sym, date=str(day), time=tod, setup=setup,
                            entry=round(entry, 4), t1=t1[0], t1_name=t1[1],
                            t2=t2[0], t2_name=t2[1], **res))
    return out


def manage(b, idx, j, entry, t1, t2, s50, setup_high):
    c, h, l = b["c"].values, b["h"].values, b["l"].values
    tod = b["tod"].values
    left, pnl, hit1, hit2, how = 1.0, 0.0, False, False, "eod"
    below50 = c[idx[j]] < s50[idx[j]]
    stop_be = False
    mfe = 0.0
    for k in range(j + 1, len(idx)):
        i = idx[k]
        mfe = max(mfe, (entry - l[i]) / entry)
        if not hit1 and t1 == t1 and l[i] <= t1:
            hit1 = True; pnl += 0.5 * (entry - t1) / entry; left = 0.5; stop_be = True
        if hit1 and not hit2 and t2 == t2 and l[i] <= t2:
            hit2 = True; pnl += 0.5 * (entry - t2) / entry; left = 0.0; how = "t2"; break
        if c[i] < s50[i]:
            below50 = True
        stop = (c[i] > s50[i]) if below50 else (c[i] > setup_high)
        if stop_be and c[i] > entry:
            stop = True
        if stop:
            pnl += left * (entry - c[i]) / entry; left = 0.0
            how = "breakeven_stop" if stop_be else "stop_50sma" if below50 else "stop_setup_high"
            break
        if tod[i] >= P["EOD_EXIT"]:
            pnl += left * (entry - c[i]) / entry; left = 0.0; how = "eod"; break
    if left > 0:
        last = idx[-1]; pnl += left * (entry - c[last]) / entry
    return dict(ret=round(pnl, 5), exit=how, hit_t1=hit1, hit_t2=hit2, mfe=round(mfe, 5))


# ----------------------------------------------------------------- report
def stats(x):
    n = len(x)
    if n == 0:
        return dict(n=0)
    m, sd = x["ret"].mean(), x["ret"].std(ddof=1) if n > 1 else float("nan")
    return dict(n=n, win=(x["ret"] > 0).mean(), avg=m,
                t=m / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan"),
                t1=x["hit_t1"].mean(), t2=x["hit_t2"].mean(),
                stopped=x["exit"].str.startswith("stop").mean(), mfe=x["mfe"].mean())


def fmt(s):
    if s.get("n", 0) == 0:
        return "| 0 | | | | | | | |"
    return (f"| {s['n']} | {s['win']:.0%} | {s['avg']*100:+.2f}% | {s['t']:.2f} | "
            f"{s['t1']:.0%} | {s['t2']:.0%} | {s['stopped']:.0%} | {s['mfe']*100:.2f}% |")


HDR = ("| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | "
       "Stopped | Avg best move |\n|---|---|---|---|---|---|---|---|")


def report(df, start, end, n_syms, feed_note):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(f"{OUT}/signals.csv", index=False)
    L = [f"# Setup Backtest v1 — {start} to {end}",
         f"\nUniverse scanned: {n_syms} names, 5-min SIP bars. {feed_note}",
         "\nStock-move test only: tells whether the setup picks moves in the right "
         "direction and reaches its targets. Option P&L comes next.\n",
         "## All signals\n", HDR, fmt(stats(df))]
    for s in ("HOD", "SMA200"):
        L += [f"\n## {s}\n", HDR, fmt(stats(df[df.setup == s]))]
    if len(df):
        L += ["\n## By time of entry\n", "| Window " + HDR.split("\n")[0] + "\n|---" + HDR.split("\n")[1]]
        b = pd.cut(pd.to_datetime(df["time"], format="%H:%M").dt.hour * 60 +
                   pd.to_datetime(df["time"], format="%H:%M").dt.minute,
                   [0, 630, 720, 840, 960], labels=["09:45-10:30", "10:30-12:00", "12:00-14:00", "14:00-15:30"])
        for lab in b.cat.categories:
            L.append(f"| {lab} " + fmt(stats(df[b == lab])))
        L += ["\n## How trades ended\n"]
        for k, v in df["exit"].value_counts().items():
            L.append(f"- {k}: {v} ({v/len(df):.0%})")
        L += ["\n## Which level was T1\n"]
        for k, v in df["t1_name"].fillna("none below").value_counts().items():
            L.append(f"- {k}: {v}")
        g = df.groupby("symbol")["ret"].agg(["size", "mean"]).sort_values("size", ascending=False).head(25)
        L += ["\n## Most frequent names\n", "| Ticker | Signals | Avg |", "|---|---|---|"]
        for s, row in g.iterrows():
            L.append(f"| {s} | {int(row['size'])} | {row['mean']*100:+.2f}% |")
    L.append("\nPass bar before trusting any setup: t-stat ≥ 3 on enough signals "
             "(roughly 400+), then option P&L must confirm.")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[:12]))


# ----------------------------------------------------------------- main
def main():
    end_dt = datetime.now(timezone.utc) - timedelta(minutes=20)
    start_dt = end_dt - timedelta(days=int(MONTHS * 30.5))
    warm = start_dt - timedelta(days=60)   # warm-up for 200 SMA / hourly 200 / daily 8
    s, e, w = start_dt.date().isoformat(), end_dt.isoformat(), warm.date().isoformat()

    if os.environ.get("SYMBOLS"):
        syms = [x.strip().upper() for x in os.environ["SYMBOLS"].split(",") if x.strip()]
    else:
        u = pd.read_csv("universe/universe.csv")
        u = u[u["group"] != "gauge"].sort_values("avg_dollar_vol", ascending=False)
        syms = u["symbol"].head(MAX_SYMBOLS).tolist()
    print(f"Backtest {s} -> {e[:10]}, {len(syms)} symbols, extended={EXTENDED}")

    allsig = []
    for ci in range(0, len(syms), CHUNK):
        ch = syms[ci:ci + CHUNK]
        try:
            m5 = fetch(ch, "5Min", w, e)
            h1 = fetch(ch, "1Hour", (warm - timedelta(days=60)).date().isoformat(), e)
            d1 = fetch(ch, "1Day", (warm - timedelta(days=30)).date().isoformat(), e)
        except Exception as ex:
            print(f"  chunk {ci}: fetch failed: {ex}"); continue
        for sym in ch:
            try:
                sig = signals_for_symbol(sym, m5[m5.symbol == sym], h1[h1.symbol == sym],
                                         d1[d1.symbol == sym])
                allsig += [x for x in sig if x["date"] >= s]
            except Exception as ex:
                print(f"  {sym}: {ex}")
        print(f"  {min(ci + CHUNK, len(syms))}/{len(syms)} symbols, {len(allsig)} signals so far")
    df = pd.DataFrame(allsig)
    if df.empty:
        df = pd.DataFrame(columns=["symbol", "date", "time", "setup", "entry", "t1", "t1_name",
                                   "t2", "t2_name", "ret", "exit", "hit_t1", "hit_t2", "mfe"])
    report(df, s, e[:10], len(syms), f"Extended-hours indicators: {EXTENDED}.")


if __name__ == "__main__":
    main()
