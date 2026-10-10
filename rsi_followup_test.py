"""
RSI follow-up — turn the one pass (daily RSI 30 -> calls on ETFs) into a tradeable rule, and check the
near-miss on the other side (RSI 70/80 -> puts). Free (Yahoo daily back to 1999, Alpaca fallback 2016+).

1. Trade path (stock/ETF): how far it goes AGAINST you first (max adverse move in 10 days),
   whether +3% comes before -3%, days to +3%.
2. Entry variants: signal close / next open / first close back ABOVE 30 (confirmation) within 5 days.
3. Option estimate: buy the at-the-money option, ~21 days to expiry, priced with Black-Scholes.
   Implied vol = the real volatility index where one exists (VIX for SPY/DIA, VXN for QQQ/XLK/tech ETFs,
   RVX for IWM), updated every day, so the IV drop when the market bounces (vol crush) is included.
   Single stocks: 20-day realized vol x 1.2. Exits: (a) hold 10 days, (b) +50% target else day 10,
   (c) +50% target / -50% stop else day 10. Our earlier calibration found Black-Scholes too pessimistic
   on decay, so these are conservative, not exact.
4. Splits reported (not part of the pass): 50 over/under the 200, VIX under/over 25.

Comparison ('random') = the same option trade on every day of the same symbol and period.
PASS (set before running), for the bot: ETFs, RSI 30 -> calls, base entry, exit (b):
  average option return minus random > 0 in EVERY period (2000-15, 2016-21, 2022-26) AND t >= 3 (monthly clusters)
  AND 100+ trades.
The puts side is reported with the same rule but was a near miss before, so treat any pass there as a lead.
Out: results/rsi_followup/report.md, trades.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/rsi_followup"
ETFS = "QQQ SPY IWM DIA XLK SMH SOXX IGV XLC XLY FDN ARKK".split()
MEGA = "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split()
VOL_INDEX = {"SPY": "^VIX", "DIA": "^VIX", "IWM": "^RVX", "QQQ": "^VXN", "XLK": "^VXN", "SMH": "^VXN", "SOXX": "^VXN",
             "IGV": "^VXN", "FDN": "^VXN", "XLC": "^VXN", "XLY": "^VIX", "ARKK": "^VXN"}
PERIODS = (("2000-2015", "1999-01-01", "2016-01-01"), ("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))
DTE = 21


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


# ------------------------------------------------------------------ option pricing
_erf = np.vectorize(math.erf, otypes=[float])


def ncdf(x):
    return 0.5 * (1 + _erf(np.asarray(x, float) / math.sqrt(2)))


def bs(S, K, T, sig, call):
    S, K, T, sig = map(np.asarray, (S, K, T, sig))
    T = np.maximum(T, 1e-6); sig = np.maximum(sig, 0.05)
    d1 = (np.log(S / K) + 0.5 * sig ** 2 * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    return S * ncdf(d1) - K * ncdf(d2) if call else K * ncdf(-d2) - S * ncdf(-d1)


def option_trade(c, iv, j, call):
    """Buy ATM option at close j with DTE days left; price daily for 10 days. Returns returns for exits a/b/c."""
    S0 = c[j]; K = S0
    k = np.arange(0, 11)
    prices = bs(c[j:j + 11], K, (DTE - k) / 252, iv[j:j + 11], call)
    p0 = float(prices[0])
    if not np.isfinite(p0) or p0 <= 0:
        return None
    path = prices[1:] / p0 - 1
    if not np.all(np.isfinite(path)):
        return None
    a = path[-1]
    hit = np.where(path >= 0.5)[0]
    b = 0.5 if len(hit) else a
    stop = np.where(path <= -0.5)[0]
    if len(hit) and (not len(stop) or hit[0] <= stop[0]):
        cc = 0.5
    elif len(stop):
        cc = -0.5
    else:
        cc = a
    return a * 100, b * 100, cc * 100


# ------------------------------------------------------------------ build
def prep(d, ivser):
    d = d.copy()
    delta = d.c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["rsi"] = 100 - 100 / (1 + up / dn)
    d["s50"] = d.c.rolling(50).mean(); d["s200"] = d.c.rolling(200).mean()
    rv = np.log(d.c).diff().rolling(20).std() * math.sqrt(252) * 1.2
    if ivser is not None:
        iv = (ivser.reindex(d.index).ffill() / 100)
        d["iv"] = iv.fillna(rv)
    else:
        d["iv"] = rv
    return d


def path_stats(d, j, call):
    c0 = d.c.iloc[j]
    seg = d.iloc[j + 1:j + 11]
    if call:
        adverse = (seg.l.min() / c0 - 1) * 100
        up3 = np.where(seg.h.values >= c0 * 1.03)[0]; dn3 = np.where(seg.l.values <= c0 * 0.97)[0]
    else:
        adverse = -(seg.h.max() / c0 - 1) * 100
        up3 = np.where(seg.l.values <= c0 * 0.97)[0]; dn3 = np.where(seg.h.values >= c0 * 1.03)[0]
    first_good = up3[0] + 1 if len(up3) else np.nan
    good_first = float(len(up3) > 0 and (len(dn3) == 0 or up3[0] < dn3[0]))
    return adverse, first_good, good_first


def signals(d, kind):
    r = d.rsi.values
    cond = {"rsi30": r <= 30, "rsi70": r >= 70, "rsi80": r >= 80}[kind]
    out, last = [], -99
    for j in np.where(cond)[0]:
        if j > 0 and not cond[j - 1] and j - last >= 10:
            out.append(j); last = j
    return out


def run_symbol(sym, grp, d, rows, base_rows):
    c = d.c.values; iv = d.iv.values; o = d.o.values
    n = len(d)
    # random baseline: every valid day, both directions
    for j in range(210, n - 12, 1):
        if not np.isfinite(iv[j]):
            continue
        for call in (True, False):
            tr = option_trade(c, iv, j, call)
            if tr:
                base_rows.append((sym, grp, d.index[j], call, *tr))
    for kind, call in (("rsi30", True), ("rsi70", False), ("rsi80", False)):
        for j in signals(d, kind):
            if j < 210 or j + 12 >= n:
                continue
            entries = {"signal close": j}
            if call:
                back = [q for q in range(j + 1, min(j + 6, n - 12)) if d.rsi.iloc[q] > 30]
            else:
                back = [q for q in range(j + 1, min(j + 6, n - 12)) if d.rsi.iloc[q] < (70 if kind == "rsi70" else 80)]
            if back:
                entries["confirm (RSI back through the line)"] = back[0]
            for ename, q in entries.items():
                tr = option_trade(c, iv, q, call)
                if not tr:
                    continue
                adv, days, good_first = path_stats(d, q, call)
                sgn = 1 if call else -1
                rows.append(dict(symbol=sym, group=grp, kind=kind, entry=ename, date=d.index[q],
                                 move10=sgn * (c[q + 10] / c[q] - 1) * 100, adverse=adv, days_to_3=days, good_first=good_first,
                                 opt_hold=tr[0], opt_t50=tr[1], opt_t50s50=tr[2],
                                 trend="50 over 200" if d.s50.iloc[q] > d.s200.iloc[q] else "50 under 200",
                                 vix=iv[q] * 100))
            # next open entry (stock move only; options priced at close)
            if j + 11 < n:
                rows.append(dict(symbol=sym, group=grp, kind=kind, entry="next open (stock only)", date=d.index[j + 1],
                                 move10=(1 if call else -1) * (c[j + 10] / o[j + 1] - 1) * 100))


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


def report(T, B):
    T = T.copy(); T["date"] = pd.to_datetime(T.date); B = B.copy(); B["date"] = pd.to_datetime(B.date)
    base = {}
    for (g, call), x in B.groupby(["group", "call"]):
        for pn, a, b in PERIODS:
            y = per(x, a, b)
            if len(y):
                base[(g, call, pn)] = y[["a", "b", "c"]].mean().to_dict()

    def edge(x, col, call):
        key = {"opt_hold": "a", "opt_t50": "b", "opt_t50s50": "c"}[col]
        e = []
        for r in x.itertuples():
            pn = next(p for p, a, b in PERIODS if pd.Timestamp(a) <= r.date < pd.Timestamp(b))
            e.append(getattr(r, col) - base.get((r.group, call, pn), {}).get(key, np.nan))
        return pd.Series(e, index=x.index)

    L = ["# RSI follow-up — trade path and option estimates", "",
         "Option = buy at-the-money, ~21 days to expiry, priced with Black-Scholes using the real volatility index "
         "(VIX/VXN/RVX) day by day for ETFs, realized vol x1.2 for stocks. Random = the same option trade on every day "
         "of that symbol and period. Edge = signal minus random. t clustered by month.", ""]
    L += ["## PASS CHECK (set before running): exit (b) +50% target else day 10; edge > 0 every period, t >= 3, 100+ trades", "",
          "| Signal | Group | Entry | Edge 2000-15 / 16-21 / 22-26 | All years | Verdict |", "|---|---|---|---|---|---|"]
    for kind, call, lab in (("rsi30", True, "RSI 30 → calls"), ("rsi70", False, "RSI 70 → puts"), ("rsi80", False, "RSI 80 → puts")):
        for g in ("ETF", "MEGA"):
            for ent in ("signal close", "confirm (RSI back through the line)"):
                x = T[(T.kind == kind) & (T.group == g) & (T.entry == ent)]
                if not len(x):
                    continue
                e = edge(x, "opt_t50", call)
                pe = [e[(x.date >= a) & (x.date < b)].mean() for _, a, b in PERIODS]
                t = tcl(e, x.date.values)
                ok = all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3 and len(x) >= 100
                L.append(f"| {lab} | {g} | {ent} | {' / '.join('—' if pd.isna(p) else f'{p:+.1f}%' for p in pe)} | "
                         f"{e.mean():+.1f}% (t {t:.1f}, n {len(x)}) | {'**PASS**' if ok else 'fail'} |")
    for kind, call, lab in (("rsi30", True, "RSI 30 → CALLS"), ("rsi70", False, "RSI 70 → PUTS"), ("rsi80", False, "RSI 80 → PUTS")):
        X = T[(T.kind == kind) & (T.entry != "next open (stock only)")]
        L += [f"\n## {lab}\n", "### Option estimate (average return per trade, and vs random)\n",
              "| Group / split | Entry | Trades | Hold 10 days | +50% target else day 10 | +50% target / −50% stop | Win rate (b) | Random (b) |",
              "|---|---|---|---|---|---|---|---|"]
        for g in ("ETF", "MEGA"):
            for ent in ("signal close", "confirm (RSI back through the line)"):
                x = X[(X.group == g) & (X.entry == ent)]
                if not len(x):
                    continue
                splits = [("all", x)] + [(s, x[x.trend == s]) for s in ("50 over 200", "50 under 200")]
                if g == "ETF":
                    splits += [("vol index under 25", x[x.vix < 25]), ("vol index 25+", x[x.vix >= 25])]
                splits += [(f"{s} only", x[x.symbol == s]) for s in (["QQQ"] if g == "ETF" else [])]
                for lab2, y in splits:
                    if len(y) < 5:
                        continue
                    cells = []
                    for col in ("opt_hold", "opt_t50", "opt_t50s50"):
                        e = edge(y, col, call)
                        cells.append(f"{y[col].mean():+.1f}% (edge {e.mean():+.1f}, t {tcl(e, y.date.values):.1f})")
                    rb = np.nanmean([base.get((g, call, next(p for p, a, b in PERIODS if pd.Timestamp(a) <= dd < pd.Timestamp(b))), {}).get("b", np.nan) for dd in y.date])
                    L.append(f"| {g}: {lab2} | {ent} | {len(y)} | {cells[0]} | {cells[1]} | {cells[2]} | {(y.opt_t50 > 0).mean():.0%} | {rb:+.1f}% |")
        L += ["\n### Path (the stock/ETF itself, 10 days after entry)\n",
              "| Group | Entry | Trades | Avg move your way | Worst move against you: median / 75th pct / 90th pct | +3% your way before −3% against | Median days to +3% |",
              "|---|---|---|---|---|---|---|"]
        for g in ("ETF", "MEGA"):
            for ent in ("signal close", "confirm (RSI back through the line)"):
                y = X[(X.group == g) & (X.entry == ent)]
                if len(y):
                    L.append(f"| {g} | {ent} | {len(y)} | {y.move10.mean():+.2f}% | {y.adverse.median():+.1f}% / {y.adverse.quantile(.25):+.1f}% / "
                             f"{y.adverse.quantile(.10):+.1f}% | {y.good_first.mean():.0%} | {y.days_to_3.median():.0f} |")
            y = T[(T.kind == kind) & (T.group == g) & (T.entry == "next open (stock only)")]
            if len(y):
                L.append(f"| {g} | next open (stock only) | {len(y)} | {y.move10.mean():+.2f}% | — | — | — |")
    q = T[(T.symbol == "QQQ") & (T.kind == "rsi30") & (T.entry == "signal close")].sort_values("date")
    L += ["\n## QQQ RSI 30 signals (every one)\n", "| Date | VXN | Trend | 10-day move | Worst against | Option: hold 10d | +50% else day 10 | +50%/−50% |",
          "|---|---|---|---|---|---|---|---|"]
    for r in q.itertuples():
        L.append(f"| {r.date:%Y-%m-%d} | {r.vix:.0f} | {r.trend} | {r.move10:+.1f}% | {r.adverse:+.1f}% | {r.opt_hold:+.0f}% | {r.opt_t50:+.0f}% | {r.opt_t50s50:+.0f}% |")
    L += ["", "Limits: option prices are Black-Scholes estimates (no bid/ask spread, earlier calibration says too pessimistic on decay). "
          "Real fills on QQQ/SPY options are tight; on smaller ETFs and in panics, spreads widen. Mega tech = known winners."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    vol = {}
    for v in sorted(set(VOL_INDEX.values())):
        s = yahoo(v); time.sleep(1)
        vol[v] = s.c if s is not None else None
        print(f"  {v}: {'ok' if s is not None else 'missing (falls back to realized vol)'}")
    rows, base_rows = [], []
    for grp, syms in (("ETF", ETFS), ("MEGA", MEGA)):
        for s in syms:
            d = load(s)
            if d is None or len(d) < 400:
                print(f"  {s}: no data"); continue
            d = prep(d, vol.get(VOL_INDEX.get(s)))
            run_symbol(s, grp, d, rows, base_rows)
            print(f"  {s}: done, trades {len(rows)}", flush=True)
    T = pd.DataFrame(rows)
    B = pd.DataFrame(base_rows, columns=["symbol", "group", "date", "call", "a", "b", "c"])
    T.to_csv(f"{OUT}/trades.csv.gz", index=False, compression="gzip")
    report(T, B)


if __name__ == "__main__":
    main()
