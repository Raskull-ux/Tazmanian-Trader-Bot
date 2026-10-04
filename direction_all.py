"""
Direction test — ALL accounts (Robinhood, Webull, Bebo), 2019-2026, from Raw Fills.
Fill times exist only for part of Robinhood, so this works on dates:
each option position (account + contract) is dated by its first buy, and the stock's move
in the trade's direction is measured two ways:
  from the OPEN of the entry day   (as if you entered early)
  from the CLOSE of the entry day  (ignores the entry-day move entirely)
to the entry-day close, next close, 3-day close, 5-day close.
Also shown 'vs SPY': the stock's move minus SPY's move, so a bull market's upward drift
doesn't count against puts. Real option result per position is shown alongside.
Free: Alpaca daily bars only.
"""
import os, glob, math
import numpy as np, pandas as pd
import setup_backtest as sb

OUT = "results/direction_all"


def positions():
    path = sorted(glob.glob("Tazmanian_Trade_Record*.xlsx"))[-1]
    r = pd.read_excel(path, "Raw Fills (All Accounts)", header=3)
    r["Date"] = pd.to_datetime(r["Date"]).dt.date
    r["Expiry"] = pd.to_datetime(r["Expiry"], errors="coerce").dt.date
    r["Side"] = r["Side"].astype(str).str.upper()
    r["put"] = r["Type"].astype(str).str.lower().str.startswith("p")
    r["cash"] = r["Qty"] * r["Price"] * 100
    k = ["Account", "Symbol", "Expiry", "put", "Strike"]
    rows = []
    for key, g in r.groupby(k):
        b, s = g[g.Side == "BUY"], g[g.Side == "SELL"]
        if b.empty:
            continue
        bq, sq = b.Qty.sum(), s.Qty.sum()
        cost, proceeds = b.cash.sum(), s.cash.sum()
        if sq > bq:                      # partial history: scale proceeds to bought qty
            proceeds *= bq / sq
        rows.append(dict(account=key[0], symbol=str(key[1]).upper(), expiry=key[2], put=key[3],
                         entry=b.Date.min(), opt_ret=proceeds / cost - 1 if cost > 0 else np.nan,
                         net=proceeds - cost))
    P = pd.DataFrame(rows)
    P["dte"] = [(e - d).days if pd.notna(e) else np.nan for e, d in zip(P.expiry, P.entry)]
    return P


def main():
    os.makedirs(OUT, exist_ok=True)
    P = positions()
    start = (pd.Timestamp(min(P.entry)) - pd.Timedelta(days=5)).date().isoformat()
    # Free Alpaca plan only serves SIP data older than 15 minutes: never ask past (now - 20 min)
    cap = pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)
    end = min(pd.Timestamp(max(P.entry)).tz_localize("UTC") + pd.Timedelta(days=14), cap).isoformat()
    syms = sorted(set(P.symbol) | {"SPY"})
    D = {}
    for i in range(0, len(syms), 50):
        ch = syms[i:i + 50]
        try:
            d = sb.fetch(ch, "1Day", start, end)
        except Exception as ex:
            print("fetch", ch[:3], ex); continue
        for s in ch:
            x = d[d.symbol == s].copy()
            if len(x):
                x["day"] = x["t"].dt.tz_convert(sb.NY).dt.date
                D[s] = x.sort_values("day").reset_index(drop=True)
        print(f"  {min(i + 50, len(syms))}/{len(syms)}")
    if "SPY" not in D:
        raise SystemExit("SPY prices could not be downloaded; see the fetch errors above.")
    spy = D["SPY"].set_index("day")
    rows = []
    for _, p in P.iterrows():
        x = D.get(p.symbol)
        if x is None:
            continue
        x = x[x.day >= p.entry].reset_index(drop=True)
        if x.empty or x.day.iloc[0] != p.entry or len(x) < 6:
            continue
        sg = -1 if p.put else 1
        o0, c0 = x.o.iloc[0], x.c.iloc[0]
        r = p.to_dict(); r["year"] = p.entry.year
        for n, nm in ((0, "day"), (1, "next"), (3, "d3"), (5, "d5")):
            cn = x.c.iloc[n]; dn = x.day.iloc[n]
            r[f"open_{nm}"] = sg * (cn / o0 - 1) * 100
            if n > 0:
                r[f"close_{nm}"] = sg * (cn / c0 - 1) * 100
            if p.entry in spy.index and dn in spy.index:
                s_ref = spy.loc[p.entry, "o"]
                r[f"xspy_{nm}"] = sg * ((cn / o0 - 1) - (spy.loc[dn, "c"] / s_ref - 1)) * 100
        rows.append(r)
    R = pd.DataFrame(rows); R.to_csv(f"{OUT}/positions.csv", index=False)

    # Same ticker + same day + same direction is ONE call, not several (multiple strikes/accounts).
    R = R.drop_duplicates(["symbol", "entry", "put"]).reset_index(drop=True)

    def cell(v, g):
        ok = v.notna()
        v, dates = v[ok], g.loc[ok, "entry"]
        if len(v) < 3:
            return " — |"
        # t-stat clustered by entry date: calls made the same day share the same market move
        dm = v.groupby(dates.values).mean()
        t = dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm))) if len(dm) > 2 and dm.std() > 0 else float("nan")
        return f" {(v > 0).mean():.0%} / {v.mean():+.2f}% (t {t:.1f}) |"

    def block(title, cols, labels):
        L = [f"\n## {title}\n", "| Group | Positions | " + " | ".join(labels) + " | Your option result (median) |",
             "|---|---|" + "---|" * len(labels) + "---|"]
        best = (R.entry >= pd.Timestamp("2025-11-01").date()) & (R.entry <= pd.Timestamp("2026-04-30").date())
        groups = [("**BEST RUN: Nov 2025 - Apr 2026**", R[best]),
                  ("Best run, puts", R[best & R.put]), ("Best run, calls", R[best & ~R.put])] + \
                 [(f"Best run, {a}", g) for a, g in R[best].groupby("account")] + \
                 [("Before Nov 2025", R[R.entry < pd.Timestamp("2025-11-01").date()]),
                  ("After Apr 2026", R[R.entry > pd.Timestamp("2026-04-30").date()])] + \
                 [("ALL", R)] + [(str(y), g) for y, g in R.groupby("year")] + \
                 [(a, g) for a, g in R.groupby("account")] + \
                 [("puts", R[R.put]), ("calls", R[~R.put])] + \
                 [(f"{a} {y}", g) for (a, y), g in R[R.year >= 2025].groupby(["account", "year"])]
        for name, g in groups:
            L.append(f"| {name} | {len(g)} |" + "".join(cell(g[c], g) for c in cols) +
                     f" {g.opt_ret.median()*100:+.0f}% |")
        return L

    L = ["# Direction Test — all accounts",
         f"\n{len(R)} option positions with stock data ({R.entry.min()} to {R.entry.max()}). "
         "Each ticker+day+direction counts once. Each cell: % of calls where the stock moved your way / "
         "average move your way (t-stat clustered by day, since same-day calls share one market move). "
         "Coin flip = 50% / 0.00%."]
    L += block("From the entry day's OPEN", ["open_day", "open_next", "open_d3", "open_d5"],
               ["Entry-day close", "Next close", "3-day close", "5-day close"])
    L += block("From the entry day's CLOSE (skips the entry-day move)", ["close_next", "close_d3", "close_d5"],
               ["Next close", "3-day close", "5-day close"])
    L += block("Vs SPY, from the entry day's open (removes bull-market drift)", ["xspy_day", "xspy_next", "xspy_d3", "xspy_d5"],
               ["Entry-day close", "Next close", "3-day close", "5-day close"])
    L.append("\nRead: an edge shows as clearly above 50% with t >= 3, ideally in recent years and in more than one account.")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
