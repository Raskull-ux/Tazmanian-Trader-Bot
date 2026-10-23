"""
Nightly scanner (after the close): 860 stocks (Taz's 75 + sector peers + liquid names).
Posts to the private trade channel. Setups = the ones that held up on 2022-26 data the rules never saw:
  1. Staircase off a top + green higher high still under the top + RSI < 50   (860 stocks: 48.8% vs 45.0% base; your 75: 53%)
     ⭐ with RSI < 40 + QQQ down over 5 days: 54.4% on 2022-26 (5-day put outcome)
  2. Long staircase at a top (green, 4-5 lower-high reds, green under the first green) + RSI < 50  (49.3%; your 75: 53%)
     ⭐ with the stock under its 50: 54.3% on 2022-26
  3. Shortlist: between the 200 and the falling 10 SMA (no edge on its own; your calls here were right 57%)
Every hit gets the daily grade (same math as the bot's `grade` command). Not trade calls: a list to look at.
"""
import os, sys, json, time, datetime as dt
import numpy as np, pandas as pd, requests, yfinance as yf

U = pd.read_csv("universe/expanded_universe.csv")
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", ""); CH = os.environ.get("PRIVATE_CHANNEL_ID", "")
FORCE = os.environ.get("FORCE", "") == "1"


def pull(symbols):
    data = {}
    for i in range(0, len(symbols), 80):
        chunk = symbols[i:i + 80]
        for _ in range(3):
            try:
                df = yf.download(chunk, period="2y", interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False); break
            except Exception as e:
                print("retry", e); time.sleep(5)
        for s in chunk:
            try:
                x = (df[s] if len(chunk) > 1 else df).rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
                x.columns = ["o", "h", "l", "c"]
                if len(x) > 260: data[s] = x
            except Exception:
                pass
    return data


def ind(x):
    c = x.c
    tr = pd.concat([x.h - x.l, (x.h - c.shift()).abs(), (x.l - c.shift()).abs()], axis=1).max(axis=1)
    x["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    x["e8"] = c.ewm(span=8, adjust=False).mean(); x["e10"] = c.ewm(span=10, adjust=False).mean()
    for n in (10, 20, 50, 200): x[f"s{n}"] = c.rolling(n).mean()
    d = c.diff(); g = d.clip(lower=0).ewm(span=14, adjust=False, min_periods=14).mean(); l = (-d.clip(upper=0)).ewm(span=14, adjust=False, min_periods=14).mean()
    x["rsi"] = 100 - 100 / (1 + g / l); x["hh20"] = x.h.rolling(20).max(); x["r5"] = c.pct_change(5)
    return x


def grade(x, q):
    i = len(x) - 1; c, h, e8, s10, e10, A = x.c.values, x.h.values, x.e8.values, x.s10.values, x.e10.values, x.atr.values
    pts = 2 * (c[i] < e8[i])
    pts += int(h[i] >= min(e8[i], s10[i]) and c[i] < max(e8[i], s10[i]) and c[i - 1] < max(e8[i - 1], s10[i - 1]))
    pts += int(sum(abs(c[k] - s10[k]) <= 0.5 * A[k] for k in range(i - 4, i + 1)) >= 3)
    pts += int(e10[i] < s10[i])
    qi = q.index.get_loc(x.index[i]) if x.index[i] in q.index else None
    if qi is not None: pts += int(c[i] / c[i - 5] - 1 < q.c.iloc[qi] / q.c.iloc[qi - 5] - 1)
    return int(pts), ("A" if pts >= 6 else "A-" if pts == 5 else "B" if pts == 4 else "C" if pts == 3 else "D")


def scan(x, q):
    i = len(x) - 1; o, h, l, c = x.o.values, x.h.values, x.l.values, x.c.values
    A, R, s50, s10, s200, hh20 = x.atr.values, x.rsi.values, x.s50.values, x.s10.values, x.s200.values, x.hh20.values
    G = c > o; Rd = c < o
    run = 0
    for k in range(i - 1, 0, -1):
        if h[k] < h[k - 1]: run += 1
        else: break
    hits = []
    if G[i] and run >= 3:
        st = i - 1 - run
        if h[st] >= hh20[st] and c[st] > s50[st] and h[i - 1] < h[i] < h[st] and R[i] < 50:
            qi = q.index.get_loc(x.index[i]) if x.index[i] in q.index else None
            q5 = q.c.iloc[qi] / q.c.iloc[qi - 5] - 1 if qi else 0
            star = R[i] < 40 and q5 < 0
            hits.append(("stair", star, f"top {h[st]:.2f} (stop over it) · {run} lower highs · RSI {R[i]:.0f}"))
    if G[i]:
        for k in (4, 5):
            st = i - k - 1
            if G[st] and all(Rd[j] for j in range(st + 1, i)) and all(h[j + 1] < h[j] for j in range(st, i - 1)) and h[i] < h[st] and h[st] >= hh20[st] and R[i] < 50:
                hits.append(("long", c[i] < s50[i], f"top {h[st]:.2f} (stop over it) · {k} reds · RSI {R[i]:.0f}")); break
    if s10[i] > s200[i] and c[i] < s10[i] and c[i] >= s200[i] * 0.99 and s10[i] < s10[i - 3] and (s10[i] - s200[i]) <= 1.5 * A[i]:
        hits.append(("pocket", False, f"10 SMA {s10[i]:.2f} · 200 SMA {s200[i]:.2f}"))
    return hits


def post(text):
    if not TOKEN or not CH: print(text); return
    for chunk in [text[i:i + 1900] for i in range(0, len(text), 1900)]:
        r = requests.post(f"https://discord.com/api/v10/channels/{CH}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                          json={"content": chunk, "allowed_mentions": {"parse": []}}, timeout=20)
        print(f"::notice::discord post {r.status_code}"); time.sleep(1)


def main():
    syms = sorted(set(U.symbol) | {"QQQ"})
    data = pull(syms); q = ind(data["QQQ"].copy())
    last = q.index[-1].date(); today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).date()
    if last != today and not FORCE:
        print(f"::notice::Latest bar {last} is not today {today}. Nothing posted."); return
    mine = set(U[U.group == "your 75"].symbol)
    out = {"stair": [], "long": [], "pocket": []}
    for s, x in data.items():
        if s == "QQQ" or x.index[-1].date() != last: continue
        x = ind(x.copy())
        for kind, star, info in scan(x, q):
            pts, letter = grade(x, q)
            out[kind].append((star, pts, s, letter, x.c.iloc[-1], info, s in mine))
    def fmt(rows, n):
        rows.sort(key=lambda z: (not z[0], -z[1], z[2]))
        return [f"{'⭐ ' if r[0] else ''}**{r[2]}** {r[4]:.2f} · grade **{r[3]}** ({r[1]}/6) · {r[5]}{' · your name' if r[6] else ''}" for r in rows[:n]]
    L = [f"🌙🌪️ **Nightly scan: {last:%a %b %d}** ({len(data)} stocks). A list to look at, not trade calls.", ""]
    L += ["**1. Staircase + green higher high under the top + RSI < 50** (860 stocks: 48.8% vs 45% normal · your names 53%) ⭐ = RSI < 40 and QQQ down 5 days (54% on new data)"]
    L += fmt(out["stair"], 12) or ["   none today"]
    L += ["", "**2. Long staircase at a top + RSI < 50** (49% vs 45% · your names 53%) ⭐ = under its 50 (54% on new data)"]
    L += fmt(out["long"], 10) or ["   none today"]
    L += ["", "**3. Shortlist: between the 200 and the falling 10 SMA** (no edge by itself · your calls here were right 57%)"]
    L += fmt(out["pocket"], 10) or ["   none today"]
    L += ["", "Next: `grade TICKER` for any of these, `check TICKER` before entry. Stop = a close over the top. A week+ out, 2 losses = done.", "", "Pattern. Process. Paid. 🌪️🔴"]
    print(f"::notice::stocks {len(data)} | stair {len(out['stair'])} | long {len(out['long'])} | pocket {len(out['pocket'])} | " + " ; ".join(f"{k}: " + ", ".join(sorted(z[2] for z in v)[:15]) for k, v in out.items()))
    post("\n".join(L))


if __name__ == "__main__":
    main()
