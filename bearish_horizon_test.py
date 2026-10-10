"""
Bearish horizon test — the bearish setups graded the way puts actually get paid:
longer holds (5 to 60 days), the LOWEST point reached inside the window, and a put-option estimate
held up to 20 days with profit targets. Free (Yahoo daily back to 1999, Alpaca fallback 2016+).

Setups (puts unless stated)
  Triple MA break DOWN (close under 10/20/50, not under all three 2 days earlier; first fire in 10 days)
    - all breaks
    - Taz's version: 50 SMA 5%+ over the 200, NOT into a golden cross, 10/20/50 bunched within 2.5%
    - 50 SMA 10%+ over the 200 ("far above the 200 = harder dump")
    - next day closes lower (entry at that close)
    - failed retest of the 10 from below (entry at the retest)
  Daily RSI 70 and RSI 80 (first close at/above)
  Mirror for comparison: triple MA break UP -> calls

Measured for every signal, compared with EVERY day of the same symbol and period ('random'):
  1. Close-to-close move your way after 5, 10, 15, 20, 30, 40, 60 days
  2. Best point inside the window: deepest low within 15 / 20 / 30 days (how far a put could have been sold)
  3. Hit rates: dropped 5% / 7% / 10% at any point within 30 days
  4. Put option estimate: at-the-money, 30 days to expiry, Black-Scholes with the real volatility index
     (VIX/VXN/RVX) day by day for ETFs; stocks use a 20-day/1-year realized-vol blend x1.2. Exits within 20 days:
     (a) hold 20 days, (b) +50% target else day 20, (c) +100% target else day 20.

PASS (set before running), ETF group and Mega tech judged separately, 100+ signals:
  A. close-to-close edge > 0 in EVERY period (2000-15 / 2016-21 / 2022-26) with t >= 3 at ANY of 15/20/30/40 days, or
  B. 'dropped 5% within 30 days' rate beats random in EVERY period with t >= 3, or
  C. put option exit (b) beats random in EVERY period with t >= 3 (ETFs only: they use the real volatility index;
     the stock option estimate leaned toward puts on random test data, so it is shown but not used to pass).
Checked on random-walk test data, 6 runs x 16 rows: 1 false pass in 96.
t clustered by month. Out: results/bearish_horizon/report.md, events.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/bearish_horizon"
ETFS = "QQQ SPY IWM DIA XLK SMH SOXX IGV XLC XLY FDN ARKK".split()
MEGA = "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split()
VOL_INDEX = {"SPY": "^VIX", "DIA": "^VIX", "IWM": "^RVX", "QQQ": "^VXN", "XLK": "^VXN", "SMH": "^VXN", "SOXX": "^VXN",
             "IGV": "^VXN", "FDN": "^VXN", "XLC": "^VXN", "XLY": "^VIX", "ARKK": "^VXN"}
PERIODS = (("2000-2015", "1999-01-01", "2016-01-01"), ("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))
H = (5, 10, 15, 20, 30, 40, 60)
QQQ_DATES = ["2021-09-17", "2022-01-04", "2023-03-09", "2023-10-18", "2024-04-04", "2024-04-15", "2024-08-30", "2025-02-21"]
DTE, HOLD = 30, 20


# ------------------------------------------------------------------ data
def yahoo(sym):
    try:
        import yfinance as yf
        d = yf.download(sym, start="1999-01-01", auto_adjust=True, progress=False, threads=False)
        if d is None or len(d) < 300:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        d.columns = ["o", "h", "l", "c", "v"]
        d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        return d.dropna(subset=["c"])
    except Exception as ex:
        print(f"  yahoo {sym}: {ex}")
        return None


def alpaca(sym):
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s or sym.startswith("^"):
        return None
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": "1Day", "start": "2016-01-01", "end": end, "feed": "sip", "adjustment": "all", "limit": 10000}
        if token:
            p["page_token"] = token
        r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=p, timeout=60,
                         headers={"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s})
        if r.status_code != 200:
            return None
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    if not rows:
        return None
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v"])
    d.index = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return d[["o", "h", "l", "c", "v"]]


def load(sym):
    d = yahoo(sym)
    if d is None:
        d = alpaca(sym)
    time.sleep(1)
    return d


# ------------------------------------------------------------------ pricing
_erf = np.vectorize(math.erf, otypes=[float])


def ncdf(x):
    return 0.5 * (1 + _erf(np.asarray(x, float) / math.sqrt(2)))


def bs(S, K, T, sig, call):
    S, K, T, sig = (np.asarray(a, float) for a in (S, K, T, sig))
    T = np.maximum(T, 1e-6); sig = np.maximum(sig, 0.05)
    d1 = (np.log(S / K) + 0.5 * sig ** 2 * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    return S * ncdf(d1) - K * ncdf(d2) if call else K * ncdf(-d2) - S * ncdf(-d1)


def option_trade(c, iv, j, call):
    k = np.arange(0, HOLD + 1)
    pr = bs(c[j:j + HOLD + 1], c[j], (DTE - k) / 252, iv[j:j + HOLD + 1], call)
    if not np.isfinite(pr[0]) or pr[0] <= 0:
        return (np.nan,) * 3
    path = pr[1:] / pr[0] - 1
    if not np.all(np.isfinite(path)):
        return (np.nan,) * 3
    a = path[-1]
    b = 0.5 if (path >= 0.5).any() else a
    cc = 1.0 if (path >= 1.0).any() else a
    return a * 100, b * 100, cc * 100


# ------------------------------------------------------------------ outcome for one day
def outcome(d, j, sign):
    c, h, l, iv = d.c.values, d.h.values, d.l.values, d.iv.values
    c0 = c[j]; r = {}
    for n in H:
        r[f"x{n}"] = sign * (c[j + n] / c0 - 1) * 100 if j + n < len(c) else np.nan
    for n in (15, 20, 30):
        seg_l, seg_h = l[j + 1:j + n + 1], h[j + 1:j + n + 1]
        r[f"best{n}"] = (-(seg_l.min() / c0 - 1) if sign < 0 else (seg_h.max() / c0 - 1)) * 100
    seg = l[j + 1:j + 31] if sign < 0 else h[j + 1:j + 31]
    for p in (5, 7, 10):
        r[f"hit{p}"] = float((seg <= c0 * (1 - p / 100)).any()) if sign < 0 else float((seg >= c0 * (1 + p / 100)).any())
    r["opt_a"], r["opt_b"], r["opt_c"] = option_trade(c, iv, j, sign > 0)
    return r


METRICS = [f"x{n}" for n in H] + ["best15", "best20", "best30", "hit5", "hit7", "hit10", "opt_a", "opt_b", "opt_c"]


def baseline(d):
    out = {}
    rows = []
    for j in range(210, len(d) - 61):
        for s in (-1, 1):
            rows.append(dict(day=d.index[j], sign=s, **outcome(d, j, s)))
    b = pd.DataFrame(rows)
    for pn, a, z in PERIODS:
        m = (b.day >= a) & (b.day < z)
        for s in (-1, 1):
            x = b[m & (b.sign == s)]
            if len(x):
                out[(pn, s)] = x[METRICS].mean().to_dict()
    return out


def period_of(day):
    for pn, a, z in PERIODS:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


# ------------------------------------------------------------------ setups
def prep(d, ivser):
    d = d.copy()
    for n in (10, 20, 50, 200):
        d[f"s{n}"] = d.c.rolling(n).mean()
    delta = d.c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["rsi"] = 100 - 100 / (1 + up / dn)
    lr = np.log(d.c).diff()
    # stocks: blend of 20-day and 1-year realized vol x1.2. Pure 20-day vol made options look too cheap after
    # calm stretches (RSI 70 signals) and handed puts a fake edge on random-walk test data.
    rv = (0.5 * lr.rolling(20).std() + 0.5 * lr.rolling(252, min_periods=60).std()) * math.sqrt(252) * 1.2
    d["iv"] = (ivser.reindex(d.index).ffill() / 100).fillna(rv) if ivser is not None else rv
    return d


def add(out, setup, sign, sym, grp, d, j, base):
    if j < 210 or j + 61 >= len(d):
        return
    o = outcome(d, j, sign)
    b = base.get((period_of(d.index[j]), sign), {})
    out.append(dict(setup=setup, symbol=sym, group=grp, date=d.index[j], **o, **{f"ctrl_{k}": v for k, v in b.items()}))


def setups(sym, grp, d, out, base, calib):
    c, h = d.c, d.h
    s10, s20, s50, s200 = d.s10, d.s20, d.s50, d.s200
    gap = (s50 / s200 - 1) * 100
    bunch = (pd.concat([s10, s20, s50], axis=1).max(axis=1) - pd.concat([s10, s20, s50], axis=1).min(axis=1)) / c * 100
    gc = ((s50 > s200) & (s50.shift() <= s200.shift())).rolling(30, min_periods=1).max().astype(bool)
    into_gc = gc | ((s50 < s200) & (s50 >= s200 * 0.98) & (s50 > s50.shift(5)))
    for side, sign in (("down", -1), ("up", +1)):
        b3 = ((c < s10) & (c < s20) & (c < s50)) if side == "down" else ((c > s10) & (c > s20) & (c > s50))
        fire = b3 & ~b3.shift(2, fill_value=False)
        last = -99
        for j in np.where(fire.values)[0]:
            if j - last < 10 or j < 210 or j + 62 >= len(d):
                continue
            last = j
            if side == "up":
                add(out, "MA break UP -> calls", +1, sym, grp, d, j, base); continue
            add(out, "MA break DOWN: all", -1, sym, grp, d, j, base)
            if gap.iloc[j] >= 5 and not into_gc.iloc[j] and bunch.iloc[j] <= 2.5:
                add(out, "MA break DOWN: Taz version (50 5%+ over 200, no golden cross, bunched)", -1, sym, grp, d, j, base)
            if gap.iloc[j] >= 10:
                add(out, "MA break DOWN: 50 10%+ over the 200", -1, sym, grp, d, j, base)
            if c.iloc[j + 1] < c.iloc[j]:
                add(out, "MA break DOWN: next day lower (enter that close)", -1, sym, grp, d, j + 1, base)
            for q in range(j + 1, min(j + 8, len(d) - 62)):
                if h.iloc[q] >= s10.iloc[q] and c.iloc[q] < s10.iloc[q]:
                    add(out, "MA break DOWN: failed retest of the 10", -1, sym, grp, d, q, base); break
            if sym == "QQQ":
                calib.append((d.index[j], gap.iloc[j], bunch.iloc[j], bool(into_gc.iloc[j])))
    r = d.rsi.values
    for name, cond in (("RSI 70 -> puts", r >= 70), ("RSI 80 -> puts", r >= 80)):
        last = -99
        for j in np.where(cond)[0]:
            if j > 0 and not cond[j - 1] and j - last >= 10:
                add(out, name, -1, sym, grp, d, j, base); last = j


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


def check(x, m):
    e = x[m] - x[f"ctrl_{m}"]
    pe = [(per(x, a, b)[m] - per(x, a, b)[f"ctrl_{m}"]).mean() for _, a, b in PERIODS]
    t = tcl(e, x.date.values)
    ok = len(x) >= 100 and all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3
    return ok, pe, e.mean(), t


def report(E, calib):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    names = list(dict.fromkeys(E.setup))
    L = ["# Bearish setups — longer holds, best point in the window, put-option estimate", "",
         "Puts direction: positive = it fell. Random = the same measurement on EVERY day of that symbol and period, so "
         "QQQ's normal upward drift is already priced in. Edge = signal minus random. t clustered by month.", "",
         "## PASS CHECK (set before running): 100+ signals, positive in EVERY period, t >= 3 — on any of (A) close move at "
         "15/20/30/40 days, (B) dropped 5% within 30 days, (C) put option +50% target else day 20", "",
         "| Setup | Group | Signals | Passes on | Best evidence |", "|---|---|---|---|---|"]
    for s in names:
        for g in ("ETF", "MEGA"):
            x = E[(E.setup == s) & (E.group == g)]
            if not len(x):
                continue
            hits, best = [], None
            tries = [(f"x{n}", f"{n}-day close") for n in (15, 20, 30, 40)] + [("hit5", "dropped 5% in 30d")]
            if g == "ETF":   # stock option prices use realized vol, which tilted puts positive on random test data
                tries.append(("opt_b", "put +50% target"))
            for m, lab in tries:
                ok, pe, em, t = check(x, m)
                if ok:
                    hits.append(lab)
                if best is None or (pd.notna(t) and t > best[2]):
                    best = (lab, em, t, pe)
            ev = f"{best[0]}: {best[1]:+.2f} (t {best[2]:.1f}; periods {' / '.join('—' if pd.isna(p) else f'{p:+.2f}' for p in best[3])})" if best else "—"
            L.append(f"| {s} | {g} | {len(x)} | {'**' + ', '.join(hits) + '**' if hits else 'nothing'} | {ev} |")
    L += ["\n## 1. Close-to-close move your way, by holding period (edge vs random, t)\n",
          "| Setup | Group | " + " | ".join(f"{n}d" for n in H) + " |", "|---|---|" + "---|" * len(H)]
    for s in names:
        for g in ("ETF", "MEGA"):
            x = E[(E.setup == s) & (E.group == g)]
            if len(x) < 8:
                continue
            cells = [f"{(x[f'x{n}'] - x[f'ctrl_x{n}']).mean():+.2f} (t {tcl(x[f'x{n}'] - x[f'ctrl_x{n}'], x.date.values):.1f})" for n in H]
            L.append(f"| {s} | {g} | " + " | ".join(cells) + " |")
        x = E[(E.setup == s) & (E.symbol == "QQQ")]
        if len(x) >= 8:
            L.append(f"| {s} | QQQ alone ({len(x)}) | " + " | ".join(f"{(x[f'x{n}'] - x[f'ctrl_x{n}']).mean():+.2f}" for n in H) + " |")
    L += ["\n## 2. Best point inside the window, and how often it dumped (signal vs random)\n",
          "| Setup | Group | Deepest move your way: 15d / 20d / 30d | Dropped 5% in 30d | Dropped 7% | Dropped 10% |", "|---|---|---|---|---|---|"]
    for s in names:
        for g in ("ETF", "MEGA", "QQQ"):
            x = E[(E.setup == s) & ((E.group == g) if g != "QQQ" else (E.symbol == "QQQ"))]
            if len(x) < 8:
                continue
            best = " / ".join(f"{x[f'best{n}'].mean():.1f}% vs {x[f'ctrl_best{n}'].mean():.1f}%" for n in (15, 20, 30))
            hits = [f"{x[f'hit{p}'].mean():.0%} vs {x[f'ctrl_hit{p}'].mean():.0%} (t {tcl(x[f'hit{p}'] - x[f'ctrl_hit{p}'], x.date.values):.1f})" for p in (5, 7, 10)]
            L.append(f"| {s} | {g if g != 'QQQ' else 'QQQ alone'} ({len(x)}) | {best} | " + " | ".join(hits) + " |")
    L += ["\n## 3. Option estimate: at-the-money, 30 days to expiry, up to 20 trading days held\n",
          "| Setup | Group | Hold 20 days | +50% target else day 20 | +100% target else day 20 | Win rate (+50% rule) |", "|---|---|---|---|---|---|"]
    for s in names:
        for g in ("ETF", "MEGA", "QQQ"):
            x = E[(E.setup == s) & ((E.group == g) if g != "QQQ" else (E.symbol == "QQQ"))].dropna(subset=["opt_b"])
            if len(x) < 8:
                continue
            cells = [f"{x[m].mean():+.1f}% vs {x[f'ctrl_{m}'].mean():+.1f}% (t {tcl(x[m] - x[f'ctrl_{m}'], x.date.values):.1f})" for m in ("opt_a", "opt_b", "opt_c")]
            L.append(f"| {s} | {g if g != 'QQQ' else 'QQQ alone'} ({len(x)}) | " + " | ".join(cells) + f" | {(x.opt_b > 0).mean():.0%} |")
    # QQQ list
    q = E[(E.symbol == "QQQ") & (E.setup == "MA break DOWN: all")].sort_values("date")
    L += ["\n## QQQ triple breaks down — every one since 2018 (raw puts-direction moves)\n",
          "| Date | 10d | 15d | 20d | 30d | Deepest within 20d | Put +50% rule |", "|---|---|---|---|---|---|---|"]
    for r in q[q.date >= "2018-01-01"].itertuples():
        L.append(f"| {r.date:%Y-%m-%d} | {r.x10:+.1f}% | {r.x15:+.1f}% | {r.x20:+.1f}% | {r.x30:+.1f}% | {r.best20:+.1f}% | {r.opt_b:+.0f}% |")
    L += ["", f"Your QQQ dates: {', '.join(QQQ_DATES)} (see the list above for the break that matches each).",
          "", "Limits: option prices are Black-Scholes estimates, no bid/ask spread. Mega tech = known winners (makes puts look worse). "
          "Several horizons are checked; they overlap heavily, so they are not independent tries, but treat a single borderline pass with care."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    vol = {}
    for v in sorted(set(VOL_INDEX.values())):
        s = yahoo(v); time.sleep(1)
        vol[v] = s.c if s is not None else None
        print(f"  {v}: {'ok' if s is not None else 'missing (realized vol used)'}")
    E, calib = [], []
    for grp, syms in (("ETF", ETFS), ("MEGA", MEGA)):
        for s in syms:
            d = load(s)
            if d is None or len(d) < 400:
                print(f"  {s}: no data"); continue
            d = prep(d, vol.get(VOL_INDEX.get(s)))
            base = baseline(d)
            setups(s, grp, d, E, base, calib)
            print(f"  {s}: done, signals {len(E)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/events.csv.gz", index=False, compression="gzip")
    report(E, calib)


if __name__ == "__main__":
    main()
