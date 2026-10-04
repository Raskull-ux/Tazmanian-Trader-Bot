"""
Tazmanian Trader — Your Entries Study
=====================================
The event study proved the mechanical HOD-rejection pattern has no edge by
itself. So the edge Taz does have (2025 +5%/trade, 2026 +9%/trade) comes from
what he adds: market context and selection. This script measures it on his
REAL trades — real option entry and exit prices, no estimates.

Input: 'Exact Entry-Exit Times' tab (576 Robinhood trades with minute-level
entry and exit, Apr 2024 - Apr 2026), expiry matched from 'Raw Fills'.

At each entry minute (using only the last COMPLETED 5-min bar) it records:
  Stock:   move from open, distance from high/low of day (ATR), run size,
           above/below VWAP, 5-min 50/200 SMA position, RSI vs its MA,
           RSI divergence, consolidation, gap from yesterday, daily 8 SMA,
           yesterday's move
  Market:  SPY, QQQ, SMH (semis), IWM, IYT (transports) move from open and
           position vs their VWAP; VIXY move (fear proxy); SPY 5-day trend
  Trade:   time of day, days to expiry, how far out of the money, premium paid,
           put or call

Everything directional is expressed "with the trade": for a put, the market
falling counts as WITH; for a call, rising counts as WITH.

Outcome: real option return = exit price / entry price - 1.
Then: which conditions separate winners from losers, and a walk-forward rule
(picked on the older 2/3 of trades, scored on the newest 1/3).

Env: ALPACA keys.  Out: results/entries_study/{report.md, trades_features.csv}
"""
from __future__ import annotations
import os, glob, math
from datetime import timedelta
import numpy as np
import pandas as pd
import setup_backtest as sb

OUT = "results/entries_study"
CONTEXT = ["SPY", "QQQ", "SMH", "IWM", "IYT", "VIXY"]


def load_trades():
    path = sorted(glob.glob("Tazmanian_Trade_Record*.xlsx"))[-1]
    e = pd.read_excel(path, "Exact Entry-Exit Times", header=3)
    e = e.dropna(subset=["Symbol", "Entry Time", "Entry $", "Exit $"])
    e["entry_t"] = pd.to_datetime(e["Entry Time"]).dt.tz_localize(sb.NY)
    e["exit_t"] = pd.to_datetime(e["Exit Time"]).dt.tz_localize(sb.NY)
    e["put"] = e["Type"].astype(str).str.lower().str.startswith("p")
    e["ret"] = e["Exit $"] / e["Entry $"] - 1
    e["date"] = e["entry_t"].dt.date
    # expiry from raw fills: same symbol/strike/type bought that day
    r = pd.read_excel(path, "Raw Fills (All Accounts)", header=3)
    r = r[r["Side"].astype(str).str.upper() == "BUY"]
    r["date"] = pd.to_datetime(r["Date"]).dt.date
    r["put"] = r["Type"].astype(str).str.lower().str.startswith("p")
    r["Expiry"] = pd.to_datetime(r["Expiry"], errors="coerce")
    ex = r.groupby(["Symbol", "Strike", "put", "date"])["Expiry"].min().reset_index()
    e = e.merge(ex, on=["Symbol", "Strike", "put", "date"], how="left")
    e["dte"] = (e["Expiry"].dt.date - e["date"]).apply(lambda d: d.days if pd.notna(d) else np.nan)
    print(f"Trades: {len(e)} ({int(e.put.sum())} puts, {int((~e.put).sum())} calls), "
          f"expiry matched {e.Expiry.notna().mean():.0%}, {e.date.min()} -> {e.date.max()}")
    return e.reset_index(drop=True)


def frame(b5, b1d):
    b = sb.prep_5m(b5)
    pc = b["c"].shift()
    tr = np.maximum(b["h"] - b["l"], np.maximum((b["h"] - pc).abs(), (b["l"] - pc).abs()))
    b["atr"] = tr.rolling(14).mean()
    b["end"] = b["t"] + pd.Timedelta(minutes=5)
    rth = b["rth"]
    tp = (b["h"] + b["l"] + b["c"]) / 3
    pv = (tp * b["v"]).where(rth, 0.0); vv = b["v"].where(rth, 0.0)
    b["vwap"] = pv.groupby(b["day"]).cumsum() / vv.groupby(b["day"]).cumsum().replace(0, np.nan)
    first = b[rth].groupby("day")["o"].first()
    b["day_open"] = b["day"].map(first)
    b["hod"] = b["h"].where(rth).groupby(b["day"]).cummax()
    b["lod"] = b["l"].where(rth).groupby(b["day"]).cummin()
    d = b1d.sort_values("t").copy()
    d["day"] = d["t"].dt.date
    d["sma8"] = d["c"].rolling(8).mean()
    d["ret5"] = d["c"].pct_change(5)
    daily = pd.DataFrame({"day": d["day"], "prev_c": d["c"].shift(), "prev_ret": d["c"].pct_change().shift(),
                          "sma8": d["sma8"].shift(), "ret5": d["ret5"].shift()}).set_index("day")
    return b.reset_index(drop=True), daily


def at(b, t):
    """Index of the last completed 5-min bar at time t (bar end <= t)."""
    k = np.searchsorted(b["end"].values, np.datetime64(t.tz_convert("UTC").tz_localize(None)), side="right") - 1
    return k


def stock_features(b, daily, t, put):
    k = at(b, t)
    if k < 30:
        return None
    row = b.iloc[k]
    if row["day"] != t.date():
        return None   # entry before first bar of the day completed
    s = -1 if put else 1                  # +1 = trade wants price UP
    a = row["atr"] if row["atr"] > 0 else np.nan
    c = row["c"]
    dd = daily.loc[t.date()] if t.date() in daily.index else None
    r = b["rsi"].values
    f = dict(
        stock_move_open=(c / row["day_open"] - 1) * 100,
        # 'into the move' = fading: put after the stock ran up, call after it fell
        faded_move_atr=-s * (c - row["day_open"]) / a,
        from_extreme_atr=((row["hod"] - c) if put else (c - row["lod"])) / a,
        vs_vwap_with=s * (c / row["vwap"] - 1) * 100 if row["vwap"] == row["vwap"] else np.nan,
        ext50_atr=(c - row["sma50"]) / a,
        above200=bool(c > row["sma200"]),
        rsi=row["rsi"],
        rsi_turned_with=bool((row["rsi"] < row["rsima"]) if put else (row["rsi"] > row["rsima"])),
        div_pts=(np.nanmax(r[k - 24:k - 6]) - np.nanmax(r[k - 6:k + 1])) if put
        else (np.nanmin(r[k - 6:k + 1]) - np.nanmin(r[k - 24:k - 6])),
        minute=t.hour * 60 + t.minute,
    )
    if dd is not None:
        f["gap_pct"] = (row["day_open"] / dd["prev_c"] - 1) * 100 if dd["prev_c"] == dd["prev_c"] else np.nan
        f["above_d8"] = bool(c > dd["sma8"]) if dd["sma8"] == dd["sma8"] else np.nan
        f["yday_move_with"] = s * dd["prev_ret"] * 100 if dd["prev_ret"] == dd["prev_ret"] else np.nan
    return f


def context_features(ctx, t, put):
    s = -1 if put else 1
    f = {}
    for sym, (b, daily) in ctx.items():
        k = at(b, t)
        if k < 0 or b.iloc[k]["day"] != t.date():
            continue
        row = b.iloc[k]
        mv = (row["c"] / row["day_open"] - 1) * 100
        if sym == "VIXY":
            f["vixy_move"] = mv            # fear rising = VIXY up
            continue
        f[f"{sym.lower()}_with"] = s * mv
        f[f"{sym.lower()}_vwap_with"] = bool(s * (row["c"] - row["vwap"]) > 0) if row["vwap"] == row["vwap"] else np.nan
        if sym == "SPY" and t.date() in daily.index:
            f["spy_5d_with"] = s * daily.loc[t.date(), "ret5"] * 100
    return f


# ------------------------------------------------------------------ analysis
def tstat(x):
    x = x.dropna()
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def line(name, x):
    v = x["ret"].clip(upper=5.0)   # cap single trades at +500% so one lotto win can't dominate
    if len(v) == 0:
        return None
    return (f"| {name} | {len(v)} | {(v > 0).mean():.0%} | {v.mean()*100:+.0f}% | "
            f"{v.median()*100:+.0f}% | {tstat(v):.1f} |")


HDR = "| Condition | Trades | Win rate | Avg return | Median | t |\n|---|---|---|---|---|---|"


def buckets(df):
    q = lambda col, cuts, labels: [(lab, df[col].between(lo, hi, inclusive="left"))
                                   for lab, (lo, hi) in zip(labels, zip(cuts[:-1], cuts[1:]))]
    B = {
        "Market: SPY move from open, WITH your trade (%)": q("spy_with", [-99, -0.5, 0, 0.5, 99],
            ["SPY moving against you >0.5%", "against 0-0.5%", "with you 0-0.5%", "with you >0.5%"]),
        "Market: QQQ move from open, WITH your trade (%)": q("qqq_with", [-99, -0.5, 0, 0.5, 99],
            ["QQQ against >0.5%", "against 0-0.5%", "with 0-0.5%", "with >0.5%"]),
        "Semis: SMH move WITH your trade (%)": q("smh_with", [-99, -0.75, 0, 0.75, 99],
            ["SMH against >0.75%", "against 0-0.75%", "with 0-0.75%", "with >0.75%"]),
        "Transports: IYT move WITH your trade (%)": q("iyt_with", [-99, -0.5, 0, 0.5, 99],
            ["IYT against >0.5%", "against 0-0.5%", "with 0-0.5%", "with >0.5%"]),
        "Small caps: IWM move WITH your trade (%)": q("iwm_with", [-99, -0.5, 0, 0.5, 99],
            ["IWM against >0.5%", "against 0-0.5%", "with 0-0.5%", "with >0.5%"]),
        "SPY vs its VWAP": [("SPY on your side of VWAP", df["spy_vwap_with"] == True),
                            ("SPY on the wrong side of VWAP", df["spy_vwap_with"] == False)],
        "Fear: VIXY move from open (%)": q("vixy_move", [-99, -1, 1, 99],
            ["VIXY down >1%", "VIXY flat", "VIXY up >1%"]),
        "SPY 5-day trend WITH your trade (%)": q("spy_5d_with", [-99, -1, 1, 99],
            ["5-day trend against >1%", "flat", "5-day trend with >1%"]),
        "Stock: faded move from open (ATR, + = fading the move)": q("faded_move_atr", [-99, -2, 0, 2, 5, 99],
            ["chasing >2 ATR", "chasing 0-2", "fading 0-2", "fading 2-5", "fading 5+"]),
        "Stock: distance from high (puts) / low (calls), ATR": q("from_extreme_atr", [0, 1, 3, 6, 999],
            ["within 1 ATR of the extreme", "1-3 ATR", "3-6 ATR", "6+ ATR"]),
        "Stock vs VWAP WITH your trade (%)": q("vs_vwap_with", [-99, -0.5, 0, 0.5, 99],
            ["wrong side of VWAP >0.5%", "wrong side 0-0.5%", "right side 0-0.5%", "right side >0.5%"]),
        "RSI turned your way (vs its MA)": [("yes", df["rsi_turned_with"] == True), ("no", df["rsi_turned_with"] == False)],
        "RSI divergence (points)": q("div_pts", [-99, 0, 5, 99], ["none", "0-5", "5+"]),
        "Gap from yesterday (%)": q("gap_pct", [-99, -1, 1, 99], ["gap down >1%", "flat open", "gap up >1%"]),
        "Yesterday's move WITH your trade (%)": q("yday_move_with", [-99, -1, 1, 99],
            ["yesterday against >1%", "flat", "yesterday with >1%"]),
        "Time of entry": q("minute", [0, 600, 660, 780, 900, 9999],
            ["before 10:00", "10:00-11:00", "11:00-1:00", "1:00-3:00", "after 3:00"]),
        "Days to expiry": q("dte", [-1, 0.5, 1.5, 3.5, 7.5, 999], ["0DTE", "1 day", "2-3 days", "4-7 days", "8+ days"]),
        "Premium paid per contract ($)": q("Entry $", [0, 0.25, 0.5, 1, 2, 9999],
            ["under $0.25", "$0.25-0.50", "$0.50-1", "$1-2", "$2+"]),
        "How far out of the money (%)": q("otm_pct", [-99, 0, 1, 3, 99],
            ["in the money", "0-1% OTM", "1-3% OTM", "3%+ OTM"]),
        "Hold time": q("Hold (hrs)", [0, 1, 4, 24, 9999], ["under 1 hr", "1-4 hrs", "4-24 hrs (overnight)", "1+ day"]),
        "Puts vs calls": [("puts", df["put"]), ("calls", ~df["put"])],
    }
    return B


def pick_rule(train, min_n=35):
    chosen, cur = [], pd.Series(True, index=train.index)
    allb = [(f, n, m) for f, lst in buckets(train).items() for n, m in lst
            if not f.startswith("Hold time")]          # hold time isn't known at entry
    for _ in range(2):
        base = train.loc[cur, "ret"].clip(upper=5).mean(); best = None
        for f, n, m in allb:
            if f in [x[0] for x in chosen]:
                continue
            sel = cur & m.fillna(False).astype(bool)
            if sel.sum() < min_n:
                continue
            v = train.loc[sel, "ret"].clip(upper=5).mean()
            if v > base + 0.03 and (best is None or v > best[3]):
                best = (f, n, sel, v)
        if best is None:
            break
        chosen.append((best[0], best[1])); cur = best[2]
    return chosen


def apply(df, rule):
    m = pd.Series(True, index=df.index); B = buckets(df)
    for f, n in rule:
        m &= dict(B[f])[n].fillna(False).astype(bool)
    return df[m]


def main():
    os.makedirs(OUT, exist_ok=True)
    tr = load_trades()
    start = (tr.entry_t.min() - timedelta(days=60)).date().isoformat()
    end = (tr.exit_t.max() + timedelta(days=2)).date().isoformat()
    syms = sorted(set(tr.Symbol.astype(str)) | set(CONTEXT))
    data = {}
    for i in range(0, len(syms), 20):
        ch = syms[i:i + 20]
        try:
            m5 = sb.fetch(ch, "5Min", start, end); d1 = sb.fetch(ch, "1Day", start, end)
        except Exception as ex:
            print("fetch", ch[:3], ex); continue
        for s in ch:
            x5, x1 = m5[m5.symbol == s], d1[d1.symbol == s]
            if len(x5) > 100 and len(x1) > 10:
                data[s] = frame(x5, x1)
        print(f"  bars: {min(i + 20, len(syms))}/{len(syms)} symbols")
    ctx = {s: data[s] for s in CONTEXT if s in data}
    rows = []
    for _, t in tr.iterrows():
        sym = str(t.Symbol)
        if sym not in data:
            continue
        b, daily = data[sym]
        f = stock_features(b, daily, t.entry_t, t.put)
        if f is None:
            continue
        f.update(context_features(ctx, t.entry_t, t.put))
        k = at(b, t.entry_t); px = b.iloc[k]["c"]
        f["otm_pct"] = ((px - t.Strike) / px * 100) if t.put else ((t.Strike - px) / px * 100)
        rows.append({**t.to_dict(), **f})
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/trades_features.csv", index=False)

    L = ["# Your Entries Study — what's present when you win",
         f"\n{len(df)} of {len(tr)} trades matched to 5-min bars "
         f"({df.date.min()} to {df.date.max()}). Real option returns (exit ÷ entry − 1); "
         "single trades capped at +500% in averages. 'WITH' = moving in your trade's direction.\n",
         "## All matched trades\n", HDR, line("all trades", df)]
    for name, lst in buckets(df).items():
        rows_ = [line(n, df[m.fillna(False).astype(bool)]) for n, m in lst]
        rows_ = [r for r in rows_ if r and not r.split("|")[2].strip() == "0"]
        if rows_:
            L += [f"\n## {name}\n", HDR] + rows_
    df = df.sort_values("entry_t").reset_index(drop=True)
    cut = int(len(df) * 2 / 3)
    train, test = df.iloc[:cut], df.iloc[cut:]
    rule = pick_rule(train)
    desc = " AND ".join(f"{n} [{f.split(':')[0]}]" for f, n in rule) or "(nothing beat the baseline)"
    L += [f"\n## Walk-forward rule — picked on your older {len(train)} trades, scored on your newest {len(test)}\n",
          f"Rule: **{desc}**\n", HDR, line("older trades, all", train), line("older trades, rule", apply(train, rule)),
          line("NEWEST trades, all", test), line("NEWEST trades, rule", apply(test, rule)),
          "\nOnly the NEWEST rows count. With ~575 trades, a filter needs a big, consistent gap "
          "(not a few points) to be believable; look for conditions where the win rate and the "
          "median move together, in both halves."]
    open(f"{OUT}/report.md", "w").write("\n".join(x for x in L if x) + "\n")
    print("\n".join(x for x in L if x))


if __name__ == "__main__":
    main()
