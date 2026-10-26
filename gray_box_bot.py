"""
Gray Box Fade bot (Taz's trade style from Oct 24, 2026). Two jobs, run after the close on weekdays:

  grade    Grade yesterday's top 10 on today's 5-minute bars. Post the scorecard. Append to results/gray_box/log.csv.
  nightly  Scan 200 stocks (Taz's 75 + the most liquid others) for gray boxes. Post the best 10 for the next session.
           Save the list to results/gray_box/lists/<date>.csv for tomorrow's grading.

Rules (unchanged from the study, claude/gray_box_fade_study.md in the Project):
  Box      gap between two daily candle bodies, trimmed by every later body, 120-session lookback.
  Setup    puts: nearest box above the close; calls: nearest box below. Box edge within 1.5 daily ranges (ATR 14).
  Arm      price must first trade 0.4 range away from the trigger (the real move in). Skip if it opens past the trigger.
  Trigger  a tenth of a range before the box edge.
  Exits    stop half a range past entry; half off after half a range (was a tenth, too small to pay on options); stop to entry; runner to three quarters
           of a range or out at the close.
Ranking (a hypothesis until live grading says otherwise): stock tier from the minute-bar test, box distance,
gap-through (extra weight on calls), stacked box edges.

Data: Yahoo via yfinance (free). Posts to the private channel first.
Local test: LOCAL_BARS=<stock_bars.csv> LOCAL_5M=<dir with SYM_5Min.csv> ASOF=YYYY-MM-DD python gray_box_bot.py nightly|grade
"""
import os, sys, time, glob, datetime as dt
import numpy as np, pandas as pd, requests

KS, K1, K2, TAG, POP, LOOKBACK, MAXDIST, N_UNI, N_TOP = 0.5, 0.5, 0.75, 0.1, 0.4, 120, 1.5, 200, 10
TIER = {"QQQ": 3, "PLTR": 3, "AMD": 2, "WMT": 2, "NVDA": 2, "TSLA": 1, "AAPL": 1, "META": 1}
SKIP = {"SPY", "AVGO", "MSFT", "UNH"}
OUT = "results/gray_box"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", ""); CH = os.environ.get("PRIVATE_CHANNEL_ID", "")
FORCE = os.environ.get("FORCE", "") == "1"
ET = dt.timezone(dt.timedelta(hours=-4))


# ------------------------------------------------------------------ data
def pull_daily(symbols):
    if os.environ.get("LOCAL_BARS"):
        b = pd.read_csv(os.environ["LOCAL_BARS"]).rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
        if os.environ.get("ASOF"): b = b[b.date <= os.environ["ASOF"]]
        out = {}
        for s, x in b[b.symbol.isin(symbols)].groupby("symbol"):
            x = x.sort_values("date"); x.index = pd.to_datetime(x.date); out[s] = x[["o", "h", "l", "c", "v"]]
        return out
    import yfinance as yf
    out = {}
    for i in range(0, len(symbols), 80):
        chunk = symbols[i:i + 80]; df = None
        for _ in range(3):
            try:
                df = yf.download(chunk, period="1y", interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False); break
            except Exception as e:
                print("retry", e); time.sleep(5)
        if df is None: continue
        for s in chunk:
            try:
                x = (df[s] if len(chunk) > 1 else df).rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna()
                x.columns = ["o", "h", "l", "c", "v"]
                if len(x) > 150: out[s] = x
            except Exception:
                pass
    return out


def pull_5m(symbols, day):
    out = {}
    if os.environ.get("LOCAL_5M"):
        for s in symbols:
            f = os.path.join(os.environ["LOCAL_5M"], f"{s}_5Min.csv")
            if not os.path.exists(f): continue
            m = pd.read_csv(f); m["t"] = pd.to_datetime(m.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
            out[s] = m.set_index("t")[["o", "h", "l", "c"]]
    else:
        import yfinance as yf
        for s in symbols:
            try:
                x = yf.download(s, period="5d", interval="5m", auto_adjust=False, progress=False, prepost=False)
                if isinstance(x.columns, pd.MultiIndex): x.columns = x.columns.get_level_values(0)
                x = x.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna(); x.columns = ["o", "h", "l", "c"]
                x.index = (x.index.tz_convert("America/New_York") if x.index.tz is not None else x.index).tz_localize(None)
                out[s] = x
            except Exception as e:
                print("5m fail", s, e)
    res = {}
    for s, x in out.items():
        x = x[(x.index.strftime("%Y-%m-%d") == day) & (x.index.hour * 60 + x.index.minute >= 570) & (x.index.hour < 16)]
        if len(x): res[s] = x
    return res


# ------------------------------------------------------------------ boxes
def trim(p, lo, hi):
    a, b = p[0], p[1]
    if hi <= a or lo >= b: return [p]
    out = []
    if lo > a: out.append((a, lo) + p[2:])
    if hi < b: out.append((hi, b) + p[2:])
    return [q for q in out if q[1] - q[0] > 1e-6]


def setups(sym, x):
    o, c, h, l = x.o.values, x.c.values, x.h.values, x.l.values
    pc = np.r_[np.nan, c[:-1]]
    A = pd.Series(np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))).rolling(14).mean().values[-1]
    bt = np.maximum(o, c); bb = np.minimum(o, c); pieces, filled = [], []
    dates = x.index.strftime("%Y-%m-%d")
    for i in range(1, len(x)):
        nxt = []
        for p in pieces:
            t = trim(p, bb[i], bt[i])
            if t: nxt += t
            else: filled.append(p)
        pieces = [p for p in nxt if i - p[2] <= LOOKBACK]; filled = [p for p in filled if i - p[2] <= LOOKBACK]
        if bb[i] > bt[i - 1]: pieces.append((bt[i - 1], bb[i], i, dates[i]))
        elif bt[i] < bb[i - 1]: pieces.append((bt[i], bb[i - 1], i, dates[i]))
    last = len(x) - 1; close = c[last]; out = []
    for put in (True, False):
        cand = [p for p in pieces if (p[0] > close if put else p[1] < close)]
        if not cand: continue
        lvl = min(p[0] for p in cand) if put else max(p[1] for p in cand)
        box = [p for p in cand if (p[0] if put else p[1]) == lvl][0]
        dist = abs(lvl - close) / A
        if dist > MAXDIST: continue
        s = 1 if put else -1; trig = lvl - s * TAG * A
        stack = sum(1 for p in cand if abs((p[0] if put else p[1]) - lvl) <= 0.25 * A)
        gt = any((c[k - 1] > lvl > o[k]) if put else (c[k - 1] < lvl < o[k]) for k in range(max(1, last - 9), last + 1))
        lv = sorted({round(p[0] if put else p[1], 2) for p in filled if (p[0] > close if put else p[1] < close) and abs((p[0] if put else p[1]) - close) / A <= MAXDIST})
        score = TIER.get(sym, 0) * 2 + (2 if dist <= 0.5 else 1 if dist <= 1.0 else 0) + (2 if (gt and not put) else 1 if gt else 0) + (1 if stack >= 2 else 0)
        out.append(dict(sym=sym, side="PUT" if put else "CALL", score=score, close=round(close, 2), atr=round(A, 2),
                        box_lo=round(box[0], 2), box_hi=round(box[1], 2), box_from=box[3], dist=round(dist, 2),
                        arm=round(trig - s * POP * A, 2), trigger=round(trig, 2), stop=round(trig + s * KS * A, 2),
                        half=round(trig - s * K1 * A, 2), runner=round(trig - s * K2 * A, 2),
                        gap_through=bool(gt), stack=stack, filled_levels=" ".join(map(str, lv[:3]))))
    return out


# ------------------------------------------------------------------ discord
def post(text):
    if not TOKEN or not CH: print(text); return
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > 1900: chunks.append(cur); cur = ""
        cur += line + "\n"
    chunks.append(cur)
    for ch in chunks:
        r = requests.post(f"https://discord.com/api/v10/channels/{CH}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                          json={"content": ch, "allowed_mentions": {"parse": []}}, timeout=20)
        print(f"::notice::discord post {r.status_code}"); time.sleep(1)


def universe(data):
    U = pd.read_csv("universe/expanded_universe.csv")
    mine = [s for s in U[U.group == "your 75"].symbol if s in data and s not in SKIP]
    dv = {s: float((x.c * x.v).tail(20).median()) for s, x in data.items() if s not in SKIP and s not in mine}
    rest = sorted(dv, key=dv.get, reverse=True)[:max(0, N_UNI - len(mine))]
    return mine + rest, set(mine)


def latest_ok(data):
    last = max(x.index[-1] for x in data.values()).date()
    today = dt.datetime.now(ET).date()
    if os.environ.get("ASOF") or FORCE: return last, True
    if last != today:
        print(f"::notice::Latest bar {last} is not today {today}. Nothing posted."); return last, False
    return last, True


# ------------------------------------------------------------------ jobs
def nightly():
    U = pd.read_csv("universe/expanded_universe.csv")
    data = pull_daily(sorted(set(U.symbol) | {"QQQ"}))
    last, ok = latest_ok(data)
    if not ok: return
    uni, mine = universe(data)
    rows = []
    for s in uni:
        x = data[s]
        if x.index[-1].date() != last or len(x) < 150: continue
        rows += setups(s, x)
    r = pd.DataFrame(rows)
    if r.empty: post(f"📦 Gray Box Fade: no setups within range for the next session ({last})."); return
    r = r.sort_values(["score", "dist"], ascending=[False, True]).reset_index(drop=True)
    top = r.head(N_TOP).copy(); top["rank"] = range(1, len(top) + 1); top["asof"] = str(last)
    os.makedirs(f"{OUT}/lists", exist_ok=True)
    top.to_csv(f"{OUT}/lists/{last}.csv", index=False); r.to_csv(f"{OUT}/candidates_latest.csv", index=False)
    L = [f"📦🌪️ **Gray Box Fade: best {len(top)} for the next session** (boxes as of {last:%a %b %d} close · {len(uni)} stocks scanned · {len(r)} setups found)", "",
         "Live only after price trades past the **arm** level, then tags the **trigger**. Skip if it opens past the trigger.", ""]
    for z in top.itertuples():
        note = []
        if z.gap_through: note.append("gap-through retest")
        if z.stack >= 2: note.append(f"{z.stack} box edges stacked")
        if z.filled_levels: note.append(f"filled levels {z.filled_levels}")
        icon = "🔻" if z.side == "PUT" else "🟢"
        L.append(f"{z.rank}. {icon} **{z.sym} {z.side}** · arm {'above' if z.side == 'CALL' else 'below'} {z.arm} · trigger **{z.trigger}** · stop {z.stop} · half {z.half} · runner {z.runner}")
        L.append(f"    box {z.box_lo}-{z.box_hi} ({z.box_from}) · {z.dist} range from close" + (f" · {', '.join(note)}" if note else ""))
    L += ["", "Expiry a week+ out · contracts under $500 (else a debit spread) · 2 losses = done.", "Graded after tomorrow's close. Pattern. Process. Paid. 🌪️🔴"]
    print(f"::notice::gray box: {len(r)} setups, top: " + ", ".join(f"{z.sym} {z.side}" for z in top.itertuples()))
    post("\n".join(L))


def walk(z, x):
    """Grade one setup on one session of 5m bars."""
    put = z.side == "PUT"
    if len(x) == 0: return "no data", "", np.nan
    o0 = x.o.iloc[0]
    if (o0 >= z.trigger) if put else (o0 <= z.trigger): return "skipped: opened past the trigger", "", np.nan
    armed = False; j = None
    for k, b in enumerate(x.itertuples()):
        if (b.l <= z.arm) if put else (b.h >= z.arm): armed = True
        if (b.h >= z.trigger) if put else (b.l <= z.trigger):
            if armed or ((b.l <= z.arm) if put else (b.h >= z.arm)): j = k; break
            return "tagged without arming: skipped", x.index[k].strftime("%H:%M"), np.nan
    if j is None: return ("armed, never triggered" if armed else "never armed"), "", np.nan
    E, stop, got1 = z.trigger, z.stop, False
    for b in list(x.itertuples())[j + 1:]:
        hs = (b.h >= stop) if put else (b.l <= stop)
        if not got1:
            if hs: return "STOPPED (full loss)", x.index[j].strftime("%H:%M"), -KS
            if (b.l <= z.half) if put else (b.h >= z.half):
                got1, stop = True, E
                if (b.l <= z.runner) if put else (b.h >= z.runner): return "HALF + RUNNER HIT", x.index[j].strftime("%H:%M"), (K1 + K2) / 2
            continue
        if hs: return "HALF, runner out at entry", x.index[j].strftime("%H:%M"), K1 / 2
        if (b.l <= z.runner) if put else (b.h >= z.runner): return "HALF + RUNNER HIT", x.index[j].strftime("%H:%M"), (K1 + K2) / 2
    mv = (E - x.c.iloc[-1]) / z.atr * (1 if put else -1)
    if got1: return "HALF, runner closed at the bell", x.index[j].strftime("%H:%M"), (K1 + mv) / 2
    return "TRIGGERED, closed at the bell", x.index[j].strftime("%H:%M"), mv


def grade():
    files = sorted(glob.glob(f"{OUT}/lists/*.csv"))
    if not files: print("no lists yet"); return
    today = os.environ.get("ASOF_GRADE") or dt.datetime.now(ET).strftime("%Y-%m-%d")
    lst = [f for f in files if os.path.basename(f)[:-4] < today]
    if not lst: print("no list before", today); return
    L0 = pd.read_csv(lst[-1])
    bars = pull_5m(sorted(L0.sym.unique()), today)
    if not bars and not FORCE:
        print(f"::notice::no 5m bars for {today}; nothing graded"); return
    rows = []
    for z in L0.itertuples():
        res, when, r = walk(z, bars.get(z.sym, pd.DataFrame(columns=["o", "h", "l", "c"])))
        rows.append(dict(day=today, asof=z.asof, rank=z.rank, sym=z.sym, side=z.side, trigger=z.trigger, stop=z.stop,
                         half=z.half, runner=z.runner, result=res, entry_time=when, result_range=None if r != r else round(r, 3)))
    g = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True); logf = f"{OUT}/log.csv"
    if os.path.exists(logf):
        old = pd.read_csv(logf); old = old[old.day != today]; g_all = pd.concat([old, g])
    else: g_all = g
    g_all.to_csv(logf, index=False)
    trig = g[g.result_range.notna()]
    L = [f"📊🌪️ **Gray Box Fade scorecard: {pd.Timestamp(today):%a %b %d}** (list from {L0["asof"].iloc[0]} close)", ""]
    for z in g.itertuples():
        icon = "✅" if "RUNNER HIT" in z.result or "HALF" in z.result else "❌" if "STOPPED" in z.result else "➖"
        L.append(f"{icon} {z.rank}. **{z.sym} {z.side}** · {z.result}" + (f" (entry {z.entry_time})" if z.entry_time else ""))
    hit = trig.result.str.contains("HALF").sum(); stp = trig.result.str.contains("STOPPED").sum()
    L += ["", f"Triggered {len(trig)} of {len(g)} · half off {hit} · stopped {stp}" + (f" · avg {trig.result_range.mean():+.2f} range" if len(trig) else "")]
    allt = g_all[g_all.result_range.notna()]
    if len(allt): L.append(f"Running total since start: {len(allt)} triggered · half off {allt.result.str.contains('HALF').sum()} · stopped {allt.result.str.contains('STOPPED').sum()} · avg {allt.result_range.mean():+.3f} range")
    L.append("Stock moves only, no option P&L. Pattern. Process. Paid. 🌪️🔴")
    post("\n".join(L))


if __name__ == "__main__":
    {"nightly": nightly, "grade": grade}[sys.argv[1] if len(sys.argv) > 1 else "nightly"]()
