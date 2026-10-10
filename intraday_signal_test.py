"""
Intraday signal test — the daily setups graded the way Taz trades them: the break happens LIVE during the
session, the put/call goes on at that 5-minute bar, and it pays in 15 minutes to a few hours.
Data: Alpaca 5-minute bars (SIP, regular hours), 2016 -> now, plus Alpaca daily bars. Needs the repo's Alpaca keys.

Live signals (checked on every 5-min bar close, using today's LIVE moving averages and RSI:
yesterday's closes + the current price, exactly what the chart shows at that moment). One per day, 10-day cooldown.
  1. Triple MA break DOWN live -> puts: price under the live 10, 20 and 50 SMA, and the last TWO daily closes were
     NOT under all three (a fresh break).
       splits: Taz version (50 5%+ over 200, not into a golden cross, 10/20/50 within 2.5%), 50 10%+ over 200,
               time of day (first hour / 10:30-14:00 / last 2 hours)
  2. Triple MA break UP live -> calls (mirror)
  3. Live daily RSI crosses 70 -> puts ; crosses 80 -> puts ; crosses 30 -> calls (yesterday's RSI was on the other side)
  4. Yesterday CLOSED with a fresh triple break down -> puts at today's 9:35 bar (the "next morning" trade)
     Yesterday CLOSED with RSI <= 30 -> calls at today's 9:35 bar

Measured from the signal bar's close, your way (puts: down), capped at today's close:
  move after 15m, 30m, 1h, 2h, 3h, at today's close, and at the next day's close
  deepest move your way within 15m / 1h / 3h / rest of day (how far a put could have been sold)
  worst move against you within 1h
  hit rates: moved 0.5% / 1% / 2% your way within 3h
Random = EVERY day's bar at the same time of day (same 5-min slot), same symbol, same period, same direction
(the open is wilder than lunch, so time of day must match exactly). Edge = signal minus random. t clustered by month.

PASS (set before running), ETFs and Mega tech separately, 100+ signals, positive in BOTH periods (2016-21, 2022-26),
t >= 3, edge at least 0.10% of price (or +3 points on the hit rate), on ANY of: move at 15m / 30m / 1h / 2h / 3h /
close, or 'moved 1% your way within 3h'. Checked on random-walk 5-min test data, 6 runs x 14 rows: without the size
floor 1 false pass in 84 (a +0.03% 'edge'); with it, none.
Out: results/intraday_signal/report.md, signals.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/intraday_signal"
ETFS = "QQQ SPY IWM DIA XLK SMH SOXX IGV XLC XLY FDN ARKK".split()
MEGA = "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split()
PERIODS = (("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))
HB = {"15m": 3, "30m": 6, "1h": 12, "2h": 24, "3h": 36}
NB = 78   # 5-min bars in a regular session


# ------------------------------------------------------------------ data
def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing: run this in the repo that has ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


def fetch(sym, tf, start):
    H, rows, token = keys(), [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": "all", "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            raise RuntimeError(f"{sym} {tf} {r.status_code}: {r.text[:200]}")
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c"])
    d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York")
    return d


def load(sym):
    dd = fetch(sym, "1Day", "2015-01-01")
    dd.index = dd.t.dt.tz_localize(None).dt.normalize(); dd = dd[["o", "h", "l", "c"]]
    m = fetch(sym, "5Min", "2016-01-01")
    m["day"] = m.t.dt.tz_localize(None).dt.normalize()
    mins = m.t.dt.hour * 60 + m.t.dt.minute
    m = m[(mins >= 570) & (mins < 960)].copy()                      # 9:30 .. 15:55 bar starts
    m["slot"] = ((m.t.dt.hour * 60 + m.t.dt.minute) - 570) // 5
    return dd, m


# ------------------------------------------------------------------ grids
def to_grid(m, days):
    """days x 78 arrays (NaN where a bar is missing) for o,h,l,c."""
    di = pd.Index(days)
    r = di.get_indexer(m.day); ok = r >= 0
    g = {k: np.full((len(days), NB), np.nan) for k in ("o", "h", "l", "c")}
    for k in g:
        g[k][r[ok], m.slot.values[ok]] = m[k].values[ok]
    # forward-fill missing closes within the day so horizons always have a price
    c = pd.DataFrame(g["c"]).ffill(axis=1).values
    g["c"] = c
    for k in ("h", "l"):
        g[k] = np.where(np.isnan(g[k]), c, g[k])
    return g


def outcomes_grid(g, next_close, sign):
    """Outcome of entering at the close of EVERY bar (days x 78) in direction sign."""
    c, h, l = g["c"], g["h"], g["l"]
    nd, nb = c.shape
    last = np.nanmax(np.where(np.isnan(c), -1, np.arange(nb)[None, :]), axis=1)      # last bar index each day
    out = {}
    idx = np.arange(nb)[None, :]
    for lab, hb in HB.items():
        tgt = np.minimum(idx + hb, last[:, None])
        out[lab] = sign * (np.take_along_axis(c, tgt, axis=1) / c - 1) * 100
    lastc = c[np.arange(nd), last][:, None]
    out["close"] = sign * (lastc / c - 1) * 100
    out["next close"] = sign * (next_close[:, None] / c - 1) * 100
    # deepest favourable / adverse within windows (forward, capped at day end)
    fav_src = l if sign < 0 else h
    adv_src = h if sign < 0 else l
    for lab, w in (("best 15m", 3), ("best 1h", 12), ("best 3h", 36), ("best day", nb)):
        run = np.full_like(c, np.nan)
        for k in range(1, w + 1):
            sh = np.full_like(c, np.nan); sh[:, :-k] = fav_src[:, k:]
            run = np.fmin(run, sh) if sign < 0 else np.fmax(run, sh)
        out[lab] = sign * (run / c - 1) * 100
    run = np.full_like(c, np.nan)
    for k in range(1, 13):
        sh = np.full_like(c, np.nan); sh[:, :-k] = adv_src[:, k:]
        run = np.fmax(run, sh) if sign < 0 else np.fmin(run, sh)
    out["worst 1h"] = sign * (run / c - 1) * 100
    for p in (0.5, 1, 2):
        out[f"hit {p}%"] = np.where(np.isnan(out["best 3h"]), np.nan, (out["best 3h"] >= p).astype(float))
    return out


METRICS = list(HB) + ["close", "next close", "best 15m", "best 1h", "best 3h", "best day", "worst 1h", "hit 0.5%", "hit 1%", "hit 2%"]


def baseline(O, days):
    """mean outcome per (period, exact 5-min slot of the day). Exact slot, not half-hour: on test data a 9:35 entry
    vs a 9:30-10:00 average was biased (the first bar carries the open's extra movement)."""
    base = {}
    dser = pd.Series(days)
    for pn, a, z in PERIODS:
        rows = ((dser >= a) & (dser < z)).values
        means = {k: np.nanmean(O[k][rows, :], axis=0) for k in METRICS}
        for b in range(NB):
            base[(pn, b)] = {k: means[k][b] for k in METRICS}
    return base


def period_of(day):
    for pn, a, z in PERIODS:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


# ------------------------------------------------------------------ signals
def run_symbol(sym, grp, dd, m, out):
    days = sorted(set(m.day) & set(dd.index))
    days = [d for d in days if d >= pd.Timestamp("2016-01-01")]
    if len(days) < 300:
        return
    c = dd.c
    s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    below3 = (c < c.rolling(10).mean()) & (c < c.rolling(20).mean()) & (c < s50)
    above3 = (c > c.rolling(10).mean()) & (c > c.rolling(20).mean()) & (c > s50)
    gc = ((s50 > s200) & (s50.shift() <= s200.shift())).rolling(30, min_periods=1).max().astype(bool)
    into_gc = gc | ((s50 < s200) & (s50 >= s200 * 0.98) & (s50 > s50.shift(5)))
    delta = c.diff()
    au = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    ad = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + au / ad)
    P = pd.DataFrame({"sum9": c.rolling(9).sum(), "sum19": c.rolling(19).sum(), "sum49": c.rolling(49).sum(),
                      "s50": s50, "s200": s200, "below3": below3, "above3": above3, "into_gc": into_gc,
                      "au": au, "ad": ad, "rsi": rsi, "c": c}).shift(1)          # everything known BEFORE today's open
    P["below3_2"] = below3.shift(2); P["above3_2"] = above3.shift(2)
    for col in ("below3", "above3", "below3_2", "above3_2", "into_gc"):
        P[col] = P[col].astype("boolean").fillna(False).astype(bool)
    P["next_c"] = c.shift(-1)
    P = P.reindex(days)
    g = to_grid(m, days)
    nextc = P.next_c.values
    O = {+1: outcomes_grid(g, nextc, +1), -1: outcomes_grid(g, nextc, -1)}
    B = {s: baseline(O[s], days) for s in (+1, -1)}
    cl = g["c"]
    s10 = (P.sum9.values[:, None] + cl) / 10; s20 = (P.sum19.values[:, None] + cl) / 20; s50l = (P.sum49.values[:, None] + cl) / 50
    chg = cl - P.c.values[:, None]
    up = (P.au.values[:, None] * 13 + np.clip(chg, 0, None)) / 14
    dn = (P.ad.values[:, None] * 13 + np.clip(-chg, 0, None)) / 14
    rsil = 100 - 100 / (1 + up / dn)
    live = {
        "Live triple break DOWN -> puts": ((cl < s10) & (cl < s20) & (cl < s50l)) & ~(P.below3.values.astype(bool) | P.below3_2.values.astype(bool))[:, None],
        "Live triple break UP -> calls": ((cl > s10) & (cl > s20) & (cl > s50l)) & ~(P.above3.values.astype(bool) | P.above3_2.values.astype(bool))[:, None],
        "Live RSI crosses 70 -> puts": (rsil >= 70) & (P.rsi.values < 70)[:, None],
        "Live RSI crosses 80 -> puts": (rsil >= 80) & (P.rsi.values < 80)[:, None],
        "Live RSI crosses 30 -> calls": (rsil <= 30) & (P.rsi.values > 30)[:, None],
    }
    gap = (P.s50 / P.s200 - 1).values * 100
    for name, M in live.items():
        sign = -1 if "puts" in name else +1
        M = np.where(np.isnan(cl), False, M)
        last = -99
        for i in range(len(days)):
            if i - last < 10 or not np.isfinite(P.s200.values[i]):
                continue
            hits = np.where(M[i])[0]
            if not len(hits):
                continue
            j = hits[0]; last = i
            tags = {}
            if "triple" in name:
                bunch = (max(s10[i, j], s20[i, j], s50l[i, j]) - min(s10[i, j], s20[i, j], s50l[i, j])) / cl[i, j] * 100
                tags = dict(gap=gap[i], bunch=bunch, into_gc=bool(P.into_gc.values[i]))
            emit(out, name, sym, grp, days[i], j, sign, O, B, i, tags)
    # next-morning trades from yesterday's CLOSE
    fresh_close = (below3 & ~below3.shift(2, fill_value=False)).reindex(days).shift(1).fillna(False).astype(bool).values
    rsi_close = (rsi <= 30).reindex(days).shift(1).fillna(False).astype(bool).values
    for name, M, sign in (("Yesterday closed triple break DOWN -> puts at 9:35", fresh_close, -1),
                          ("Yesterday closed RSI <= 30 -> calls at 9:35", rsi_close, +1)):
        last = -99
        for i in np.where(M)[0]:
            if i - last >= 10 and np.isfinite(cl[i, 0]):
                emit(out, name, sym, grp, days[i], 0, sign, O, B, i, {}); last = i


def emit(out, name, sym, grp, day, j, sign, O, B, i, tags):
    b = B[sign].get((period_of(day), j), {})
    rec = dict(setup=name, symbol=sym, group=grp, date=day, bar=j, time=f"{9 + (30 + 5 * j) // 60}:{(30 + 5 * j) % 60:02d}", **tags)
    for k in METRICS:
        rec[k] = O[sign][k][i, j]
        rec[f"ctrl_{k}"] = b.get(k, np.nan)
    out.append(rec)


# ------------------------------------------------------------------ report
def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); dd = pd.Series(np.asarray(dates))
    ok = x.notna(); x, dd = x[ok], dd[ok]
    dm = x.groupby(pd.DatetimeIndex(dd.values).to_period("M")).mean()
    if len(dm) < 5 or dm.std() == 0:
        return float("nan")
    return dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm)))


def per(x, a, b):
    return x[(x.date >= a) & (x.date < b)]


def check(x, k):
    e = x[k] - x[f"ctrl_{k}"]
    pe = [(per(x, a, b)[k] - per(x, a, b)[f"ctrl_{k}"]).mean() for _, a, b in PERIODS]
    t = tcl(e, x.date.values)
    floor = 0.03 if k.startswith("hit") else 0.10      # big enough to matter for an option: 0.10% of price, or +3 points hit rate
    return len(x) >= 100 and all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3 and e.mean() >= floor, pe, e.mean(), t


def report(E):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    names = list(dict.fromkeys(E.setup))
    L = ["# Intraday — the setups graded in minutes and hours", "",
         "Entry = close of the 5-minute bar where the signal happened (live moving averages / RSI = yesterday's closes + "
         "current price). Your-way move: puts = down. Random = every day's bar at the same 5-minute time slot, same symbol, "
         "same period. Edge = signal minus random (in % of price). t clustered by month.", "",
         "## PASS CHECK (set before running): 100+ signals, positive in BOTH periods, t >= 3, edge >= 0.10% of price "
         "(or +3 points hit rate), on any of 15m / 30m / 1h / 2h / 3h / close, or 'moved 1% your way within 3h'", "", "| Setup | Group | Signals | Passes on | Strongest |", "|---|---|---|---|---|"]
    tries = list(HB) + ["close", "hit 1%"]
    for s in names:
        for g in ("ETF", "MEGA"):
            x = E[(E.setup == s) & (E.group == g)]
            if not len(x):
                continue
            hits, best = [], None
            for k in tries:
                ok, pe, em, t = check(x, k)
                if ok:
                    hits.append(k)
                if pd.notna(t) and (best is None or t > best[2]):
                    best = (k, em, t, pe)
            ev = f"{best[0]}: {best[1]:+.3f} (t {best[2]:.1f}; {' / '.join(f'{p:+.3f}' for p in best[3])})" if best else "—"
            L.append(f"| {s} | {g} | {len(x)} | {'**' + ', '.join(hits) + '**' if hits else 'nothing'} | {ev} |")

    def table(title, X, splits=()):
        L.extend([f"\n### {title}\n", "| Group | Signals | 15m | 30m | 1h | 2h | 3h | Today's close | Next close | Moved 1% your way in 3h |",
                  "|---|---|---|---|---|---|---|---|---|---|"])
        groups = [("QQQ alone", X[X.symbol == "QQQ"])] + [(g, X[X.group == g]) for g in ("ETF", "MEGA")]
        groups += [(f"ETF: {lab}", X[(X.group == "ETF") & f(X)]) for lab, f in splits]
        for lab, x in groups:
            if len(x) < 8:
                continue
            cells = [f"{(x[k] - x[f'ctrl_{k}']).mean():+.2f} (t {tcl(x[k] - x[f'ctrl_{k}'], x.date.values):.1f})" for k in list(HB) + ["close", "next close"]]
            L.append(f"| {lab} | {len(x)} | " + " | ".join(cells) + f" | {x['hit 1%'].mean():.0%} vs {x['ctrl_hit 1%'].mean():.0%} |")

    tod = [("first hour", lambda x: x.bar < 12), ("10:30-14:00", lambda x: (x.bar >= 12) & (x.bar < 54)), ("last 2 hours", lambda x: x.bar >= 54)]
    L += ["\n## Edge by holding time (in % of price, signal minus random)"]
    for s in names:
        X = E[E.setup == s]
        sp = list(tod)
        if "triple" in s:
            sp += [("Taz version", lambda x: (x.gap >= 5) & (~x.into_gc.astype(bool)) & (x.bunch <= 2.5)),
                   ("50 10%+ over 200", lambda x: x.gap >= 10)]
        if "9:35" in s:
            sp = []
        table(s, X, sp)
    L += ["\n## How far it went your way (deepest point) and against you\n",
          "| Setup | Group | Best within 15m | Best within 1h | Best within 3h | Best rest of day | Worst against within 1h |", "|---|---|---|---|---|---|---|"]
    for s in names:
        for g, x in (("QQQ", E[(E.setup == s) & (E.symbol == "QQQ")]), ("ETF", E[(E.setup == s) & (E.group == "ETF")]), ("MEGA", E[(E.setup == s) & (E.group == "MEGA")])):
            if len(x) < 8:
                continue
            cells = [f"{x[k].mean():.2f}% vs {x[f'ctrl_{k}'].mean():.2f}%" for k in ("best 15m", "best 1h", "best 3h", "best day", "worst 1h")]
            L.append(f"| {s} | {g} ({len(x)}) | " + " | ".join(cells) + " |")
    q = E[(E.symbol == "QQQ") & (E.setup == "Live triple break DOWN -> puts")].sort_values("date")
    L += ["\n## QQQ live triple breaks down (every one)\n", "| Date | Time | 50 vs 200 | 15m | 1h | 3h | Close | Best within 3h | Worst within 1h |",
          "|---|---|---|---|---|---|---|---|---|"]
    for _, r in q.iterrows():
        L.append(f"| {r['date']:%Y-%m-%d} | {r['time']} | {r['gap']:+.1f}% | {r['15m']:+.2f}% | {r['1h']:+.2f}% | {r['3h']:+.2f}% | "
                 f"{r['close']:+.2f}% | {r['best 3h']:+.2f}% | {r['worst 1h']:+.2f}% |")
    L += ["", "Limits: 5-minute bars (the 15-minute moves inside a bar are not seen). Stock/ETF moves, not option prices: "
          "an out-of-the-money put pays when the move is big and fast, so read 'best within' and 'moved 1%' with that in mind."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    E = []
    for grp, syms in (("ETF", ETFS), ("MEGA", MEGA)):
        for s in syms:
            try:
                dd, m = load(s)
            except Exception as ex:
                print(f"  {s}: {ex}"); continue
            run_symbol(s, grp, dd, m, E)
            print(f"  {s}: {len(m)} bars, signals so far {len(E)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/signals.csv.gz", index=False, compression="gzip")
    report(E)


if __name__ == "__main__":
    main()
