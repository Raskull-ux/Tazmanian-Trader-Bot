"""
One live track record for every list the bots post. Stock moves only, no dollar P&L.

Sources (rebuilt from scratch on every run, so it never double counts):
  gray box   results/gray_box/log.csv (graded on 5m bars by gray_box_bot.py grade). Result = ranges (daily ATR).
  watchlist  results/watchlist/lists.csv, graded here with watchlist.py's own rules (grade_item) on daily bars.
             Result in ATR from the trigger: target = +(trigger - target)/ATR, stop = -(stop - trigger)/ATR.
  clue board results/clue_board/<date>.csv, the top 10 names with 1+ broken clue. Graded on the next session as a put
             from that close: result = (close - next close)/ATR; hit = next low 0.5 ATR under the close; stopped = next
             high 0.5 ATR over the close.
Writes results/track_record.csv. POST=1 (the Sunday run) posts a summary to the private channel: lists, triggered,
hit, stopped, average result, for the last 7 days and since the start.
"""
import os, glob, time, datetime as dt
import numpy as np, pandas as pd, requests

OUT = "results/track_record.csv"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", ""); CH = os.environ.get("PRIVATE_CHANNEL_ID", "")
POST = os.environ.get("POST", "") == "1" or dt.datetime.now(dt.timezone.utc).weekday() == 6 and os.environ.get("GITHUB_EVENT_NAME") == "schedule"
COLS = ["source", "list_date", "graded", "sym", "side", "setup", "status", "triggered", "hit", "stopped", "result", "unit", "detail"]


def daily(symbols):
    import yfinance as yf
    out = {}
    symbols = sorted(set(symbols))
    for i in range(0, len(symbols), 60):
        chunk = symbols[i:i + 60]
        try:
            df = yf.download(chunk, period="1y", interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False)
        except Exception as e:
            print("yf fail", e); continue
        for s in chunk:
            try:
                x = (df[s] if len(chunk) > 1 else df).rename(columns=str.lower)[["open", "high", "low", "close"]].dropna()
                x.columns = ["o", "h", "l", "c"]; x.index = pd.to_datetime(x.index).tz_localize(None).normalize()
                if len(x): out[s] = x
            except Exception:
                pass
    return out


def gray_box():
    f = "results/gray_box/log.csv"
    if not os.path.exists(f): return []
    g = pd.read_csv(f); rows = []
    # a list is graded on the next session only (older runs re-graded the same list on later days)
    g = g.sort_values("day").drop_duplicates(["asof", "sym", "side"], keep="first")
    for z in g.itertuples():
        trig = z.result_range == z.result_range
        rows.append(dict(source="gray box", list_date=z.asof, graded=z.day, sym=z.sym, side=z.side, setup="box fade", status=z.result,
                         triggered=trig, hit=trig and "HALF" in str(z.result), stopped=trig and "STOPPED" in str(z.result),
                         result=z.result_range if trig else np.nan, unit="range", detail=""))
    return rows


def watchlist(D):
    f = "results/watchlist/lists.csv"
    if not os.path.exists(f): return []
    import watchlist as W
    L = pd.read_csv(f); rows = []
    for it in L.to_dict("records"):
        if it["sym"] == "NONE" or it["sym"] not in D: continue
        st, detail, done = W.grade_item(it, D[it["sym"]])
        trig = st in ("target", "stop") or (st == "open" and "in at" in detail) or st == "expired"
        res = np.nan
        if st == "target": res = (it["trigger"] - it["target"]) / it["atr"]
        elif st == "stop": res = -(it["stop"] - it["trigger"]) / it["atr"]
        rows.append(dict(source="watchlist", list_date=it["list_date"], graded=str(pd.Timestamp.now().date()) if done else "", sym=it["sym"],
                         side="PUT", setup=it["setup"], status=st, triggered=trig, hit=st == "target", stopped=st == "stop",
                         result=res, unit="ATR", detail=detail))
    return rows


def clue_board(D):
    rows = []
    for f in sorted(glob.glob("results/clue_board/20*.csv")):
        b = pd.read_csv(f)
        b = b[b.n_broken > 0].head(10)
        for z in b.itertuples():
            x = D.get(z.sym)
            if x is None: continue
            d0 = pd.Timestamp(z.date); nxt = x[x.index > d0]
            if not len(nxt):
                rows.append(dict(source="clue board", list_date=z.date, graded="", sym=z.sym, side="PUT", setup=f"{z.n_broken} broken",
                                 status="open", triggered=False, hit=False, stopped=False, result=np.nan, unit="ATR", detail="next session not done"))
                continue
            n1 = nxt.iloc[0]; c0, A = z.close, z.atr
            rows.append(dict(source="clue board", list_date=z.date, graded=str(nxt.index[0].date()), sym=z.sym, side="PUT",
                             setup=f"{z.n_broken} broken", status="graded", triggered=True, hit=bool(n1.l <= c0 - 0.5 * A),
                             stopped=bool(n1.h >= c0 + 0.5 * A), result=(c0 - n1.c) / A, unit="ATR",
                             detail=f"next close {n1.c:.2f} vs {c0:.2f}"))
    return rows


def post(text):
    if not TOKEN or not CH:
        print(text); return
    r = requests.post(f"https://discord.com/api/v10/channels/{CH}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                      json={"content": text[:1990], "allowed_mentions": {"parse": []}}, timeout=20)
    print("discord", r.status_code)


def summary(T):
    now = pd.Timestamp.now().normalize()
    L = [f"📒🌪️ **Track record: week ending {now:%a %b %d}** (stock moves only, no dollar P&L)", ""]
    for src in ("gray box", "watchlist", "clue board"):
        x = T[T.source == src]
        if not len(x): L.append(f"**{src}**: nothing posted yet"); continue
        for lab, y in (("last 7 days", x[pd.to_datetime(x.list_date) >= now - pd.Timedelta(days=7)]), ("since start", x)):
            t = y[y.triggered]
            unit = y.unit.iloc[0] if len(y) else ""
            L.append(f"**{src}** {lab}: {y.list_date.nunique()} lists · {len(y)} names · {len(t)} triggered · {int(t.hit.sum())} hit · "
                     f"{int(t.stopped.sum())} stopped" + (f" · avg {t.result.mean():+.2f} {unit}" if t.result.notna().any() else ""))
    L += ["", "Hit/stopped: gray box = half off / full stop; watchlist = target / stop; clue board = next day 0.5 ATR down / up.",
          "Pattern. Process. Paid. 🌪️🔴"]
    return "\n".join(L)


def main():
    syms = set()
    if os.path.exists("results/watchlist/lists.csv"): syms |= set(pd.read_csv("results/watchlist/lists.csv").sym) - {"NONE"}
    for f in glob.glob("results/clue_board/20*.csv"): syms |= set(pd.read_csv(f).sym)
    D = daily(syms) if syms else {}
    rows = gray_box() + watchlist(D) + clue_board(D)
    T = pd.DataFrame(rows, columns=COLS)
    T.to_csv(OUT, index=False)
    s = summary(T)
    print(s)
    if POST: post(s)


if __name__ == "__main__":
    main()
