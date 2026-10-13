"""
REAL OPTION PRICES TEST: do the signals that passed on stock moves still make money on real contracts?

Every pass so far measured the ETF's move, not an option. A small stock edge can disappear into the bid/ask spread
and time decay. This prices each trade with REAL Alpaca option trade prices (1-minute bars), Feb 2024 -> now
(as far back as Alpaca's option history goes).

ETFs: QQQ SPY IWM SMH XLK DIA.

THE FOUR SIGNALS (same definitions that passed on stock moves):
  S1  RSI 30 at the close -> CALLS at 3:55 pm. Daily RSI(14) closes at/under 30 (one per 5 sessions per ETF).
      Holds: 1 / 3 / 5 / 10 days (sold 3:55 pm), and '+50% target, else day 10'.
  S2  RSI 30 next morning -> CALLS at 9:35 am the day after an RSI-30 close. Holds: 1 hour, to 3:55 pm.
  S3  Live RSI 30 cross -> CALLS on the 5-min bar where the live daily RSI (yesterday's closes + current price)
      drops under 30 (yesterday's was above). One per 10 sessions. Holds: 1 hour, 2 hours, to 3:55 pm.
  S4  3-hour RSI 80 -> PUTS. 3-hour candles incl. extended hours (4/7/10/13/16/19 ET), RSI(14) closes at/above 80
      (one per 5 sessions per ETF). Entry at the candle close if it closes 10:00 / 1:00 / 4:00 (4:00 -> 3:55 pm),
      otherwise 9:35 next session. Holds: 1 / 3 / 5 days (3:55 pm).

CONTRACTS (picked at entry, from the real contract list):
  Expiry: 0DTE (same day; S2/S3 only), ~1 week (first expiry 7+ days out), ~3 weeks (21+ days out).
  Strike: ATM (nearest the price), 0.5% OTM, 1% OTM, and BUDGET = the nearest-to-the-money strike whose real entry
  price is $2.00 or less ($200 a contract: what Taz can actually buy). A hold that runs past expiry is skipped.
PRICES: entry = first real trade at/after the entry minute (within 10 min); exit = first trade at/after the exit
  minute (within 10 min, else the last trade before it). No trade = no price (counted, not guessed).
COSTS (assumption, not measured; Alpaca has no historical quotes): you pay max($0.02, 1% of the price) MORE than the
  trade price to buy and get that much LESS to sell. 'Stress' = double that. Returns are per contract, in %.
RANDOM: for every signal, the same trade (same ETF, same clock time, same contract rule) on 3 random sessions
  that are not within 5 sessions of a signal. Long options usually lose on random days (decay + spread), so a
  signal has to beat that AND make money.

PASS (set before running), ONE main contract per signal (the original test's setup, at the money):
  S1: ~3-week ATM, '+50% else day 10'  S2: ~1-week ATM, to 3:55 pm  S3: ~1-week ATM, 2 hours  S4: ~3-week ATM, 5 days
  20+ signal days; average return after costs > 0 AND above random; t >= 2.5 on both (t clustered by entry date,
  since ETFs signal together). Everything else (other contracts, budget picks, stress costs) is INFO ONLY.
Out: results/option_reality/report.md, trades.csv
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/option_reality"
ETFS = ["QQQ", "SPY", "IWM", "SMH", "XLK", "DIA"]
START = pd.Timestamp("2024-02-01")
TRADING = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"
NY = "America/New_York"
EXPIRIES = {"0DTE": 0, "1wk": 7, "3wk": 21}
STRIKES = {"ATM": 0.0, "0.5% OTM": 0.005, "1% OTM": 0.01}
BUDGET_OTM = (0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05)
BUDGET_MAX = 2.00
N_RANDOM = 3
SIGNALS = {
    "S1": dict(name="RSI 30 at the close -> calls", cp="C", exps=("1wk", "3wk"),
               holds=("1d", "3d", "5d", "10d", "+50% else 10d"), main=("3wk", "ATM", "+50% else 10d")),
    "S2": dict(name="RSI 30 next morning -> calls", cp="C", exps=("0DTE", "1wk", "3wk"),
               holds=("1h", "close"), main=("1wk", "ATM", "close")),
    "S3": dict(name="Live RSI 30 cross -> calls", cp="C", exps=("0DTE", "1wk", "3wk"),
               holds=("1h", "2h", "close"), main=("1wk", "ATM", "2h")),
    "S4": dict(name="3-hour RSI 80 -> puts", cp="P", exps=("1wk", "3wk"),
               holds=("1d", "3d", "5d"), main=("3wk", "ATM", "5d")),
}


# ------------------------------------------------------------------ API
def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing in this repo's secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


HD = None


def get(url, params):
    for i in range(7):
        try:
            r = requests.get(url, headers=HD, params=params, timeout=90)
        except requests.RequestException:
            time.sleep(2 ** i); continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** i); continue
        if r.status_code != 200:
            print(f"  {url.split('/')[-1]} {r.status_code}: {r.text[:150]}")
            return None
        return r.json()
    return None


def utc(ts):
    return pd.Timestamp(ts).tz_localize(NY).tz_convert("UTC").isoformat()


def stock_bars(sym, tf, start, end=None):
    rows, token = [], None
    end = end or (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": "split", "limit": 10000}
        if token:
            p["page_token"] = token
        j = get(f"{DATA}/v2/stocks/bars", p)
        if not j:
            break
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    if len(d):
        d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert(NY).dt.tz_localize(None)
    return d


def contracts(sym, day, cp, spot):
    """Real contract list (expired + live) for one ETF, expiring day .. day+40, strikes within 7%."""
    out = []
    for status in ("inactive", "active"):
        token = None
        while True:
            p = {"underlying_symbols": sym, "status": status, "type": "call" if cp == "C" else "put",
                 "expiration_date_gte": f"{day:%Y-%m-%d}", "expiration_date_lte": f"{day + pd.Timedelta(days=40):%Y-%m-%d}",
                 "strike_price_gte": round(spot * 0.93, 2), "strike_price_lte": round(spot * 1.07, 2), "limit": 10000}
            if token:
                p["page_token"] = token
            j = get(f"{TRADING}/v2/options/contracts", p)
            if not j:
                break
            out += [(c["symbol"], pd.Timestamp(c["expiration_date"]), float(c["strike_price"])) for c in j.get("option_contracts") or []]
            token = j.get("next_page_token")
            if not token:
                break
    return pd.DataFrame(out, columns=["occ", "exp", "k"]).drop_duplicates("occ")


def option_bars(occs, start, end):
    """1-minute real trade bars for several contracts; {occ: DataFrame(t, c, h)}."""
    res = {o: [] for o in occs}
    for i in range(0, len(occs), 50):
        chunk, token = occs[i:i + 50], None
        while True:
            p = {"symbols": ",".join(chunk), "timeframe": "1Min", "start": utc(start), "end": utc(end), "limit": 10000}
            if token:
                p["page_token"] = token
            j = get(f"{DATA}/v1beta1/options/bars", p)
            if not j:
                break
            for o, bl in (j.get("bars") or {}).items():
                res.setdefault(o, []).extend((b["t"], b["c"], b["h"]) for b in bl)
            token = j.get("next_page_token")
            if not token:
                break
    out = {}
    for o, rows in res.items():
        if rows:
            d = pd.DataFrame(rows, columns=["t", "c", "h"])
            d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert(NY).dt.tz_localize(None)
            out[o] = d.sort_values("t").reset_index(drop=True)
    return out


# ------------------------------------------------------------------ indicators / signals
def wilder(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return up, dn


def rsi(c, n=14):
    up, dn = wilder(c, n)
    return 100 - 100 / (1 + up / dn)


def sessions(daily):
    return pd.DatetimeIndex(daily.t.dt.normalize().unique())


def find_signals(sym, daily, m5, h1):
    """Returns list of dicts: sig, symbol, entry (timestamp), spot."""
    out = []
    d = daily.copy(); d["day"] = d.t.dt.normalize(); d = d.set_index("day")
    d["rsi"] = rsi(d.c)
    days = d.index
    ok = days >= START
    m5 = m5[(m5.t.dt.time >= pd.Timestamp("09:30").time()) & (m5.t.dt.time < pd.Timestamp("16:00").time())].copy()
    m5["day"] = m5.t.dt.normalize()
    m5["end"] = m5.t + pd.Timedelta(minutes=5)          # bar close time
    by_day = dict(tuple(m5.groupby("day")))

    def spot_at(ts):
        g = by_day.get(ts.normalize())
        if g is None:
            return np.nan
        x = g[g.end <= ts]
        return float(x.c.iloc[-1]) if len(x) else float(g.o.iloc[0])

    # S1 + S2
    last = -99
    for i in np.where(ok & (d.rsi.values <= 30))[0]:
        if i - last < 5:
            continue
        last = i
        day = days[i]
        out.append(dict(sig="S1", symbol=sym, entry=day + pd.Timedelta(hours=15, minutes=55), spot=float(d.c.iloc[i])))
        if i + 1 < len(days):
            nd = days[i + 1]; e = nd + pd.Timedelta(hours=9, minutes=35)
            out.append(dict(sig="S2", symbol=sym, entry=e, spot=spot_at(e)))
    # S3: live daily RSI crosses under 30 on a 5-min bar
    up, dn = wilder(d.c)
    last = -99
    for i in range(1, len(days)):
        if not ok[i] or d.rsi.iloc[i - 1] <= 30 or i - last < 10:
            continue
        g = by_day.get(days[i])
        if g is None:
            continue
        ch = g.c.values - d.c.iloc[i - 1]
        u = (up.iloc[i - 1] * 13 + np.clip(ch, 0, None)) / 14
        w = (dn.iloc[i - 1] * 13 + np.clip(-ch, 0, None)) / 14
        live = 100 - 100 / (1 + u / w)
        hit = np.where(live < 30)[0]
        hit = hit[g.end.values[hit] <= np.datetime64(days[i] + pd.Timedelta(hours=15, minutes=30))]
        if len(hit):
            j = hit[0]; last = i
            out.append(dict(sig="S3", symbol=sym, entry=pd.Timestamp(g.end.values[j]), spot=float(g.c.values[j])))
    # S4: 3-hour RSI 80 (extended hours)
    h = h1[(h1.t.dt.hour >= 4) & (h1.t.dt.hour < 20)].copy()
    h["start"] = 4 + 3 * ((h.t.dt.hour - 4) // 3); h["day"] = h.t.dt.normalize()
    g3 = h.groupby(["day", "start"]).agg(c=("c", "last")).reset_index().sort_values(["day", "start"])
    g3["rsi"] = rsi(g3.c).values
    last_day = None
    for r in g3[(g3.rsi >= 80) & (g3.day >= START)].itertuples():
        close_h = r.start + 3
        if close_h in (10, 13):
            e = r.day + pd.Timedelta(hours=close_h)
        elif close_h == 16:
            e = r.day + pd.Timedelta(hours=15, minutes=55)
        else:
            pos = days.searchsorted(r.day + pd.Timedelta(days=1) if r.start >= 16 else r.day)
            if pos >= len(days):
                continue
            e = days[pos] + pd.Timedelta(hours=9, minutes=35)
        if last_day is not None and days.searchsorted(e.normalize()) - days.searchsorted(last_day) < 5:
            continue
        sp = spot_at(e)
        if np.isnan(sp):
            continue
        last_day = e.normalize()
        out.append(dict(sig="S4", symbol=sym, entry=e, spot=sp))
    return out, days, spot_at


def exit_times(entry, holds, days):
    pos = days.searchsorted(entry.normalize())
    out = {}
    for h in holds:
        if h in ("1h", "2h"):
            t = min(entry + pd.Timedelta(hours=int(h[0])), entry.normalize() + pd.Timedelta(hours=15, minutes=55))
        elif h == "close":
            t = entry.normalize() + pd.Timedelta(hours=15, minutes=55)
        else:
            n = int(h.split("d")[0].split()[-1]) if h[0].isdigit() else 10
            if pos + n >= len(days):
                continue
            t = days[pos + n] + pd.Timedelta(hours=15, minutes=55)
        if t > entry:
            out[h] = t
    return out


def cost(px, mult=1.0):
    return max(0.02, 0.01 * px) * mult


def price_after(b, t, within=10):
    x = b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=within))]
    return float(x.c.iloc[0]) if len(x) else np.nan


def price_exit(b, t):
    p = price_after(b, t)
    if np.isnan(p):
        x = b[(b.t <= t) & (b.t >= t.normalize())]
        p = float(x.c.iloc[-1]) if len(x) else np.nan
    return p


def pick(C, entry, spot, cp, exp_key, otm):
    day = entry.normalize()
    target = day + pd.Timedelta(days=EXPIRIES[exp_key])
    c = C[C.exp >= target] if exp_key != "0DTE" else C[C.exp == day]
    if not len(c):
        return None
    c = c[c.exp == c.exp.min()]
    if otm == 0:
        return c.iloc[(c.k - spot).abs().argmin()]
    if cp == "C":
        x = c[c.k >= spot * (1 + otm)]
        return x.sort_values("k").iloc[0] if len(x) else None
    x = c[c.k <= spot * (1 - otm)]
    return x.sort_values("k").iloc[-1] if len(x) else None


def price_event(ev, cfg, days, is_random):
    """All contract/hold combos for one event -> list of trade rows."""
    entry, spot, cp = ev["entry"], ev["spot"], cfg["cp"]
    if not np.isfinite(spot):
        return []
    C = contracts(ev["symbol"], entry.normalize(), cp, spot)
    if not len(C):
        return []
    ex = exit_times(entry, cfg["holds"], days)
    if not ex:
        return []
    picks = {}
    for e in cfg["exps"]:
        for sn, otm in STRIKES.items():
            r = pick(C, entry, spot, cp, e, otm)
            if r is not None:
                picks[(e, sn)] = r
        for otm in BUDGET_OTM:
            r = pick(C, entry, spot, cp, e, otm)
            if r is not None:
                picks[(e, f"budget:{otm}")] = r
    occs = sorted({r.occ for r in picks.values()})
    last_exit = max(ex.values())
    B = option_bars(occs, entry.normalize() + pd.Timedelta(hours=9, minutes=30), last_exit + pd.Timedelta(minutes=15))
    rows = []
    budget_done = set()
    for (e, sn), r in sorted(picks.items(), key=lambda kv: (kv[0][0], kv[0][1].startswith("budget"),
                                                             float(kv[0][1].split(":")[1]) if kv[0][1].startswith("budget") else 0)):
        b = B.get(r.occ)
        if b is None:
            continue
        px = price_after(b, entry)
        if not np.isfinite(px) or px <= 0:
            continue
        label = sn
        if sn.startswith("budget"):
            if e in budget_done or px > BUDGET_MAX:
                continue
            budget_done.add(e); label = "BUDGET (<= $2.00)"
        for hname, t in ex.items():
            if t.normalize() > r.exp:
                continue                                     # hold runs past expiry
            if hname == "+50% else 10d":
                w = b[(b.t > entry) & (b.t <= t)]
                hit = w[w.c >= px * 1.5]
                xp = float(hit.c.iloc[0]) if len(hit) else price_exit(b, t)
            else:
                xp = price_exit(b, t)
            if not np.isfinite(xp):
                continue
            rec = dict(sig=ev["sig"], symbol=ev["symbol"], random=is_random, entry=entry, spot=spot, occ=r.occ,
                       exp=e, strike=label, k=r.k, otm_pct=(r.k / spot - 1) * 100 * (1 if cp == "C" else -1),
                       hold=hname, px_in=px, px_out=xp, raw=(xp / px - 1) * 100)
            for lab, m in (("ret", 1.0), ("stress", 2.0)):
                rec[lab] = ((xp - cost(xp, m)) / (px + cost(px, m)) - 1) * 100
            rows.append(rec)
    return rows


def random_events(sig_events, days, spot_at, rng):
    """Same clock time, random sessions not within 5 sessions of any signal of this type."""
    sig_pos = {days.searchsorted(e["entry"].normalize()) for e in sig_events}
    bad = {p + k for p in sig_pos for k in range(-5, 6)}
    pool = [i for i in range(len(days)) if days[i] >= START and i not in bad and i < len(days) - 12]
    out = []
    for e in sig_events:
        for i in rng.choice(pool, size=min(N_RANDOM, len(pool)), replace=False):
            t = days[i] + (e["entry"] - e["entry"].normalize())
            sp = spot_at(t) if e["sig"] != "S1" else spot_at(days[i] + pd.Timedelta(hours=16))
            out.append(dict(sig=e["sig"], symbol=e["symbol"], entry=t, spot=sp))
    return out


# ------------------------------------------------------------------ report
def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); d = pd.Series(pd.DatetimeIndex(dates).normalize())
    ok = x.notna(); x, d = x[ok], d[ok]
    g = x.groupby(d.values).mean()
    if len(g) < 5 or g.std() == 0:
        return float("nan")
    return g.mean() / (g.std(ddof=1) / math.sqrt(len(g)))


def summarize(T, sig, e, s, h, col="ret"):
    x = T[(T.sig == sig) & (T.exp == e) & (T.strike == s) & (T.hold == h)]
    sg, rd = x[~x.random], x[x.random]
    if not len(sg):
        return None
    t_abs = tcl(sg[col], sg.entry)
    # edge vs random: each signal minus the average random trade of the same ETF
    rmean = rd.groupby("symbol")[col].mean()
    edge = sg[col] - sg.symbol.map(rmean)
    t_edge = tcl(edge, sg.entry)
    return dict(n=len(sg), days=sg.entry.dt.normalize().nunique(), avg=sg[col].mean(), med=sg[col].median(),
                win=(sg[col] > 0).mean(), cost=sg.px_in.mean() * 100, rnd=rd[col].mean() if len(rd) else np.nan,
                t_abs=t_abs, edge=edge.mean(), t_edge=t_edge)


def report(T, counts):
    L = ["# Real option prices: do the passed signals make money on real contracts?", "",
         "Real Alpaca option trade prices (1-minute), Feb 2024 to now. Returns per contract, AFTER an assumed cost of "
         "max($0.02, 1% of price) each way (Alpaca has no historical bid/ask; 'stress' doubles it). "
         "Random = the same trade at the same clock time on 3 random sessions per signal. t clustered by entry date.", "",
         "## 0. Coverage", "", "| Signal | Signals found | Signals priced (main contract) | Random trades priced |", "|---|---|---|---|"]
    for k, cfg in SIGNALS.items():
        e, s, h = cfg["main"]
        x = T[(T.sig == k) & (T.exp == e) & (T.strike == s) & (T.hold == h)] if len(T) else T
        L.append(f"| {k} {cfg['name']} | {counts.get(k, 0)} | {(~x.random).sum() if len(x) else 0} | {x.random.sum() if len(x) else 0} |")
    L += ["", "## 1. PASS CHECK (set before running): main contract per signal",
          "20+ signal days; average after costs > 0 AND above random; t >= 2.5 on both.", "",
          "| Signal | Contract | Signal days | Avg cost | Avg return | Median | Win rate | Random avg | Edge vs random | t (avg) | t (edge) | Verdict |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, cfg in SIGNALS.items():
        e, s, h = cfg["main"]
        r = summarize(T, k, e, s, h) if len(T) else None
        if r is None:
            L.append(f"| {k} | {e} {s}, {h} | 0 | — | — | — | — | — | — | — | — | no data |"); continue
        ok = r["days"] >= 20 and r["avg"] > 0 and r["edge"] > 0 and r["t_abs"] >= 2.5 and r["t_edge"] >= 2.5
        L.append(f"| {k} {cfg['name']} | {e} {s}, {h} | {r['days']} | ${r['cost']:,.0f} | {r['avg']:+.1f}% | {r['med']:+.1f}% | "
                 f"{r['win']:.0%} | {r['rnd']:+.1f}% | {r['edge']:+.1f} pts | {r['t_abs']:.1f} | {r['t_edge']:.1f} | "
                 f"{'**PASS**' if ok else ('too few' if r['days'] < 20 else 'fail')} |")
    L += ["", "## 2. Every contract choice (INFO ONLY: many tries, some will look good by luck)", ""]
    for k, cfg in SIGNALS.items():
        L += [f"### {k} {cfg['name']}", "",
              "| Expiry | Strike | Hold | Trades | Avg cost | Avg return | Median | Win rate | Stress-cost avg | Random avg | Edge | t (edge) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for e in cfg["exps"]:
            for s in list(STRIKES) + ["BUDGET (<= $2.00)"]:
                for h in cfg["holds"]:
                    r = summarize(T, k, e, s, h) if len(T) else None
                    if r is None or r["n"] < 5:
                        continue
                    st = summarize(T, k, e, s, h, "stress")
                    L.append(f"| {e} | {s} | {h} | {r['n']} | ${r['cost']:,.0f} | {r['avg']:+.1f}% | {r['med']:+.1f}% | {r['win']:.0%} | "
                             f"{st['avg']:+.1f}% | {r['rnd']:+.1f}% | {r['edge']:+.1f} | {r['t_edge']:.1f} |")
        L.append("")
    L += ["## 3. Every signal, main contract", "",
          "| Signal | ETF | Entry | Contract | Paid | Sold | Return after costs |", "|---|---|---|---|---|---|---|"]
    for k, cfg in SIGNALS.items():
        e, s, h = cfg["main"]
        x = T[(T.sig == k) & (T.exp == e) & (T.strike == s) & (T.hold == h) & (~T.random)] if len(T) else T
        for r in x.sort_values("entry").itertuples():
            L.append(f"| {k} | {r.symbol} | {r.entry:%Y-%m-%d %H:%M} | {r.occ} | ${r.px_in:.2f} | ${r.px_out:.2f} | {r.ret:+.0f}% |")
    L += ["", "Limits: Feb 2024 onward only (Alpaca's option history), so samples are small and it was mostly a rising "
          "market. Trade prices, not bid/ask: the cost line is an assumption. Entry/exit at the first trade within "
          "10 minutes of the planned time. Not financial advice."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    global HD
    HD = keys()
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(7)
    rows, counts = [], {}
    for sym in ETFS:
        daily = stock_bars(sym, "1Day", "2023-01-01T00:00:00Z")
        m5 = stock_bars(sym, "5Min", "2024-01-15T00:00:00Z")
        h1 = stock_bars(sym, "1Hour", "2023-06-01T00:00:00Z")
        if len(daily) < 200 or len(m5) < 1000:
            print(f"  {sym}: not enough stock data"); continue
        sigs, days, spot_at = find_signals(sym, daily, m5, h1)
        for k, cfg in SIGNALS.items():
            ev = [e for e in sigs if e["sig"] == k]
            counts[k] = counts.get(k, 0) + len(ev)
            for e in ev:
                rows += price_event(e, cfg, days, False)
            for e in random_events(ev, days, spot_at, rng):
                rows += price_event(e, cfg, days, True)
            print(f"  {sym} {k}: {len(ev)} signals, trades so far {len(rows)}", flush=True)
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/trades.csv", index=False)
    report(T, counts)


if __name__ == "__main__":
    main()
