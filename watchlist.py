"""
Tazmanian watchlist bot. One bot, two posts a day. Replaces the options-bot readout, Gray Box, nightly scan and morning brief posts.

  python watchlist.py evening   after the close: grade the open names from earlier lists, then post tomorrow's list (max 5)
  python watchlist.py morning   9:15 AM: the same names with the pre-market price and LIVE / WAIT / SKIP

Every name has a reason, a trigger, a stop and a target, and gets graded on the next sessions (up to 5).
Only setups that held up on data the rules never saw are used (puts side):
  STAIR  staircase off a top (3+ lower highs), then a green higher high still under the top, RSI < 50
         860 stocks: 48.8% vs 45.0% normal (2 ATR down before 2 ATR up, 20 days). Your 75 names: 53%.
         Star: RSI < 40 and QQQ down over 5 days, 54.4% on 2022-26.
  LONG   long staircase at a top: green, 4-5 red lower-high candles, green under the first green, RSI < 50. 49% vs 45%.
         Star: closed under its 50 SMA, 54.3% on 2022-26.
  LAG    (your 75 names only, where it was tested) lagging at the top: QQQ up over 5 days, the stock 2%+ weaker, under its daily 8 EMA, within 1 ATR of its 20-day high.
         75 stocks 2016-26: 52.1% vs 46.0% normal (1.5 ATR down before 1.5 ATR up, 5 days), held in both 2016-21 and 2022-26.
Levels:
  STAIR / LONG  trigger = a trade under the setup day's low; stop = a daily close over the top, or 2 ATR over the setup close if the
                top is farther (the study's own 2 ATR race); target = 2 ATR under the setup close
  LAG           entry = the open, or a pop back to the setup close; stop = 1.5 ATR over the setup close; target = 1.5 ATR under it

Data: Alpaca free plan (SIP daily bars, 15 minutes delayed; IEX snapshots for pre-market). Posts with the Discord bot token.
Local test: LOCAL_DAILY=<dir of SYM.parquet> ASOF=YYYY-MM-DD DRY=1 python watchlist.py evening
"""
import os, sys, json, time, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np, pandas as pd, requests

ET = ZoneInfo("America/New_York")
OUT = "results/watchlist"; LISTS = f"{OUT}/lists.csv"; GRADES = f"{OUT}/grades.csv"
U = pd.read_csv("universe/expanded_universe.csv")
MINE = set(U[U.group == "your 75"].symbol)
KEY = (os.environ.get("APCA_API_KEY_ID") or "").strip(); SEC = (os.environ.get("APCA_API_SECRET_KEY") or "").strip()
H = {"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SEC}
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
CHANNELS = {"private": "1562327911866830949", "vip": "1412516610845184123"}
WHERE = (os.environ.get("WHERE") or "private").strip().lower()
DRY = os.environ.get("DRY") == "1"
FORCE = os.environ.get("FORCE") == "1"
MAX_NAMES, HOLD_DAYS = 5, 5
STATS = {
    "STAIR": "860 stocks 2016-26: 48.8% vs 45% normal · your names 53%",
    "STAIR*": "⭐ version: 54.4% on 2022-26",
    "LONG": "860 stocks: 49% vs 45% normal · your names 53%",
    "LONG*": "⭐ version: 54.3% on 2022-26",
    "LAG": "your 75 names 2016-26: 52.1% vs 46% normal, held in both halves",
}
NAMES = {"STAIR": "Staircase off a top, green higher high under the top", "LONG": "Long staircase at a top",
         "LAG": "Lagging at the top while QQQ runs"}


# ------------------------------------------------------------------ data
def now_et():
    return dt.datetime.now(ET)


def alpaca_daily(symbols, days=420):
    end = now_et() - dt.timedelta(minutes=16)
    start = end - dt.timedelta(days=days)
    out = {}
    for i in range(0, len(symbols), 100):
        chunk = symbols[i:i + 100]; token = None
        while True:
            p = {"symbols": ",".join(chunk), "timeframe": "1Day", "start": start.isoformat(), "end": end.isoformat(),
                 "feed": "sip", "adjustment": "raw", "limit": 10000}
            if token: p["page_token"] = token
            for attempt in range(4):
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=60)
                if r.status_code == 200: break
                time.sleep(3 * (attempt + 1))
            r.raise_for_status(); js = r.json()
            for s, bl in (js.get("bars") or {}).items():
                out.setdefault(s, []).extend(bl)
            token = js.get("next_page_token")
            if not token: break
    data = {}
    for s, bl in out.items():
        x = pd.DataFrame(bl)
        x.index = pd.to_datetime(x.t).dt.tz_convert(ET).dt.tz_localize(None).dt.normalize()
        x = x[["o", "h", "l", "c"]].astype(float)
        x = x[~x.index.duplicated(keep="last")].sort_index()
        if len(x) >= 120: data[s] = x
    return data


def local_daily(symbols):
    asof = os.environ.get("ASOF")
    data = {}
    for s in symbols:
        f = os.path.join(os.environ["LOCAL_DAILY"], f"{s}.parquet")
        if not os.path.exists(f): continue
        x = pd.read_parquet(f).sort_values("t"); x.index = pd.to_datetime(x.t).dt.normalize()
        x = x[["o", "h", "l", "c"]].astype(float)
        if asof: x = x[x.index <= asof]
        if len(x) >= 120: data[s] = x
    return data


def get_daily(symbols):
    return local_daily(symbols) if os.environ.get("LOCAL_DAILY") else alpaca_daily(symbols)


def snapshots(symbols):
    out = {}
    for i in range(0, len(symbols), 100):
        r = requests.get("https://data.alpaca.markets/v2/stocks/snapshots", headers=H,
                         params={"symbols": ",".join(symbols[i:i + 100]), "feed": "iex"}, timeout=30)
        if r.status_code != 200: continue
        js = r.json(); js = js.get("snapshots", js)
        for s, snap in (js or {}).items():
            t = (snap or {}).get("latestTrade") or {}
            if t.get("p"):
                ts = pd.Timestamp(t["t"]).tz_convert(ET)
                out[s] = (float(t["p"]), ts.date() == now_et().date())
    return out


# ------------------------------------------------------------------ indicators (Taz's chart settings)
def ind(x):
    x = x.copy(); c = x.c
    tr = pd.concat([x.h - x.l, (x.h - c.shift()).abs(), (x.l - c.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    x["e8"] = c.ewm(span=8, adjust=False).mean(); x["e10"] = c.ewm(span=10, adjust=False).mean()
    for n in (10, 20, 50): x[f"s{n}"] = c.rolling(n).mean()
    d = c.diff(); g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean()
    l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean()
    x["rsi"] = 100 - 100 / (1 + g / l); x["hh20"] = x.h.rolling(20).max(); x["r5"] = c.pct_change(5)
    return x


def grade(x, q):
    """Same math as the trade bot's `grade` command (puts)."""
    i = len(x) - 1; c, h, e8, s10, e10, A = x.c.values, x.h.values, x.e8.values, x.s10.values, x.e10.values, x.atr.values
    pts = 2 * int(c[i] < e8[i])
    pts += int(h[i] >= min(e8[i], s10[i]) and c[i] < max(e8[i], s10[i]) and c[i - 1] < max(e8[i - 1], s10[i - 1]))
    pts += int(sum(abs(c[k] - s10[k]) <= 0.5 * A[k] for k in range(i - 4, i + 1)) >= 3)
    pts += int(e10[i] < s10[i])
    if x.index[i] in q.index: pts += int(x.r5.iloc[i] < q.r5.loc[x.index[i]])
    return pts, ("A" if pts >= 6 else "A-" if pts == 5 else "B" if pts == 4 else "C" if pts == 3 else "D")


# ------------------------------------------------------------------ setups
def find(sym, x, q):
    i = len(x) - 1; o, h, l, c = x.o.values, x.h.values, x.l.values, x.c.values
    A, R, s50, e8, hh20 = x.atr.values[i], x.rsi.values, x.s50.values, x.e8.values, x.hh20.values
    G = c > o; Rd = c < o
    q5 = q.r5.loc[x.index[i]] if x.index[i] in q.index else np.nan
    hits = []
    run = 0
    for k in range(i - 1, 0, -1):
        if h[k] < h[k - 1]: run += 1
        else: break
    if G[i] and run >= 3:
        st = i - 1 - run
        if h[st] >= hh20[st] and c[st] > s50[st] and h[i - 1] < h[i] < h[st] and R[i] < 50:
            star = bool(R[i] < 40 and q5 < 0)
            hits.append(dict(setup="STAIR", star=star, trigger=l[i], stop=min(h[st], c[i] + 2 * A), top=h[st], target=c[i] - 2 * A,
                             why=f"{run} lower highs off the {h[st]:.2f} top, green higher high today still under it, RSI {R[i]:.0f}"))
    if G[i]:
        for k in (4, 5):
            st = i - k - 1
            if G[st] and all(Rd[j] for j in range(st + 1, i)) and all(h[j + 1] < h[j] for j in range(st, i - 1)) \
                    and h[i] < h[st] and h[st] >= hh20[st] and R[i] < 50:
                star = bool(c[i] < s50[i])
                hits.append(dict(setup="LONG", star=star, trigger=l[i], stop=min(h[st], c[i] + 2 * A), top=h[st], target=c[i] - 2 * A,
                                 why=f"green top {h[st]:.2f}, {k} red lower highs, green today under the top, RSI {R[i]:.0f}"))
                break
    r5 = x.r5.values[i]
    if sym in MINE and q5 > 0 and r5 - q5 <= -0.02 and c[i] < e8[i] and (hh20[i] - h[i]) <= A:
        hits.append(dict(setup="LAG", star=False, trigger=c[i], stop=c[i] + 1.5 * A, target=c[i] - 1.5 * A,
                         why=f"QQQ {q5*100:+.1f}% over 5 days, {sym} {r5*100:+.1f}%, under its 8 EMA {e8[i]:.2f}, "
                             f"{hh20[i]-h[i]:.2f} from its 20-day high"))
    for hh in hits:
        hh.update(sym=sym, close=c[i], atr=A)
    return hits


# ------------------------------------------------------------------ grading
def grade_item(it, x):
    """Walk the sessions after the list date. Returns (status, detail, done)."""
    d0 = pd.Timestamp(it["list_date"]); fut = x[x.index > d0].iloc[:HOLD_DAYS]
    if not len(fut): return "open", "not traded yet", False
    trig, stop, tgt = it["trigger"], it["stop"], it["target"]
    entered = None
    for k, (t, r) in enumerate(fut.iterrows(), 1):
        day = f"{t:%a %m/%d}"
        if it["setup"] == "LAG":
            if entered is None:
                entered = r.o
                if r.o >= stop: return "skip", f"opened {r.o:.2f}, over the stop", True
                if r.o <= tgt: return "skip", f"opened {r.o:.2f}, already past the target", True
            if r.h >= stop: return "stop", f"stopped {day} at {stop:.2f} (in at the {entered:.2f} open)", True
            if r.l <= tgt: return "target", f"target {tgt:.2f} hit {day} (in at the {entered:.2f} open)", True
        else:
            if entered is None:
                if r.o >= stop: return "skip", f"opened {r.o:.2f}, over the stop", True
                if r.l < trig:
                    entered = min(r.o, trig)
                    if r.l <= tgt: return "target", f"triggered and hit target {tgt:.2f} {day}", True
                    if r.c > stop: return "stop", f"triggered, then closed over the stop {stop:.2f} {day}", True
                    continue
                if k == len(fut) and len(fut) == HOLD_DAYS: return "none", f"never broke {trig:.2f} in {HOLD_DAYS} days", True
                continue
            if r.l <= tgt: return "target", f"target {tgt:.2f} hit {day} (in at {entered:.2f})", True
            if r.c > stop: return "stop", f"closed over the stop {stop:.2f} {day}", True
    last = fut.iloc[-1]
    if entered is None:
        return "open", f"not triggered yet (low {fut.l.min():.2f}, trigger {trig:.2f})", len(fut) >= HOLD_DAYS
    chg = (last.c / entered - 1) * 100
    if len(fut) >= HOLD_DAYS:
        return "expired", (f"no target or stop in {HOLD_DAYS} days, closed {last.c:.2f}, stock {chg:+.1f}% from the {entered:.2f} entry "
                           f"({'good' if chg < 0 else 'bad'} for puts)"), True
    return "open", f"in at {entered:.2f}, now {last.c:.2f} (day {len(fut)} of {HOLD_DAYS})", False


ICON = {"target": "✅", "stop": "❌", "skip": "🚫", "none": "➖", "expired": "⌛", "open": "⏳"}


# ------------------------------------------------------------------ posting
def post(text):
    if DRY or not TOKEN:
        print("----- POST -----\n" + text); return
    ch = CHANNELS.get(WHERE, CHANNELS["private"])
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > 1900: parts.append(cur); cur = ""
        cur += line + "\n"
    if cur.strip(): parts.append(cur)
    for p in parts:
        r = requests.post(f"https://discord.com/api/v10/channels/{ch}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                          json={"content": p, "allowed_mentions": {"parse": []}}, timeout=20)
        print("discord", r.status_code); time.sleep(1)


def read_csv(p):
    try:
        return pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 0 else pd.DataFrame()
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def fmt_item(n, it):
    star = "⭐ " if it["star"] else ""
    lines = [f"**{n}. {star}🔴 {it['sym']} PUTS** · {it['close']:.2f} · daily grade **{it['letter']}** ({it['pts']}/6)"
             + (" · your name" if it["sym"] in MINE else ""),
             f"   Why: {NAMES[it['setup']]}. {it['why']}"]
    if it["setup"] == "LAG":
        lines.append(f"   Entry: the open, or a pop back to **{it['trigger']:.2f}**")
        lines.append(f"   Stop: **{it['stop']:.2f}** (1.5 ATR) · Target: **{it['target']:.2f}** (1.5 ATR) · 5 days max")
    else:
        lines.append(f"   Trigger: a break under **{it['trigger']:.2f}** (today's low)")
        where = "the top" if it["stop"] >= it.get("top", it["stop"]) - 0.005 else f"2 ATR, the {it['top']:.2f} top is too far"
        lines.append(f"   Stop: a close over **{it['stop']:.2f}** ({where}) · Target: **{it['target']:.2f}** (2 ATR) · 5 days max")
    lines.append(f"   Odds: {STATS[it['setup'] + ('*' if it['star'] else '')] if it['star'] else STATS[it['setup']]}")
    return "\n".join(lines)


# ------------------------------------------------------------------ jobs
def evening():
    os.makedirs(OUT, exist_ok=True)
    syms = sorted(set(U.symbol) | {"QQQ"})
    data = get_daily(syms)
    if "QQQ" not in data: print("No QQQ data. Nothing posted."); return
    q = ind(data["QQQ"]); last = q.index[-1]
    today = pd.Timestamp(os.environ["ASOF"]) if os.environ.get("ASOF") else pd.Timestamp(now_et().date())
    if last != today and not FORCE:
        print(f"Latest bar {last.date()} is not today {today.date()} (holiday, weekend or too early). Nothing posted."); return
    lists = read_csv(LISTS)
    if len(lists) and str(last.date()) in set(lists.list_date) and not FORCE:
        print(f"Already posted the list for {last.date()}. Nothing posted."); return

    # 1) grade every name still open
    grades = read_csv(GRADES); done_keys = set(grades.key) if len(grades) else set()
    report_new, report_open = [], []
    if len(lists):
        prev_date = lists.list_date.max()
        for _, it in lists.iterrows():
            key = f"{it.list_date}|{it.sym}|{it.setup}"
            if key in done_keys or it.sym not in data: continue
            st, detail, done = grade_item(it, data[it.sym])
            line = f"{ICON[st]} {it.sym} {it.setup.lower()} ({pd.Timestamp(it.list_date):%m/%d}): {detail}"
            if done:
                grades = pd.concat([grades, pd.DataFrame([dict(key=key, list_date=it.list_date, sym=it.sym, setup=it.setup,
                                                               star=it.star, status=st, detail=detail, graded=str(last.date()))])])
                report_new.append(line)
            else:
                (report_new if it.list_date == prev_date else report_open).append(line)
        if len(grades): grades.to_csv(GRADES, index=False)

    # 2) tomorrow's list
    hits = []
    for s, x in data.items():
        if s == "QQQ" or x.index[-1] != last: continue
        x = ind(x)
        for hh in find(s, x, q):
            hh["pts"], hh["letter"] = grade(x, q); hits.append(hh)
    order = {"STAIR": 0, "LONG": 1, "LAG": 2}
    hits.sort(key=lambda z: (not z["star"], -z["pts"], z["sym"] not in MINE, order[z["setup"]], z["sym"]))
    seen, picks = set(), []
    for hh in hits:
        if hh["sym"] in seen: continue
        seen.add(hh["sym"]); picks.append(hh)
        if len(picks) == MAX_NAMES: break
    new = pd.DataFrame([dict(list_date=str(last.date()), sym=p["sym"], setup=p["setup"], star=p["star"], trigger=round(p["trigger"], 2),
                             stop=round(p["stop"], 2), target=round(p["target"], 2), close=round(p["close"], 2),
                             atr=round(p["atr"], 2), grade=p["letter"], pts=p["pts"]) for p in picks])
    if not len(new):
        new = pd.DataFrame([dict(list_date=str(last.date()), sym="NONE", setup="NONE", star=False, trigger=0, stop=0, target=0,
                                 close=0, atr=0, grade="", pts=0)])
    lists = pd.concat([lists, new]) if len(lists) else new
    lists.to_csv(LISTS, index=False)

    # 3) post
    q5 = q.r5.iloc[-1] * 100
    L = [f"🌙🌪️ **WATCHLIST · {last:%a %b %d} close** · QQQ {q.c.iloc[-1]:.2f} ({q5:+.1f}% over 5 days)", ""]
    real_new = [r for r in report_new if not r.split(" ", 2)[1] == "NONE"]
    if real_new or report_open:
        L.append("📊 **HOW THE LAST LISTS DID**")
        L += real_new or ["(nothing finished today)"]
        if report_open: L += ["", "⏳ **Still open**"] + report_open
        L.append("")
    L.append(f"🎯 **NEXT SESSION** · {len(picks)} name{'s' if len(picks) != 1 else ''} out of {len(hits)} setups found in {len(data)} stocks")
    if picks:
        for n, p in enumerate(picks, 1): L += ["", fmt_item(n, p)]
    else:
        L.append("Nothing clean tomorrow. No setup, no trade. 🚫")
    L += ["", "Puts side only. Expirations a week or more out. Stop set at entry. 2 losses = done.",
          "Pre-market check at 9:15 AM: LIVE / WAIT / SKIP for each name.", "", "Pattern. Process. Paid. 🌪️🔴"]
    post("\n".join(L))


def morning():
    lists = read_csv(LISTS)
    if not len(lists): print("No list yet."); return
    d = lists.list_date.max(); cur = lists[(lists.list_date == d) & (lists.sym != "NONE")]
    today = now_et().date()
    if str(today) <= d: print(f"Latest list is from {d}, today is {today}: nothing to check."); return
    if not len(cur): print("Last list had no names. Nothing posted."); return
    px = snapshots(list(cur.sym) + ["QQQ", "SPY"])
    if not any(live for _, live in px.values()) and not FORCE:
        print("No trades yet today (holiday or too early). Nothing posted."); return
    qn = px.get("QQQ")
    L = [f"☀️🌪️ **PRE-MARKET CHECK · {now_et():%a %b %d, %I:%M %p} ET** (IEX prices, thin before the open)"]
    if qn: L[0] += f" · QQQ {qn[0]:.2f}"
    L.append("")
    for _, it in cur.iterrows():
        p = px.get(it.sym)
        if not p: L.append(f"❔ **{it.sym}**: no price yet"); continue
        price = p[0]; g = (price / it.close - 1) * 100
        if price >= it.stop: tag, why = "🚫 **SKIP**", f"over the stop {it.stop:.2f}"
        elif price <= it.target: tag, why = "🚫 **SKIP**", f"already past the target {it.target:.2f}"
        elif it.setup == "LAG":
            tag, why = ("✅ **LIVE**", f"under {it.trigger:.2f}, sell the open") if price <= it.trigger else \
                       ("✅ **LIVE**", f"over {it.trigger:.2f}, sell a fade back under it")
        else:
            tag, why = ("✅ **LIVE**", f"already under the trigger {it.trigger:.2f}") if price < it.trigger else \
                       ("⏳ **WAIT**", f"needs a break under {it.trigger:.2f}")
        L.append(f"{tag} **{it.sym}** {price:.2f} ({g:+.1f}% vs close): {why} · stop {it.stop:.2f} · target {it.target:.2f}")
    L += ["", "No chasing 9:30. Stop set at entry. Pattern. Process. Paid. 🌪️🔴"]
    post("\n".join(L))


if __name__ == "__main__":
    {"evening": evening, "morning": morning}[sys.argv[1]]()
