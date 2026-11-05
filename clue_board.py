"""
Clue board: nightly, private channel. For each of his 75 names, the clues his own trades proved (HANDOFF.md):

BROKEN clues (his puts won more when the trend had already broken):
  monthly   last month's candle closed red AND this month so far is red (close under this month's open)
  weekly    3 lower weekly highs in a row on completed weeks
  10D       10-day chart (each candle = 10 trading days, the latest candle ends today): 10 EMA under the 10 SMA
  cliff     4h cliff diver in the last 10 trading days: red 4h candle, body 0.5+ daily ATR, closes under BOTH the 4h 50
            and 200 SMA after the prior 4h close was not under both, with the 50 and 200 within 0.5 ATR
STRENGTH warnings (his puts lost more shorting strength) = "don't short this":
  rsi90     3h RSI 90+ on any 3h candle in the last 10 trading days
  plateau   daily MACD above 0, rose 0.2+ ATR over the 7 days before, then flat (within 0.05 ATR) over the last 3
  20d high  close within 1 ATR of the 20-day high

Same definitions as broken_vs_strength.py. Chart settings: RSI 14 exponential, ATR 14 Wilder, SMAs, MACD 12/26/9.
Data: yfinance (free): daily bars, and 1-hour bars with extended hours built into 4h (0-4, 4-8, 8-12, 12-16, 16-20 ET)
and 3h (4, 7, 10, 13, 16, 19 ET) candles. Posts once per date. FORCE=1 reposts, DRY=1 prints only.
Out: results/clue_board/<date>.csv and results/clue_board/latest.md
"""
from __future__ import annotations
import os, time, datetime as dt
import numpy as np, pandas as pd, requests

OUT = "results/clue_board"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", ""); CH = os.environ.get("PRIVATE_CHANNEL_ID", "")
FORCE = os.environ.get("FORCE", "") == "1"; DRY = os.environ.get("DRY", "") == "1"
BROKEN = {"monthly": "monthly red", "weekly": "3 weekly lower highs", "tenday": "10D 10 EMA under 10 SMA", "cliff": "4h cliff diver"}
STRONG = {"rsi90": "3h RSI 90", "plateau": "MACD plateau", "high20": "near 20-day high"}


def rsi(c):
    d = c.diff()
    g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean()
    return 100 - 100 / (1 + g / l)


def _frame(df, s, multi):
    x = (df[s] if multi else df).rename(columns=str.lower)
    x = x[["open", "high", "low", "close"]].dropna()
    x.columns = ["o", "h", "l", "c"]
    return x


def pull(symbols, **kw):
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 40):
        chunk = symbols[i:i + 40]; df = None
        for _ in range(3):
            try:
                df = yf.download(chunk, group_by="ticker", threads=True, progress=False, auto_adjust=True, **kw); break
            except Exception as e:
                print("retry", e); time.sleep(5)
        if df is None: continue
        for s in chunk:
            try:
                x = _frame(df, s, len(chunk) > 1)
                if len(x): out[s] = x
            except Exception:
                pass
    return out


def candles(h1, kind):
    t = h1.index; hr = t.hour
    if kind == "4h":
        x = h1[(hr >= 0) & (hr < 20)]; st = (x.index.hour // 4) * 4
    else:
        x = h1[(hr >= 4) & (hr < 22)]; st = 4 + 3 * ((x.index.hour - 4) // 3)
    key = x.index.normalize() + pd.to_timedelta(st, unit="h")
    return x.groupby(key).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))


def clues(d, h1, today):
    """d: daily bars through today's close. h1: 1-hour bars (ET, tz-naive). Returns dict of booleans + info."""
    o, h, l, c = d.o, d.h, d.l, d.c
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    A = tr.ewm(alpha=1 / 14, adjust=False).mean()
    f = {"close": float(c.iloc[-1]), "atr": float(A.iloc[-1])}
    # monthly: last completed month red, and this month so far red
    mo = d.groupby(d.index.to_period("M")).agg(o=("o", "first"), c=("c", "last"))
    cur = today.to_period("M")
    f["monthly"] = bool(len(mo) >= 2 and mo.index[-1] == cur and mo.c.iloc[-2] < mo.o.iloc[-2] and c.iloc[-1] < mo.o.iloc[-1])
    # weekly: 3 lower highs on completed weeks (this week counts as completed after Friday's close)
    wk = d.groupby(d.index.to_period("W-FRI")).h.max()
    if today.to_period("W-FRI") == wk.index[-1] and today.weekday() != 4:
        wk = wk.iloc[:-1]
    wh = wk.values[-4:]
    f["weekly"] = bool(len(wh) == 4 and wh[3] < wh[2] < wh[1] < wh[0])
    # 10-day candles counted back from today, so the latest candle ends at today's close
    n = len(d); blk = (n - 1 - np.arange(n)) // 10
    t10 = c.groupby(blk).last().sort_index(ascending=False)       # oldest first
    e10 = t10.ewm(span=10, adjust=False).mean(); s10 = t10.rolling(10).mean()
    f["tenday"] = bool(e10.iloc[-1] < s10.iloc[-1])
    # MACD plateau, near the 20-day high
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    Ai = A.iloc[-1]
    f["plateau"] = bool(m.iloc[-1] > 0 and (m.iloc[-4] - m.iloc[-11]) > 0.2 * Ai and abs(m.iloc[-1] - m.iloc[-4]) <= 0.05 * Ai)
    f["high20"] = bool(h.tail(20).max() - c.iloc[-1] <= Ai)
    # intraday clues over the last 10 trading days
    f["cliff"] = False; f["rsi90"] = False; f["intraday"] = False
    if h1 is not None and len(h1) > 300:
        start10 = d.index[-10]
        h4 = candles(h1, "4h")
        s50, s200 = h4.c.rolling(50).mean(), h4.c.rolling(200).mean()
        lo = np.minimum(s50, s200)
        Ad = A.shift(1).reindex(h4.index.normalize()).values
        cl = (h4.c < h4.o) & ((h4.o - h4.c).values >= 0.5 * Ad) & (h4.c < lo) & ~(h4.c.shift(1) < lo.shift(1)) & \
             ((s50 - s200).abs().values <= 0.5 * Ad)
        f["cliff"] = bool(cl[h4.index >= start10].any())
        h3 = candles(h1, "3h")
        f["rsi90"] = bool((rsi(h3.c)[h3.index >= start10] >= 90).any())
        f["intraday"] = bool(s200.notna().iloc[-1])
    f["n_broken"] = sum(f[k] for k in BROKEN); f["n_strong"] = sum(f[k] for k in STRONG)
    return f


def post(text):
    if DRY or not TOKEN or not CH:
        print(text); return
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > 1900: chunks.append(cur); cur = ""
        cur += line + "\n"
    chunks.append(cur)
    for ch in chunks:
        r = requests.post(f"https://discord.com/api/v10/channels/{CH}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                          json={"content": ch, "allowed_mentions": {"parse": []}}, timeout=20)
        print(f"::notice::discord post {r.status_code}"); time.sleep(1)


def main():
    U = pd.read_csv("universe/expanded_universe.csv")
    names = sorted(U[U.group == "your 75"].symbol)
    D = pull(names, period="3y", interval="1d")
    if not D:
        print("::error::no daily data from Yahoo"); return
    last = max(x.index[-1] for x in D.values())
    last = pd.Timestamp(last).tz_localize(None).normalize() if pd.Timestamp(last).tzinfo else pd.Timestamp(last).normalize()
    now_et = pd.Timestamp(dt.datetime.now(dt.timezone.utc)).tz_convert("America/New_York").tz_localize(None)
    want = now_et.normalize() if now_et.hour >= 16 else now_et.normalize() - pd.Timedelta(days=1)
    while want.weekday() >= 5: want -= pd.Timedelta(days=1)       # last weekday session that has closed
    if last != want and not FORCE and not os.environ.get("ASOF"):
        print(f"::notice::latest daily bar {last.date()} is not the last closed session {want.date()}; nothing posted"); return
    os.makedirs(OUT, exist_ok=True)
    out_csv = f"{OUT}/{last.date()}.csv"
    if os.path.exists(out_csv) and not FORCE:
        print(f"::notice::board for {last.date()} already posted"); return
    H = pull(names, period="729d", interval="1h", prepost=True)
    rows = []
    for s in names:
        d = D.get(s)
        if d is None or len(d) < 120: continue
        d = d.copy(); d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        d = d[d.index <= last]
        if d.index[-1] != last: continue
        h1 = H.get(s)
        if h1 is not None:
            h1 = h1.copy()
            idx = pd.to_datetime(h1.index)
            h1.index = idx.tz_convert("America/New_York").tz_localize(None) if idx.tz is not None else idx
            h1 = h1[h1.index < last + pd.Timedelta(days=1)]
        try:
            f = clues(d, h1, last)
        except Exception as e:
            print("skip", s, e); continue
        rows.append({"sym": s, **f})
    B = pd.DataFrame(rows)
    B = B.sort_values(["n_broken", "n_strong", "sym"], ascending=[False, True, True]).reset_index(drop=True)
    B.insert(0, "date", str(last.date()))
    B.to_csv(out_csv, index=False)
    top = B[B.n_broken > 0].head(10)
    L = [f"🧩🌪️ **Clue board: {last:%a %b %d} close** ({len(B)} of your 75 checked, {int((B.n_broken > 0).sum())} with a broken clue)", ""]
    if not len(top):
        L.append("No name has a broken clue tonight.")
    for k, z in enumerate(top.itertuples(), 1):
        br = [BROKEN[c] for c in BROKEN if getattr(z, c)]
        st = [STRONG[c] for c in STRONG if getattr(z, c)]
        line = f"{k}. **{z.sym}** {'🔴' * z.n_broken} {z.n_broken} broken: {', '.join(br)}"
        if st: line += f" · ⚠️ don't short: {', '.join(st)}"
        L.append(line)
    flagged = B[(B.n_broken == 0) & (B.n_strong >= 2)].sym.tolist()
    if flagged:
        L += ["", f"⚠️ Strength, no broken clue (don't short): {', '.join(flagged[:15])}"]
    L += ["", "Legend: 🔴 = broken clue (monthly red = last month and this month red; 3 weekly lower highs; 10-day chart 10 EMA under 10 SMA; "
          "4h cliff diver in 10 days), his puts won more with these. ⚠️ = strength (3h RSI 90 in 10 days, MACD plateau, within 1 ATR of the "
          "20-day high), his puts lost more shorting these.", "Candidates, not signals. Pattern. Process. Paid. 🌪️🔴"]
    text = "\n".join(L)
    open(f"{OUT}/latest.md", "w").write(text + "\n")
    print(f"::notice::clue board: {len(B)} names, top: " + ", ".join(top.sym))
    post(text)


if __name__ == "__main__":
    main()
