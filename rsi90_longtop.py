"""
RSI long-term top test: the 3-hour chart and the 10-day chart.

Taz: "3-hour RSI 90 marks a long-term top. It's rare. Even if the stock keeps running, eventually it rolls over hard."
     "The 10-day RSI works like the others, but on that chart it's much more extreme. Like the 3-hour, it gets there QUICK."
     "Realistically the contract has to be under $200."

Universe: Taz's 145 core names (minus volatility/commodity products) + the 200 most-traded other names
(universe/universe.csv), so a rare signal still gets a real sample.

CHARTS
  3-hour : Alpaca 1-hour bars WITH extended hours (2016 -> now) built into 3-hour candles at 4/7/10/13/16/19 ET.
           Levels: RSI 90 and 87. Signal = first 3h close at/above the level.
  10-day : each candle = 10 trading days (half a month), on one fixed calendar for every name (counted from SPY's
           sessions, like a chart's fixed anchor). Daily data from Yahoo back to 2003 (Alpaca fallback).
           Levels: RSI 80, 85, 90. Read the way you'd see it live: at each day's close, using the candle still
           forming (no peeking at the rest of the candle).
  RSI(14), Wilder, on every chart. One signal per name per level per 180 trading days (one per run-up; no two windows overlap).
  Entry reference = that day's close (next day's if the 3h candle was after the close).

"QUICK" (set before running): bars since RSI was last under 50.
  3-hour fast = 30 candles or fewer (about 5 sessions).  10-day fast = 6 candles or fewer (about 3 months).

CONTRACT COST (rough estimate, not real prices): a near-the-money weekly (5 trading days) priced off the real
(unsplit) share price and the last 20 days' realized volatility: cost ~ 100 x 0.4 x price x vol x sqrt(5/252).
Buckets: under $200 (what Taz can trade), $200-500, over $500.

WHAT IT MEASURES (daily bars, from the signal day)
  1. The run: highest high within the next 60 sessions, how far above, how many days later
  2. The rollover: deepest fall from THAT later high within the 60 sessions after it
  3. Rolled over hard = fell 20%+ (also 30%+) from that later high
  4. Top held: that 60-session high was not beaten in the 120 sessions after
  5. Price 60 / 120 sessions after the signal
Compared with the same measurements on
  (a) every day of the same name and period, and
  (b) OVERBOUGHT days only (daily RSI 70+) of the same name, period AND the same size of moves over the next 120
      sessions (5 buckets of the name's own volatility over the outcome window). The question this answers: when the
      stock swings that hard, is it DOWN more often after the signal than after other overbought days?
      (Added after a noise check: on fake random data, extreme RSI shows up as a stock gets wilder, and wilder stocks
      fall 20% more often by themselves. Matching on past volatility was not enough; matching on the window is.)

SCORING (direction, not size; set after the noise check showed size-based rates pass on random data):
  tilt = rolled over 20%+ from the later high MINUS ripped 25%+ off the later low (the mirror image), and
         top held 6 months MINUS bottom held 6 months. Random data has zero tilt at any volatility.
PASS (set before running), all names pooled, per chart and level:
  40+ signals; either tilt beats OVERBOUGHT days' tilt by 5+ points in every period that has
  5+ signals (at least 2 such periods; periods 2005-15 / 2016-21 / 2022-26), t >= 3.0 clustered by year.
  Under-$200 names and fast vs slow are shown as an INFO-ONLY breakdown (no pass verdict: too many slices).
Out: results/rsi90_longtop/report.md, signals.csv
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/rsi90_longtop"
PERIODS = (("2005-2015", "2005-01-01", "2016-01-01"), ("2016-2021", "2016-01-01", "2022-01-01"),
           ("2022-2026", "2022-01-01", "2100-01-01"))
SKIP = {"VXX", "UVXY", "JNUG", "TLT", "UNG", "USO", "GLD", "SLV", "GDX"}
H_RUN, H_FALL, H_HOLD, COOL = 60, 60, 120, 180
LEVELS = {"3h": (90, 87), "10d": (80, 85, 90)}
FAST = {"3h": 30, "10d": 6}
M = ["run", "run_days", "fall", "roll20", "roll30", "held", "r60", "r120",
     "rip25", "rip43", "bheld", "d20", "d30", "dheld"]


# ---------------- data ----------------
def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing in this repo's secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


HD = None


def fetch(sym, tf, start, adj="all"):
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": adj, "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=HD, params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            print(f"  {sym} {tf}: {r.status_code}"); break
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    if len(d):
        d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


def yahoo(sym):
    """Daily bars 2003+: o/h/l/c fully adjusted, c_raw = the real unsplit close (for contract cost)."""
    try:
        import yfinance as yf
    except Exception:
        return None
    for i in range(4):
        try:
            h = yf.Ticker(sym).history(start="2003-01-01", auto_adjust=False, actions=True)
            if h is not None and len(h) >= 400:
                break
        except Exception:
            pass
        time.sleep(2 ** i)
    else:
        return None
    h.index = pd.to_datetime(h.index).tz_localize(None).normalize()
    h = h[~h.index.duplicated()].dropna(subset=["Close"])
    f = (h["Adj Close"] / h["Close"]).fillna(1.0)
    sp = h["Stock Splits"].replace(0, 1.0).fillna(1.0) if "Stock Splits" in h else pd.Series(1.0, index=h.index)
    after = sp[::-1].cumprod()[::-1].shift(-1).fillna(1.0)          # splits AFTER each day
    return pd.DataFrame({"o": h.Open * f, "h": h.High * f, "l": h.Low * f, "c": h.Close * f,
                         "c_raw": h.Close * after}, index=h.index)


def daily(sym):
    d = yahoo(sym)
    if d is not None:
        return d
    a = fetch(sym, "1Day", "2015-06-01")
    if len(a) < 400:
        return None
    r = fetch(sym, "1Day", "2015-06-01", "raw")
    a = a.assign(date=a.t.dt.normalize()).set_index("date")[["o", "h", "l", "c"]]
    a["c_raw"] = r.assign(date=r.t.dt.normalize()).set_index("date").c.reindex(a.index) if len(r) else np.nan
    return a


def hourly(sym):
    return fetch(sym, "1Hour", "2015-10-01")


# ---------------- indicators ----------------
def wilder(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return up, dn


def rsi(c, n=14):
    up, dn = wilder(c, n)
    return 100 - 100 / (1 + up / dn)


def bars_since_under50(r):
    """For each bar: how many bars since RSI was last under 50 (NaN until it has been)."""
    r = np.asarray(r, float); out = np.full(len(r), np.nan); last = None
    for i, v in enumerate(r):
        if not np.isnan(v) and v < 50:
            last = i
        if last is not None:
            out[i] = i - last
    return out


def three_hour(h1):
    h = h1.t.dt.hour
    h1 = h1[(h >= 4) & (h < 20)].copy()
    h1["start"] = 4 + 3 * ((h1.t.dt.hour - 4) // 3)
    h1["date"] = h1.t.dt.normalize()
    g = h1.groupby(["date", "start"]).agg(c=("c", "last")).reset_index().sort_values(["date", "start"])
    g["rsi"] = rsi(g.c).values
    g["since50"] = bars_since_under50(g.rsi.values)
    return g


def ten_day(dd, cal):
    """Live 10-day RSI at each daily close (candle still forming), plus completed-candle bars since RSI < 50."""
    blk = pd.Series(cal.searchsorted(dd.index) // 10, index=dd.index)
    C = dd.c.groupby(blk.values).last()                      # completed candle closes, indexed by block id
    up, dn = wilder(C)
    rsi_c = 100 - 100 / (1 + up / dn)
    s50 = pd.Series(bars_since_under50(rsi_c.values), index=C.index)
    k = blk.values
    pos = C.index.get_indexer(k)                             # position of this day's block
    prev = pos - 1
    ok = prev >= 13                                          # need 14+ completed candles before
    live = np.full(len(dd), np.nan); since = np.full(len(dd), np.nan)
    pc, pu, pdn = C.values, up.values, dn.values
    ch = dd.c.values[ok] - pc[prev[ok]]
    u = (pu[prev[ok]] * 13 + np.clip(ch, 0, None)) / 14
    w = (pdn[prev[ok]] * 13 + np.clip(-ch, 0, None)) / 14
    live[ok] = 100 - 100 / (1 + u / w)
    since[ok] = s50.values[prev[ok]] + 1
    return live, since


def wk_cost(dd):
    lr = np.log(dd.c).diff()
    vol = (lr.rolling(20).std() * math.sqrt(252)).clip(lower=0.15)
    return (100 * 0.4 * dd.c_raw * vol * math.sqrt(5 / 252)).values


def bucket(x):
    if pd.isna(x):
        return "unknown"
    return "under $200" if x < 200 else ("$200-500" if x < 500 else "over $500")


def outcomes(dd):
    h, l, c = dd.h.values, dd.l.values, dd.c.values
    n = len(c)
    out = {k: np.full(n, np.nan) for k in M}
    for i in range(n - H_RUN - H_FALL):
        seg = h[i + 1:i + 1 + H_RUN]
        k = int(seg.argmax()); pk = seg[k]; pki = i + 1 + k
        fall = (l[pki + 1:pki + 1 + H_FALL].min() / pk - 1) * 100
        out["run"][i] = (pk / c[i] - 1) * 100; out["run_days"][i] = k + 1; out["fall"][i] = fall
        out["roll20"][i] = float(fall <= -20); out["roll30"][i] = float(fall <= -30)
        # mirror image (what pure noise does just as often): lowest low of the next 60, then rip off it
        sl = l[i + 1:i + 1 + H_RUN]; kl = int(sl.argmin()); lo = sl[kl]; loi = i + 1 + kl
        rip = (h[loi + 1:loi + 1 + H_FALL].max() / lo - 1) * 100
        out["rip25"][i] = float(rip >= 25); out["rip43"][i] = float(rip >= 100 / 0.7 - 100)
        out["d20"][i] = out["roll20"][i] - out["rip25"][i]; out["d30"][i] = out["roll30"][i] - out["rip43"][i]
        if i + H_RUN + H_HOLD < n:
            out["held"][i] = float(max(pk, h[i]) >= h[i + 1 + H_RUN:i + 1 + H_RUN + H_HOLD].max())
            out["bheld"][i] = float(min(lo, l[i]) <= l[i + 1 + H_RUN:i + 1 + H_RUN + H_HOLD].min())
            out["dheld"][i] = out["held"][i] - out["bheld"][i]
        out["r60"][i] = (c[i + 60] / c[i] - 1) * 100
        if i + 120 < n:
            out["r120"][i] = (c[i + 120] / c[i] - 1) * 100
    return out


def period_of(day):
    for pn, a, z in PERIODS:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


def symbols():
    u = pd.read_csv("universe/universe.csv")
    core = u[u.group == "core"].symbol.tolist()
    broad = u[u.group == "broad"].sort_values("avg_dollar_vol", ascending=False).symbol.head(200).tolist()
    return [s for s in dict.fromkeys(core + broad) if s not in SKIP]


# ---------------- per symbol ----------------
def run_symbol(sym, cal, rows):
    dd = daily(sym)
    if dd is None or len(dd) < 400:
        return
    dd = dd[dd.index >= "2003-01-01"]
    days = dd.index
    drsi = rsi(dd.c).values
    O = outcomes(dd)
    cost = wk_cost(dd)
    ds = pd.Series(days)
    lr = np.log(dd.c).diff()
    vol = lr[::-1].rolling(H_RUN + H_FALL, min_periods=H_RUN).std()[::-1].shift(-1).values  # volatility over the NEXT 120 sessions
    vq = pd.Series(vol).rank(pct=True).values                      # this name's own volatility, 0..1
    vb = np.where(np.isnan(vq), -1, np.minimum((vq * 5).astype(int), 4))   # 5 volatility buckets
    base = {}
    for pn, a, z in PERIODS:
        m = ((ds >= a) & (ds < z)).values
        ob = m & (drsi >= 70)
        base[(pn, "all")] = {k: (np.nanmean(O[k][m]) if m.sum() >= 5 else np.nan) for k in M}
        for q in range(5):
            mq = ob & (vb == q)
            if mq.sum() < 10:                                      # too few: widen to neighbouring buckets
                mq = ob & (np.abs(vb - q) <= 1)
            base[(pn, "ob", q)] = {k: (np.nanmean(O[k][mq]) if mq.sum() >= 5 else np.nan) for k in M}

    def add(chart, lvl, i, when, val, since):
        pn = period_of(days[i])
        rec = dict(chart=chart, level=lvl, symbol=sym, date=days[i], when=when, rsi=val, since50=since,
                   fast=(not np.isnan(since)) and since <= FAST[chart], daily_rsi=drsi[i], close=dd.c.iloc[i],
                   price_then=dd.c_raw.iloc[i], weekly_cost=cost[i], cost_bucket=bucket(cost[i]))
        q = int(vb[i]) if vb[i] >= 0 else 2
        for k in M:
            rec[k] = O[k][i]; rec[f"all_{k}"] = base[(pn, "all")][k]; rec[f"ob_{k}"] = base[(pn, "ob", q)][k]
        rows.append(rec)

    # 10-day chart
    live, since = ten_day(dd, cal)
    for lvl in LEVELS["10d"]:
        last = -999
        for i in np.where((live >= lvl) & (days >= pd.Timestamp("2005-01-01")))[0]:
            if i - last < COOL or np.isnan(O["run"][i]):
                continue
            last = i
            add("10d", lvl, i, f"{days[i]:%Y-%m-%d}", live[i], since[i])

    # 3-hour chart
    h1 = hourly(sym)
    if len(h1) < 500:
        return
    t3 = three_hour(h1)
    for lvl in LEVELS["3h"]:
        last = -999
        for r in t3[(t3.rsi >= lvl) & (t3.date >= "2016-03-01")].itertuples():
            pos = days.searchsorted(r.date)
            if pos >= len(days) or days[pos] != r.date:
                continue
            i = pos if r.start <= 13 else pos + 1
            if i >= len(days) or i - last < COOL or np.isnan(O["run"][i]):
                continue
            last = i
            add("3h", lvl, i, f"{r.date:%Y-%m-%d} {r.start}:00", r.rsi, r.since50)


# ---------------- report ----------------
def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); d = pd.Series(np.asarray(dates))
    ok = x.notna(); x, d = x[ok], d[ok]
    g = x.groupby(pd.DatetimeIndex(d.values).year).mean()
    if len(g) < 8 or g.std() == 0:
        return float("nan")
    return g.mean() / (g.std(ddof=1) / math.sqrt(len(g)))


def check(y, k):
    """Edge vs overbought days: per-period means, t, pass flag."""
    y = y.dropna(subset=[k, f"ob_{k}"])
    if len(y) < 5:
        return None
    e = y[k] - y[f"ob_{k}"]
    pe = []
    for _, a, z in PERIODS:
        s = e[(y.date >= a) & (y.date < z)]
        pe.append(s.mean() if len(s) >= 5 else np.nan)
    t = tcl(e, y.date.values)
    real = [p for p in pe if pd.notna(p)]
    ok = len(y) >= 40 and len(real) >= 2 and all(p >= 0.05 for p in real) and pd.notna(t) and t >= 3.0
    return dict(n=len(y), sig=y[k].mean(), ob=y[f"ob_{k}"].mean(), all=y[f"all_{k}"].mean(), pe=pe, t=t, ok=ok)


def fmt_pe(pe):
    return " / ".join("—" if pd.isna(p) else f"{p * 100:+.0f} pts" for p in pe)


def report(E):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    name = {"3h": "3-hour", "10d": "10-day"}
    L = ["# RSI long-term top test: 3-hour and 10-day charts", "",
         "How it's scored (direction, not size): for each signal, did the stock ROLL OVER 20%+ from its later high "
         "(the high of the next 60 sessions, then the 60 sessions after it), or did it RIP 25%+ off its later low (the "
         "mirror image)? Random data does both equally often, however volatile the stock is, so only a real top tilts it. "
         "Same for 'top held 6 months' vs 'bottom held 6 months'. The signal's tilt is compared with the tilt on OVERBOUGHT "
         "days (daily RSI 70+) of the same stock, same period, same size of moves. t clustered by year.", "",
         "## 1. PASS CHECK (set before running)",
         "40+ signals; the tilt beats overbought days by 5+ points in every period with 5+ signals (at least 2 periods); "
         "t >= 3.0. Periods: 2005-15 / 2016-21 / 2022-26 (the 3-hour chart starts 2016).", "",
         "| Chart | RSI | Signals | Measure | Signal: down / up | Overbought days: down / up | Tilt edge by period | t | Verdict |",
         "|---|---|---|---|---|---|---|---|---|"]
    meas = (("d20", "roll20", "rip25", "rolled over 20%+ vs ripped 25%+"),
            ("dheld", "held", "bheld", "top held 6 mo vs bottom held 6 mo"),
            ("d30", "roll30", "rip43", "rolled over 30%+ vs ripped 43%+ (info only)"))
    for ch in ("3h", "10d"):
        for lvl in LEVELS[ch]:
            x = E[(E.chart == ch) & (E.level == lvl)]
            for k, dn, up, lab in meas:
                r = check(x, k)
                if r is None:
                    continue
                y = x.dropna(subset=[k])
                v = "**PASS**" if (r["ok"] and k != "d30") else "fail"
                L.append(f"| {name[ch]} | {lvl} | {r['n']} | {lab} | {y[dn].mean():.0%} / {y[up].mean():.0%} | "
                         f"{y['ob_' + dn].mean():.0%} / {y['ob_' + up].mean():.0%} | {fmt_pe(r['pe'])} | {r['t']:.1f} | {v} |")

    L += ["", "## 2. Breakdown: names you can actually trade, and how fast RSI got there",
          "INFO ONLY, no pass verdict: these are many slices of the same signals, so some will look strong by luck. "
          "Use them to see WHERE an edge sits once section 1 passes. Cost = estimated near-the-money weekly at the signal (rough Black-Scholes, not real quotes). "
          "Fast = 3-hour: 30 candles or fewer since RSI was under 50; 10-day: 6 candles or fewer.", "",
          "| Chart | RSI | Group | Signals | Rolled over 20% / ripped 25% (overbought days) | t | Top held / bottom held (overbought days) | t |",
          "|---|---|---|---|---|---|---|---|"]
    for ch in ("3h", "10d"):
        for lvl in LEVELS[ch]:
            x = E[(E.chart == ch) & (E.level == lvl)]
            groups = [("under $200 weekly", x[x.cost_bucket == "under $200"]),
                      ("$200-500 weekly", x[x.cost_bucket == "$200-500"]),
                      ("over $500 weekly", x[x.cost_bucket == "over $500"]),
                      ("FAST", x[x.fast == True]), ("slow", x[x.fast == False]),
                      ("FAST + under $200", x[(x.fast == True) & (x.cost_bucket == "under $200")])]
            for gname, y in groups:
                a, b = check(y, "d20"), check(y, "dheld")
                if a is None and b is None:
                    continue
                def cell(r, dn, up):
                    if r is None:
                        return "—", "—"
                    return (f"{y[dn].mean():.0%} / {y[up].mean():.0%} ({y['ob_' + dn].mean():.0%} / {y['ob_' + up].mean():.0%})",
                            f"{r['t']:.1f}")
                (a1, a2), (b1, b2) = cell(a, "roll20", "rip25"), cell(b, "held", "bheld")
                L.append(f"| {name[ch]} | {lvl} | {gname} | {len(y)} | {a1} | {a2} | {b1} | {b2} |")

    L += ["", "## 3. The typical path after a signal (medians)", "",
          "| Chart | RSI | Signals | Kept running to (within 60 sessions) | Days to that high | Fall from that high | 60 sessions later | 120 sessions later |",
          "|---|---|---|---|---|---|---|---|"]
    for ch in ("3h", "10d"):
        for lvl in LEVELS[ch]:
            x = E[(E.chart == ch) & (E.level == lvl)]
            if len(x):
                L.append(f"| {name[ch]} | {lvl} | {len(x)} | +{x.run.median():.1f}% (overbought days +{x.ob_run.median():.1f}%) | "
                         f"{x.run_days.median():.0f} | {x.fall.median():.1f}% (overbought days {x.ob_fall.median():.1f}%) | "
                         f"{x.r60.median():+.1f}% | {x.r120.median():+.1f}% |")

    def listing(title, x):
        out = ["", title, "",
               "| Name | Signal | RSI | Fast? | Weekly cost (est.) | Kept running to | Days | Then fell from there | 60 sessions later | Top held 6 months |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for r in x.sort_values("date").itertuples():
            cst = "—" if pd.isna(r.weekly_cost) else f"${r.weekly_cost:,.0f}"
            out.append(f"| {r.symbol} | {r.when} | {r.rsi:.0f} | {'yes' if r.fast else 'no'} | {cst} | +{r.run:.1f}% | {r.run_days:.0f} | "
                       f"{r.fall:.1f}% | {r.r60:+.1f}% | {'yes' if r.held == 1 else ('no' if r.held == 0 else '—')} |")
        return out

    L += listing("## 4. Every 3-hour RSI 90 signal", E[(E.chart == "3h") & (E.level == 90)])
    L += listing("## 5. Every 10-day RSI 85 signal (RSI column shows if it also reached 90)", E[(E.chart == "10d") & (E.level == 85)])
    L += ["", "Limits: today's most-traded names (survivorship: names that collapsed and delisted are missing, which hides "
          "some rollovers, so the real rollover rates are probably a bit higher). Daily bars for the after-signal path. "
          "Contract cost is an estimate, not real quotes. 10-day candles are on one fixed calendar; your chart's candles may "
          "start on different days, which can move the exact RSI reading a few points. Rare signals = small samples: a "
          "strong-looking result can still be luck, which is what the pass rule is for. Patterns on the 10-day chart are NOT "
          "in this run."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    global HD
    HD = keys()
    os.makedirs(OUT, exist_ok=True)
    spy = daily("SPY")
    if spy is None:
        raise SystemExit("Could not load SPY for the 10-day calendar.")
    cal = spy.index[spy.index >= "2003-01-01"]
    rows = []
    syms = symbols()
    for n, s in enumerate(syms, 1):
        try:
            run_symbol(s, cal, rows)
        except Exception as ex:
            print(f"  {s}: {ex}")
        if n % 20 == 0:
            print(f"  {n}/{len(syms)} names, signals {len(rows)}", flush=True)
    E = pd.DataFrame(rows)
    E.to_csv(f"{OUT}/signals.csv", index=False)
    report(E)


if __name__ == "__main__":
    main()
