"""
Recover missing fill times — Nov 2025 to Apr 2026 (Taz's best run), all accounts.

Webull and Bebo never record fill times, and some Robinhood fills have none.
For every fill without a time, this downloads that contract's real 1-minute
OPRA prices for that day (Databento) and finds the minutes in which the contract
traded at Taz's exact fill price. That pins the fill to a minute or a short window.

Validation first: the same method is run on Robinhood fills whose real time IS
known, and the report shows how far off the recovered time is. Recovered times
are only worth using if that error is small.

One request per trading day (all of that day's contracts together), every
download cached in the repo, hard spending cap MAX_COST_USD (default 10).

Out: results/recovered_times/{fills_with_times.csv, report.md}
"""
import os, sys, glob, time, hashlib
import numpy as np, pandas as pd
try:
    import databento as db
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "databento"]); import databento as db

ET = "America/New_York"
OUT, CACHE = "results/recovered_times", "results/recovered_times/bar_cache"
START, END = "2025-11-01", "2026-04-30"
MAX_COST = float(os.environ.get("MAX_COST_USD", "10"))
VALIDATE_DAYS = int(os.environ.get("VALIDATE_DAYS", "40"))   # days of known-time fills to check against


def osi(sym, exp, put, strike):
    return f"{str(sym).upper():<6}{pd.Timestamp(exp):%y%m%d}{'P' if put else 'C'}{int(round(strike * 1000)):08d}"


def load_fills():
    path = sorted(glob.glob("Tazmanian_Trade_Record*.xlsx"))[-1]
    r = pd.read_excel(path, "Raw Fills (All Accounts)", header=3)
    r["Date"] = pd.to_datetime(r["Date"]).dt.normalize()
    r = r[(r.Date >= START) & (r.Date <= END)].copy()
    r["Expiry"] = pd.to_datetime(r["Expiry"], errors="coerce")
    r = r.dropna(subset=["Expiry", "Strike", "Price"])
    r["put"] = r["Type"].astype(str).str.lower().str.startswith("p")
    r["occ"] = [osi(s, e, p, k) for s, e, p, k in zip(r.Symbol, r.Expiry, r.put, r.Strike)]
    r["has_time"] = r["Time (ET)"].notna()
    r["true_t"] = pd.NaT
    m = r.has_time
    r.loc[m, "true_t"] = pd.to_datetime(r.loc[m, "Date"].dt.strftime("%Y-%m-%d") + " " +
                                       r.loc[m, "Time (ET)"].astype(str), errors="coerce")
    return r.reset_index(drop=True)


def retry(fn, what, n=5):
    for k in range(n):
        try:
            return fn()
        except Exception as e:
            if k == n - 1:
                raise
            w = min(60, 5 * 2 ** k); print(f"   {what}: {str(e)[:80]} -> retry in {w}s", flush=True); time.sleep(w)


def day_bars(client, day, occs, spent):
    key = hashlib.md5((str(day.date()) + ",".join(sorted(occs))).encode()).hexdigest()[:16]
    cp = os.path.join(CACHE, key + ".pkl.gz")
    if os.path.exists(cp):
        return pd.read_pickle(cp), 0.0
    s = (day + pd.Timedelta(hours=9, minutes=30)).tz_localize(ET).tz_convert("UTC")
    e = (day + pd.Timedelta(hours=16, minutes=15)).tz_localize(ET).tz_convert("UTC")
    kw = dict(dataset="OPRA.PILLAR", schema="ohlcv-1m", stype_in="raw_symbol",
              symbols=sorted(occs), start=s, end=e)
    c = retry(lambda: client.metadata.get_cost(**kw), f"{day.date()} cost")
    if spent + c > MAX_COST:
        return None, c
    df = retry(lambda: client.timeseries.get_range(**kw).to_df(), f"{day.date()} download")
    df = df.reset_index()
    df.to_pickle(cp)
    return df, c


def locate(bars, price):
    """Minutes whose traded range contains the fill price."""
    if bars is None or bars.empty:
        return None
    hit = bars[(bars.low <= price + 1e-9) & (bars.high >= price - 1e-9) & (bars.volume > 0)]
    if hit.empty:
        return dict(status="price never traded", n=0)
    # best guess: the candidate minute whose close is nearest the fill, ties -> most volume
    h = hit.assign(d=(hit.close - price).abs()).sort_values(["d", "volume"], ascending=[True, False])
    return dict(status="ok", n=len(hit), first=hit.t.min(), last=hit.t.max(), guess=h.t.iloc[0],
                span_min=(hit.t.max() - hit.t.min()).total_seconds() / 60)


def main():
    os.makedirs(CACHE, exist_ok=True)
    F = load_fills()
    need = F[~F.has_time]
    known = F[F.has_time & F.true_t.notna()]
    val_days = sorted(known.Date.unique())[-VALIDATE_DAYS:] if len(known) else []
    known = known[known.Date.isin(val_days)]
    print(f"Best-run fills: {len(F)} | without time: {len(need)} "
          f"({need.Account.value_counts().to_dict()}) | validation fills with known time: {len(known)}", flush=True)
    client = db.Historical(os.environ["DATABENTO_API_KEY"].strip())
    work = pd.concat([need.assign(role="recover"), known.assign(role="validate")])
    days = sorted(work.Date.unique())
    # validation days first, so the accuracy check is never the part cut by the cost cap
    days = [d for d in days if d in set(val_days)] + [d for d in days if d not in set(val_days)]
    spent, rows = 0.0, []
    print(f"Databento 1-minute, {len(days)} trading days, hard stop ${MAX_COST:.0f}", flush=True)
    for j, day in enumerate(days, 1):
        g = work[work.Date == day]
        try:
            df, c = day_bars(client, pd.Timestamp(day), set(g.occ), spent)
        except Exception as ex:
            print(f"   {pd.Timestamp(day).date()} failed: {str(ex)[:120]}", flush=True); continue
        if df is None:
            print(f"STOP: cost cap reached at day {j}/{len(days)} (next day would cost ${c:.2f}).", flush=True); break
        spent += c
        if not df.empty:
            df["t"] = pd.to_datetime(df.ts_event, utc=True).dt.tz_convert(ET).dt.tz_localize(None)
        for _, f in g.iterrows():
            b = df[df.symbol == f.occ] if not df.empty else None
            res = locate(b, f.Price) or dict(status="no bars", n=0)
            rows.append({**f.to_dict(), **res})
        if j % 10 == 0:
            print(f"  day {j}/{len(days)} | spent ${spent:.2f}", flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(f"{OUT}/fills_with_times.csv", index=False)

    L = ["# Recovered fill times — Nov 2025 to Apr 2026", f"\nSpent this run: ${spent:.2f} (cap ${MAX_COST:.0f}).\n"]
    v = R[(R.role == "validate") & (R.status == "ok")].copy()
    if len(v):
        v["err"] = (v.guess - pd.to_datetime(v.true_t)).abs().dt.total_seconds() / 60
        v["inside"] = (pd.to_datetime(v.true_t) >= v["first"] - pd.Timedelta(minutes=1)) & \
                      (pd.to_datetime(v.true_t) <= v["last"] + pd.Timedelta(minutes=1))
        L += ["## 1. Accuracy check on fills whose real time is known\n",
              f"- Fills checked: {len(v)} (of {int((R.role == 'validate').sum())})",
              f"- Recovered time within 5 min of the real time: {(v.err <= 5).mean():.0%}",
              f"- Within 15 min: {(v.err <= 15).mean():.0%} | within 30 min: {(v.err <= 30).mean():.0%}",
              f"- Median error: {v.err.median():.0f} min",
              f"- Real time inside the recovered window: {v.inside.mean():.0%}",
              f"- Among fills whose window was narrow (all candidate minutes within 15 min): "
              f"{(v[v.span_min <= 15].err <= 5).mean():.0%} within 5 min, n={int((v.span_min <= 15).sum())}"]
    rc = R[R.role == "recover"]
    if len(rc):
        ok = rc[rc.status == "ok"]
        L += ["\n## 2. Recovered fills (no time on record)\n",
              "| Account | Fills | Found | Narrow window (<=15 min) | Wide window |", "|---|---|---|---|---|"]
        for a, g in rc.groupby("Account"):
            o = g[g.status == "ok"]
            L.append(f"| {a} | {len(g)} | {len(o)} | {int((o.span_min <= 15).sum())} | {int((o.span_min > 15).sum())} |")
        L.append(f"\nNot found: {rc.status.ne('ok').sum()} ({rc[rc.status != 'ok'].status.value_counts().to_dict()})")
    L.append("\nUse rule (set before running): recovered times are used in the next tests only if the accuracy "
             "check shows a median error of 15 minutes or less; narrow-window fills first.")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
