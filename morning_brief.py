"""
Morning Discord posts (weekdays, about 8:00 AM ET). All data sources are free.

  Post 1  Good morning briefing: futures and key markets, today's US economic calendar (high and medium impact),
          Fed speakers and FOMC items, Trump's public schedule, and today's earnings (before the open / after the close).
  Post 2  Trade ideas: the Gray Box Fade top setups from last night's list, checked against pre-market prices
          (still in play, close to arming, or already past the trigger and skipped).

Sources: ForexFactory weekly calendar JSON (economic events and Fed speakers), Nasdaq earnings calendar API,
Roll Call Factba.se calendar JSON (Trump schedule), Yahoo via yfinance (futures and pre-market prices).
Every source is optional: if one fails, the post says so instead of guessing.

Env: DISCORD_BOT_TOKEN, WHERE (private | vip), DATE (YYYY-MM-DD, for testing), FORCE=1 (skip the 8 AM clock check),
     DRY=1 (print instead of posting)
"""
import os, glob, json, time, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd, requests

NY = ZoneInfo("America/New_York")
NOW = dt.datetime.now(NY)
DAY = dt.date.fromisoformat(os.environ["DATE"]) if os.environ.get("DATE") else NOW.date()
CH = {"vip": "1412516610845184123", "private": "1562327911866830949"}[os.environ.get("WHERE", "private") or "private"]
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}
U = pd.read_csv("universe/expanded_universe.csv")
MINE = set(U[U.group == "your 75"].symbol)
WATCH = MINE | set(U.symbol)
notes = []


def get(url, **kw):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=25, **kw)
            if r.status_code == 200: return r
            notes.append(f"{url.split('/')[2]} {r.status_code}")
        except Exception as e:
            notes.append(f"{url.split('/')[2]} {type(e).__name__}")
        time.sleep(2 + 2 * i)
    return None


# ------------------------------------------------------------------ calendar + Fed
def econ():
    events, loaded = [], 0
    for wk in ("thisweek", "nextweek"):
        r = get(f"https://nfs.faireconomy.media/ff_calendar_{wk}.json")
        if not r: continue
        loaded += 1
        for e in r.json():
            try: t = dt.datetime.fromisoformat(e["date"]).astimezone(NY)
            except Exception: continue
            if t.date() != DAY or e.get("country") != "USD": continue
            title = e.get("title", "")
            fed = any(k in title for k in ("FOMC", "Fed", "Powell", "Speaks", "Federal"))
            if e.get("impact") in ("High", "Medium") or fed:
                events.append(dict(t=t, title=title, impact=e.get("impact", ""), fc=e.get("forecast", ""), prev=e.get("previous", ""), fed=fed))
    seen, out = set(), []
    for e in sorted(events, key=lambda z: z["t"]):
        k = (e["t"], e["title"])
        if k not in seen: seen.add(k); out.append(e)
    return out if loaded else None


def trump():
    r = get("https://media-cdn.factba.se/rss/json/trump/calendar-full.json")
    if not r: return None
    out = []
    try:
        for e in r.json():
            d = e.get("date") or ""
            if d != DAY.isoformat(): continue
            tm = (e.get("time") or "").strip()
            det = (e.get("details") or e.get("type") or "").strip()
            loc = (e.get("location") or "").strip()
            if det: out.append((tm, det, loc))
    except Exception as ex:
        notes.append(f"trump calendar parse {type(ex).__name__}"); return None
    return out


# ------------------------------------------------------------------ earnings
def earnings():
    r = get(f"https://api.nasdaq.com/api/calendar/earnings?date={DAY.isoformat()}")
    if not r: return None
    rows = ((r.json().get("data") or {}).get("rows")) or []
    def cap(x):
        try: return float(str(x).replace("$", "").replace(",", ""))
        except Exception: return 0.0
    pre, post, other = [], [], []
    for x in rows:
        s = x.get("symbol", ""); mc = cap(x.get("marketCap"))
        if mc < 20e9 and s not in MINE: continue
        item = (mc, s, s in MINE, x.get("epsForecast") or "")
        tm = x.get("time", "")
        (pre if "pre" in tm else post if "after" in tm else other).append(item)
    srt = lambda L: sorted(L, key=lambda z: (-z[2], -z[0]))[:12]
    return srt(pre), srt(post), srt(other)


# ------------------------------------------------------------------ markets
def quotes():
    import yfinance as yf
    tick = {"ES=F": "S&P futures", "NQ=F": "Nasdaq futures", "YM=F": "Dow futures", "^VIX": "VIX", "^TNX": "10-year yield",
            "CL=F": "Oil", "GC=F": "Gold", "BTC-USD": "Bitcoin"}
    out = []
    for s, name in tick.items():
        try:
            x = yf.Ticker(s).history(period="5d", interval="1d")
            last = yf.Ticker(s).history(period="1d", interval="5m", prepost=True)
            px = float(last.Close.iloc[-1]) if len(last) else float(x.Close.iloc[-1])
            prev = float(x.Close.iloc[-2]) if x.index[-1].date() >= DAY else float(x.Close.iloc[-1])
            out.append((name, px, (px / prev - 1) * 100))
        except Exception as e:
            notes.append(f"{s} {type(e).__name__}")
    return out


def premarket(syms):
    import yfinance as yf
    px = {}
    for s in syms:
        try:
            x = yf.Ticker(s).history(period="1d", interval="5m", prepost=True)
            if len(x): px[s] = float(x.Close.iloc[-1])
        except Exception:
            pass
    return px


# ------------------------------------------------------------------ posts
def fmt_t(t): return t.strftime("%-I:%M %p").lower()


def post1():
    L = [f"☀️🌪️ **GOOD MORNING, TAZ TRADERS** 🌪️☀️", f"📅 **{DAY:%A, %B %-d}** · market briefing", ""]
    q = quotes() if not os.environ.get("NO_QUOTES") else []
    if q:
        L.append("📈 **Pre-market**")
        L += [f"{'🟢' if c >= 0 else '🔴'} {n}: {p:,.2f} ({c:+.2f}%)" for n, p, c in q]
        L.append("")
    ev = econ()
    data = [e for e in (ev or []) if not e["fed"]]; fed = [e for e in (ev or []) if e["fed"]]
    L.append("🗓️ **Economic calendar (ET)**")
    if ev is None:
        L.append("❔ Couldn't load the economic calendar this morning. Check before the open.")
    elif data:
        for e in data:
            extra = " · ".join(z for z in (f"forecast {e['fc']}" if e["fc"] else "", f"prior {e['prev']}" if e["prev"] else "") if z)
            L.append(f"{'🚨' if e['impact'] == 'High' else '⚠️'} {fmt_t(e['t'])} · **{e['title']}**" + (f" · {extra}" if extra else ""))
    else:
        L.append("➖ No high or medium impact US data today.")
    L += ["", "🏛️ **Fed watch**"]
    if ev is None: L.append("❔ Calendar didn't load, so Fed speakers are unknown this morning.")
    else: L += [f"🎙️ {fmt_t(e['t'])} · **{e['title']}**" for e in fed] or ["➖ No Fed speakers or FOMC items on the calendar today."]
    tr = trump()
    L += ["", "🇺🇸 **Trump today**"]
    if tr is None: L.append("❔ Couldn't load his public schedule this morning. Watch the headlines.")
    elif not tr: L.append("➖ No public events on his schedule.")
    else:
        for tm, det, loc in tr[:8]:
            L.append(f"🎤 {tm + ' · ' if tm else ''}{det}" + (f" ({loc})" if loc else ""))
    er = earnings()
    L += ["", "💼 **Earnings today** (big names and the ones we trade)"]
    if er is None: L.append("❔ Couldn't load the earnings calendar this morning.")
    else:
        pre, post, other = er
        nm = lambda L_: ", ".join(f"**{s}**" if mine else s for _, s, mine, _ in L_)
        if pre: L.append(f"🌅 Before the open: {nm(pre)}")
        if post: L.append(f"🌙 After the close: {nm(post)}")
        if other: L.append(f"🕐 Time not set: {nm(other)}")
        if not (pre or post or other): L.append("➖ No major earnings today.")
    L += ["", "⚠️ Big data at 8:30 or 10:00 can whip the open. Let the first candles settle. Plan the trade, trade the plan. 🧘",
          "", "Pattern. Process. Paid. 🌪️🔴"]
    return "\n".join(L)


def post2():
    files = sorted(f for f in glob.glob("results/gray_box/lists/*.csv") if os.path.basename(f)[:-4] < DAY.isoformat())
    if not files: return "🎯 No Gray Box Fade list yet for today."
    t = pd.read_csv(files[-1])
    px = premarket(sorted(t.sym.unique())) if not os.environ.get("NO_QUOTES") else {}
    L = [f"🎯🌪️ **TODAY'S TRADE IDEAS: GRAY BOX FADE** 🌪️🎯", f"From last night's scan ({t['asof'].iloc[0]} close). Live only after it **arms**, then tags the **trigger**. 📦", ""]
    shown = 0
    for z in t.itertuples():
        if shown >= 5: break
        put = z.side == "PUT"; p = px.get(z.sym)
        if p is not None and ((p >= z.trigger) if put else (p <= z.trigger)):
            status = f"⛔ pre-market {p:.2f} is already past the trigger. If it opens there, SKIP."
        elif p is not None and ((p <= z.arm) if put else (p >= z.arm)):
            status = f"✅ pre-market {p:.2f} is already past the arm level. Armed. Watch the trigger."
        elif p is not None:
            gap = abs(p - z.arm) / z.atr
            status = f"⏳ pre-market {p:.2f} · {gap:.1f} daily range from arming"
        else:
            status = "⏳ no pre-market quote"
        shown += 1
        L += [f"{shown}️⃣ {'🔻' if put else '🟢'} **{z.sym} {'PUTS' if put else 'CALLS'}**",
              f"⏳ ARM {'below' if put else 'above'} **{z.arm}** · 🚨 TRIGGER **{z.trigger}** · 🛑 STOP **{z.stop}**",
              f"💰 HALF **{z.half}** then stop to entry · 🏃 RUNNER **{z.runner}**",
              f"{status}", ""]
    L += ["📋 Expiry a week+ out · contracts under 500 or a debit spread · 2 losses = done · stop set at entry, never moved further away.",
          "📊 Every setup gets graded after the close. Wins and losses.", "", "Pattern. Process. Paid. 🌪️🔴"]
    return "\n".join(L)


def send(text):
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > 1900: chunks.append(cur); cur = ""
        cur += line + "\n"
    chunks.append(cur)
    for ch in chunks:
        if os.environ.get("DRY") or not TOKEN: print(ch); print("-----"); continue
        r = requests.post(f"https://discord.com/api/v10/channels/{CH}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                          json={"content": ch, "allowed_mentions": {"parse": []}}, timeout=20)
        print(f"::notice::discord post {r.status_code}"); time.sleep(1.5)


if __name__ == "__main__":
    if not os.environ.get("FORCE"):
        if DAY.weekday() >= 5: print("::notice::weekend, nothing posted"); raise SystemExit
        if NOW.hour != 8: print(f"::notice::it is {NOW:%H:%M} ET, not the 8 AM run; nothing posted"); raise SystemExit
    send(post1())
    send(post2())
    if notes: print("::warning::" + " | ".join(notes[:20]))
