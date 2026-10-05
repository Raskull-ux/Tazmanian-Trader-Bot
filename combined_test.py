"""
Combined test — strike (delta) + fast exit, on every trade with a usable time
==========================================================================
Better than throwing away uncertain times: a recovered fill comes with a window of
"candidate minutes" (minutes when the contract traded at Taz's exact price; the real
minute was inside that window in 100% of the validation checks). So instead of one
guessed minute, each recovered trade is evaluated at EVERY candidate minute and the
results are averaged. Bounds (worst / best candidate) are reported too.

Before any result is trusted, the method is checked on fills whose real time IS known:
the candidate-average result is compared with the result at the true minute.

Trades used:
  A. 576 Robinhood trades with exact fill times (Apr 2024 - Apr 2026)
  B. recovered buy fills, Nov 2025 - Apr 2026 (Webull, Bebo, untimed Robinhood)
Option prices: real 1-minute OPRA bars already in the repo (no new Databento spend).
Stock prices: Alpaca 1-minute (free), unadjusted.

PRIMARY TEST (set before running): delta >= 0.30 at entry + exit after 15 minutes.
PASS = average return > 0 in BOTH the older half and the newer half of trades.

Out: results/combined_test/{report.md, trades.csv}
"""
from __future__ import annotations
import os, glob, math
import numpy as np, pandas as pd
from scipy.special import ndtr
from scipy.optimize import brentq
import setup_backtest as sb
import strike_study as ss

OUT = "results/combined_test"
ET = sb.NY
EXITS = {"15 min": 15, "30 min": 30, "60 min": 60, "close": None}


# ------------------------------------------------------------------ option bars
def load_option_bars():
    bars = {}
    for f in glob.glob("results_minute/bar_cache/*.pkl.gz") + glob.glob("results/recovered_times/bar_cache/*.pkl.gz"):
        try:
            d = pd.read_pickle(f)
        except Exception:
            continue
        if d is None or len(d) == 0:
            continue
        d = d.reset_index()
        d["t"] = pd.to_datetime(d.ts_event, utc=True).dt.tz_convert(ET).dt.tz_localize(None).dt.floor("min")
        d["occ"] = d.symbol.astype(str).str.replace(" ", "")
        g = d.groupby(["occ", "t"]).agg(high=("high", "max"), low=("low", "min"),
                                        close=("close", "median"), volume=("volume", "sum")).reset_index()
        for o, x in g.groupby("occ"):
            bars.setdefault(o, []).append(x[["t", "high", "low", "close", "volume"]])
    return {o: pd.concat(v).drop_duplicates("t").sort_values("t").reset_index(drop=True) for o, v in bars.items()}


def occ_nospace(sym, exp, put, strike):
    return f"{str(sym).upper()}{pd.Timestamp(exp):%y%m%d}{'P' if put else 'C'}{int(round(strike * 1000)):08d}"


# ------------------------------------------------------------------ trades
def load_trades():
    rows = []
    m = pd.read_csv("results_minute/minute_trades.csv")
    m = m[m.status == "ok"]
    for _, r in m.iterrows():
        t = pd.Timestamp(r.entry).tz_convert(ET).tz_localize(None) if pd.Timestamp(r.entry).tzinfo else pd.Timestamp(r.entry)
        occ = str(r.occ).replace(" ", "")
        rows.append(dict(src="exact", account="Robinhood-main", occ=occ, symbol=occ[:-15], put=occ[-9] == "P",
                         strike=int(occ[-8:]) / 1000, expiry=pd.to_datetime(occ[-15:-9], format="%y%m%d"),
                         day=t.normalize(), price=r.px_in, cands=[t.floor("min")], actual=r.realized, span=0.0))
    f = pd.read_csv("results/recovered_times/fills_with_times.csv")
    pos = pd.read_csv("results/strike_study/positions.csv", parse_dates=["entry", "expiry"])
    pos["occ"] = [occ_nospace(a, b, c, d) for a, b, c, d in zip(pos.symbol, pos.expiry, pos.put, pos.strike)]
    pos_ret = pos.set_index(["account", "occ", "entry"])["ret"].to_dict()
    for _, r in f[(f.role == "recover") & (f.status == "ok") & (f.Side.astype(str).str.upper() == "BUY")].iterrows():
        occ = str(r.occ).replace(" ", "")
        day = pd.Timestamp(r.Date).normalize()
        actual = pos_ret.get((r.Account, occ, day), np.nan)
        rows.append(dict(src="recovered", account=r.Account, occ=occ, symbol=occ[:-15], put=occ[-9] == "P",
                         strike=int(occ[-8:]) / 1000, expiry=pd.to_datetime(occ[-15:-9], format="%y%m%d"),
                         day=day, price=float(r.Price), cands=None, first=pd.Timestamp(r["first"]),
                         last=pd.Timestamp(r["last"]), actual=actual, span=float(r.span_min)))
    val = f[(f.role == "validate") & (f.status == "ok") & (f.Side.astype(str).str.upper() == "BUY")]
    return pd.DataFrame(rows), val


def candidate_minutes(b, day, price, first=None, last=None):
    x = b[(b.t.dt.normalize() == day) & (b.low <= price + 1e-9) & (b.high >= price - 1e-9) & (b.volume > 0)]
    if first is not None:
        x = x[(x.t >= first) & (x.t <= last)]
    return list(x.t)


def exit_returns(b, t, price):
    day_bars = b[(b.t.dt.normalize() == t.normalize()) & (b.t > t)]
    out = {}
    for name, mins in EXITS.items():
        x = day_bars[day_bars.t <= (t + pd.Timedelta(minutes=mins) if mins else t.normalize() + pd.Timedelta(hours=15, minutes=55))]
        out[name] = x.close.iloc[-1] / price - 1 if len(x) else np.nan
    return out


# ------------------------------------------------------------------ stock prices + delta
def stock_minutes(T):
    need = T.groupby("day").symbol.apply(lambda s: sorted(set(s))).to_dict()
    px = {}
    for k, (day, syms) in enumerate(sorted(need.items())):
        s = (day + pd.Timedelta(hours=9, minutes=30)).tz_localize(ET).isoformat()
        e = (day + pd.Timedelta(hours=16)).tz_localize(ET).isoformat()
        for i in range(0, len(syms), 50):
            try:
                d = ss.fetch_raw(syms[i:i + 50], "1Min", s, e)
            except Exception as ex:
                print("  stock fetch", day.date(), str(ex)[:80]); continue
            for sym, g in d.groupby("symbol"):
                g = g.assign(t=g.t.dt.tz_localize(None).dt.floor("min"))
                px[(sym, day)] = g.set_index("t").c.sort_index()
        if (k + 1) % 50 == 0:
            print(f"  stock minutes: {k + 1}/{len(need)} days", flush=True)
    return px


def delta_at(S, K, expiry, t, price, put):
    mins = max(16 * 60 - (t.hour * 60 + t.minute), 5)
    T = (mins + 390 * np.busday_count(t.date(), expiry.date())) / (390 * 252)
    iv = ss.implied(S, K, T, price, put)
    if not iv == iv:
        return np.nan
    _, d1 = ss.bs(S, K, T, iv, put)
    return abs(ndtr(d1) - (1 if put else 0))


# ------------------------------------------------------------------ main
def main():
    os.makedirs(OUT, exist_ok=True)
    bars = load_option_bars()
    T, val = load_trades()
    print(f"Option contracts with minute bars: {len(bars)} | trades: {len(T)} "
          f"({T.src.value_counts().to_dict()}) | validation buys: {len(val)}", flush=True)
    px = stock_minutes(T)

    rows = []
    for _, r in T.iterrows():
        b = bars.get(r.occ)
        if b is None:
            continue
        cands = r.cands if r.src == "exact" else candidate_minutes(b, r.day, r.price, r["first"], r["last"])
        if not cands:
            continue
        s = px.get((r.symbol, r.day))
        per = []
        for t in cands:
            ex = exit_returns(b, t, r.price)
            S = np.nan
            if s is not None:
                k = s.index.searchsorted(t, side="right") - 1
                if k >= 0:
                    S = s.iloc[k]
            ex["delta"] = delta_at(S, r.strike, r.expiry, t, r.price, r.put) if S == S else np.nan
            per.append(ex)
        P = pd.DataFrame(per)
        out = dict(src=r.src, account=r.account, occ=r.occ, day=r.day, actual=r.actual, n_cands=len(cands),
                   span=r.span, narrow=(r.src == "exact") or (r.span <= 15),
                   delta=P.delta.median(), delta_min=P.delta.min())
        for name in EXITS:
            out[name] = P[name].mean(); out[name + "_worst"] = P[name].min(); out[name + "_best"] = P[name].max()
        rows.append(out)
    R = pd.DataFrame(rows).sort_values("day").reset_index(drop=True)
    R.to_csv(f"{OUT}/trades.csv", index=False)

    # validation: candidate-average vs true-minute result, on fills with known times
    vrows = []
    for _, v in val.iterrows():
        occ = str(v.occ).replace(" ", ""); b = bars.get(occ)
        if b is None or pd.isna(v.true_t):
            continue
        day = pd.Timestamp(v.Date).normalize(); true_t = pd.Timestamp(v.true_t).floor("min")
        cands = candidate_minutes(b, day, float(v.Price))
        if not cands:
            continue
        tr = exit_returns(b, true_t, float(v.Price))["15 min"]
        avg = np.nanmean([exit_returns(b, t, float(v.Price))["15 min"] for t in cands])
        vrows.append(dict(true=tr, cand_avg=avg))
    V = pd.DataFrame(vrows).dropna()
    report(R, V)


def stat(x):
    x = x.dropna()
    if len(x) < 3:
        return dict(n=len(x), avg=np.nan, win=np.nan, t=np.nan)
    v = x.clip(upper=5)
    return dict(n=len(v), avg=v.mean(), win=(v > 0).mean(), t=np.nan)


def cell(df, col):
    x = df[[col, "day"]].dropna()
    if len(x) < 3:
        return "—"
    v = x[col].clip(upper=5)
    dm = v.groupby(x.day.values).mean()
    t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")
    return f"{v.mean()*100:+.1f}% / {(v > 0).mean():.0%} win (t {t:.1f}, n {len(v)})"


def table(df, title):
    L = [f"\n### {title}\n", "| Delta at entry | What you did | Out at 15 min | 30 min | 60 min | At the close |",
         "|---|---|---|---|---|---|"]
    for lab, m in (("under 0.30", df.delta < 0.30), ("0.30 and up", df.delta >= 0.30)):
        x = df[m]
        L.append(f"| {lab} | {cell(x, 'actual')} | {cell(x, '15 min')} | {cell(x, '30 min')} | "
                 f"{cell(x, '60 min')} | {cell(x, 'close')} |")
    return L


def report(R, V):
    L = ["# Combined test — strike + fast exit",
         f"\n{len(R)} trades: {int((R.src == 'exact').sum())} with exact fill times, "
         f"{int((R.src == 'recovered').sum())} recovered ({int(((R.src == 'recovered') & R.narrow).sum())} narrow-window). "
         "Each cell: average return / win rate (t clustered by day, n). Returns capped at +500% per trade.\n"]
    if len(V):
        diff = V.cand_avg - V.true
        L += ["## 1. Method check (fills with known times)\n",
              f"- Fills checked: {len(V)}",
              f"- 15-min result at the TRUE minute, average: {V.true.mean()*100:+.1f}%",
              f"- 15-min result averaged over candidate minutes: {V.cand_avg.mean()*100:+.1f}%",
              f"- Average gap (candidate-average minus true): {diff.mean()*100:+.1f} pts; correlation {V.true.corr(V.cand_avg):.2f}",
              "- A gap near 0 means candidate-averaging gives the right answer on average, even when the exact minute is unknown."]
    L += ["\n## 2. Results"] + table(R, "All trades") + table(R[R.narrow], "Precise only (exact times + narrow recovered windows)") + \
         table(R[R.src == "recovered"], "Recovered only (Nov 2025 - Apr 2026, all accounts)")
    best = R[(R.day >= "2025-11-01") & (R.day <= "2026-04-30")]
    L += table(best, "Best run only (Nov 2025 - Apr 2026)")
    # primary pre-registered test
    P = R[R.delta >= 0.30].reset_index(drop=True)
    half = len(P) // 2
    a, b = P.iloc[:half], P.iloc[half:]
    ra, rb = a["15 min"].clip(upper=5).mean(), b["15 min"].clip(upper=5).mean()
    verdict = "PASS" if ra > 0 and rb > 0 else "FAIL"
    pp = R[R.narrow & (R.delta >= 0.30)].reset_index(drop=True); h2 = len(pp) // 2
    pa, pb = pp.iloc[:h2]["15 min"].clip(upper=5).mean(), pp.iloc[h2:]["15 min"].clip(upper=5).mean()
    wc = P["15 min_worst"].clip(upper=5).mean()
    L += ["\n## 3. PRIMARY TEST (set before running): delta >= 0.30 + exit at 15 minutes\n",
          f"- Older half ({len(a)} trades, {a.day.min():%b %Y} - {a.day.max():%b %Y}): **{ra*100:+.1f}%** per trade",
          f"- Newer half ({len(b)} trades, {b.day.min():%b %Y} - {b.day.max():%b %Y}): **{rb*100:+.1f}%** per trade",
          f"- **Verdict: {verdict}** (pass = positive in both halves)",
          f"- Same test on precise trades only: older {pa*100:+.1f}%, newer {pb*100:+.1f}%",
          f"- Worst-case bound (every recovered trade at its WORST candidate minute): {wc*100:+.1f}% per trade",
          "\nNotes: option prices are trade prints, not bid/ask, so real fills would be slightly worse; "
          "the 15-minute exit uses the last trade at or before 15 minutes."]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
