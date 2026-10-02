"""
Tazmanian Trader - Exit Analysis
Uses Taz's REAL trades (Exact Entry-Exit Times tab) + expirations (Raw Fills tab)
+ REAL OPRA historical option bars (Databento). No mock data.

For every trade it measures:
  - peak gain while held (did it go green before he sold?)
  - what he captured vs what was there
  - what the contract did AFTER the exit (ran further / went to zero)
Then it replays a set of fixed exit rules on the same entries.

Run:  python exit_analysis.py Tazmanian_Trade_Record.xlsx
Env:  DATABENTO_API_KEY (optional MAX_COST_USD, default 100)
"""
import os, sys, time, math, json
from datetime import timedelta
import pandas as pd
import numpy as np

XLSX = sys.argv[1] if len(sys.argv) > 1 else "Tazmanian_Trade_Record.xlsx"
OUT = "results"
TF = "1-hour"                # bar size (Databento ohlcv-1h)
POST_EXIT_DAYS = 35          # how far past exit to look (capped at expiry)
GREEN_THRESHOLD = 0.20       # "went green" = at least +20% on a bar close
ET = "America/New_York"
DATA_START = pd.Timestamp("2023-03-28")   # OPRA history on Databento starts here

# ---------------- load the workbook ----------------
def read_tab(path, sheet, must_have):
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    hdr = None
    for i in range(min(15, len(raw))):
        vals = [str(v).strip() for v in raw.iloc[i].tolist()]
        if all(m in vals for m in must_have):
            hdr = i; break
    if hdr is None:
        raise SystemExit(f"Could not find header row with {must_have} in '{sheet}'")
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(v).strip() for v in raw.iloc[hdr].tolist()]
    return df.dropna(how="all")

def norm_type(x):
    s = str(x).strip().upper()
    return "C" if s.startswith("C") else ("P" if s.startswith("P") else None)

def num(x):
    try: return float(str(x).replace(",", "").replace("$", ""))
    except: return np.nan


xl = pd.ExcelFile(XLSX)
print("Sheets found in workbook:", xl.sheet_names, flush=True)

def find_sheet(*words):
    for n in xl.sheet_names:
        if all(w in n.lower() for w in words): return n
    return None

def prep_fills():
    sh = find_sheet("raw", "fill")
    if sh is None:
        raise SystemExit(f"No 'Raw Fills' sheet. Sheets present: {xl.sheet_names}. "
                         "Upload the workbook version that has the Raw Fills (All Accounts) tab.")
    f = read_tab(XLSX, sh, ["Symbol", "Expiry", "Strike"])
    f["sym"]    = f["Symbol"].astype(str).str.strip().str.upper()
    f["strike"] = f["Strike"].map(num)
    f["cp"]     = f["Type"].map(norm_type)
    f["exp"]    = pd.to_datetime(f["Expiry"], errors="coerce").dt.normalize()
    f["d"]      = pd.to_datetime(f["Date"], errors="coerce").dt.normalize()
    f["side"]   = f["Side"].astype(str).str.lower() if "Side" in f else ""
    f["acct"]   = f["Account"].astype(str).str.lower() if "Account" in f else ""
    f["px"]     = f["Price"].map(num) if "Price" in f else np.nan
    f["qty"]    = f["Qty"].map(num).abs().fillna(1) if "Qty" in f else 1.0
    tcol = next((c for c in f.columns if c.lower().startswith("time") and "source" not in c.lower()), None)
    tt = f[tcol].astype(str).str.strip() if tcol else pd.Series("", index=f.index)
    has_t = tt.str.match(r"^\d{1,2}:\d{2}")
    f["ts"] = pd.NaT
    f.loc[has_t, "ts"] = pd.to_datetime(f.loc[has_t, "d"].dt.strftime("%Y-%m-%d") + " " + tt[has_t], errors="coerce")
    f["exact_time"] = f["ts"].notna()
    return f.dropna(subset=["exp", "d", "strike", "cp"])

fills = prep_fills()

def from_exact_tab(sh):
    t = read_tab(XLSX, sh, ["Symbol", "Strike", "Entry Time", "Exit Time"])
    t["sym"] = t["Symbol"].astype(str).str.strip().str.upper()
    t["strike"] = t["Strike"].map(num); t["cp"] = t["Type"].map(norm_type)
    t["t_in"] = pd.to_datetime(t["Entry Time"], errors="coerce")
    t["t_out"] = pd.to_datetime(t["Exit Time"], errors="coerce")
    t["px_in"] = t["Entry $"].map(num); t["px_out"] = t["Exit $"].map(num)
    t["time_quality"] = "exact"; t["exit_kind"] = "sold"
    t = t.dropna(subset=["sym", "strike", "cp", "t_in", "t_out", "px_in", "px_out"])
    t = t[t.px_in > 0].reset_index(drop=True)
    res = t.apply(find_expiry, axis=1, result_type="expand")
    t["exp"], t["exp_match"] = res[0], res[1]
    return t

def from_fills_fifo(f):
    """Rebuild round trips from raw fills, FIFO per contract per account.
    Positions never sold are closed at expiry at $0 (exit_kind='expired') -> these are the 'went to zero' trades."""
    f = f[f.d >= DATA_START].copy()                           # Databento OPRA history starts Mar 28 2023
    f["is_buy"] = f.side.str.contains("buy|bto")
    f["is_sell"] = f.side.str.contains("sell|stc")
    f = f[f.is_buy | f.is_sell]
    f["when"] = f.ts.fillna(f.d + pd.Timedelta(hours=9, minutes=45))
    f.loc[f.is_sell & ~f.exact_time, "when"] = f.d + pd.Timedelta(hours=15, minutes=45)
    out = []
    for key, g in f.sort_values(["when"]).groupby(["acct", "sym", "exp", "cp", "strike"], sort=False):
        lots = []                                              # [buy_row, remaining_qty, matched list]
        for _, r in g.iterrows():
            if r.is_buy:
                lots.append([r, r.qty, []]); continue
            q = r.qty
            for lot in lots:
                if q <= 0: break
                take = min(lot[1], q)
                if take > 0:
                    lot[1] -= take; q -= take; lot[2].append((take, r.px, r.when, r.exact_time))
        for b, rem, matched in lots:
            legs = list(matched)
            if rem > 0 and key[2] + pd.Timedelta(hours=16) < pd.Timestamp.now():
                legs.append((rem, 0.0, key[2] + pd.Timedelta(hours=16), True))
            if not legs: continue                              # still open
            qty = sum(x[0] for x in legs)
            out.append({"sym": key[1], "exp": key[2], "cp": key[3], "strike": key[4],
                        "t_in": b.when, "px_in": b.px,
                        "t_out": max(x[2] for x in legs),
                        "px_out": sum(x[0] * x[1] for x in legs) / qty,
                        "qty": qty,
                        "exit_kind": "expired" if rem > 0 and len(legs) == 1 else ("partly expired" if rem > 0 else "sold"),
                        "time_quality": "exact" if b.exact_time and all(x[3] for x in legs) else "date-only (approx 9:45 in / 15:45 out)",
                        "exp_match": "from fill"})
    t = pd.DataFrame(out)
    t = t[(t.px_in > 0) & (t.t_out >= t.t_in)].reset_index(drop=True)
    return t

def find_expiry(r):
    day = r.t_in.normalize()
    m = fills[(fills.sym == r.sym) & (fills.strike == r.strike) & (fills.cp == r.cp) & (fills.d == day)]
    m = m[m.exp >= day]
    if m.empty:
        return pd.NaT, "no matching fill"
    buys = m[m.side.str.contains("buy|bto|open")]
    if not buys.empty: m = buys
    rh = m[m.acct.str.contains("robinhood")]
    if not rh.empty: m = rh
    exact_px = m[(m.px - r.px_in).abs() < 0.011]
    if not exact_px.empty: m = exact_px
    exps = m.exp.unique()
    if len(exps) == 1:
        return exps[0], "matched"
    return m.exp.value_counts().idxmax(), f"ambiguous ({len(exps)} expiries, took most common)"

exact_sheet = find_sheet("entry", "exit")
if exact_sheet:
    print(f"Using '{exact_sheet}' tab (exact times).", flush=True)
    trades = from_exact_tab(exact_sheet)
else:
    print("No Entry-Exit tab -> rebuilding round trips from Raw Fills (FIFO). "
          "Exact-time and date-only trades are reported separately.", flush=True)
    trades = from_fills_fifo(fills)
print(f"Trades to analyze: {len(trades)}", flush=True)

def occ(sym, exp, cp, strike):
    return f"{sym}{exp:%y%m%d}{cp}{int(round(strike * 1000)):08d}"

# ---------------- Databento OPRA bars (real consolidated options data) ----------------
try:
    import databento as db
except ImportError:                       # workflow didn't install it -> install it here
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "databento"])
    import databento as db
DB_KEY = os.environ.get("DATABENTO_API_KEY")
MAX_COST = float(os.environ.get("MAX_COST_USD", "100"))   # hard stop so the free $125 credit is never exceeded
DATASET, SCHEMA = "OPRA.PILLAR", "ohlcv-1h"
_bars = {}                                                    # occ -> DataFrame
_err = {}

def raw_osi(occ_sym):
    root, rest = occ_sym[:-15], occ_sym[-15:]
    return root.ljust(6) + rest

def _retry(fn, what, tries=6):
    """Databento gateway can time out (504) on busy moments: back off and retry."""
    for k in range(tries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if k == tries - 1:
                raise
            wait = min(60, 5 * 2 ** k)
            print(f"    {what}: {msg[:90]} -> retry {k+1}/{tries-1} in {wait}s", flush=True)
            time.sleep(wait)

CHUNK = 100   # symbols per request (smaller = fewer gateway timeouts)

def fetch_all(first_in):
    """One pass: for each batch, price it, add to running total, stop before exceeding MAX_COST, then download."""
    client = db.Historical(DB_KEY)
    groups = {}
    for occ_sym, t_in in first_in.items():
        exp = pd.Timestamp("20" + occ_sym[-15:-13] + "-" + occ_sym[-13:-11] + "-" + occ_sym[-11:-9])
        groups.setdefault(exp, []).append((occ_sym, t_in))
    jobs = []
    for exp, items in sorted(groups.items()):
        for k in range(0, len(items), CHUNK):
            chunk = items[k:k + CHUNK]
            start = min(t for _, t in chunk).tz_convert("UTC") - timedelta(hours=1)
            end = min((exp + timedelta(days=1)).tz_localize("UTC"),
                      pd.Timestamp.now(tz="UTC").normalize() - timedelta(days=1))   # data is T+1
            if end > start: jobs.append((chunk, start, end))
    print(f"Databento: {len(jobs)} batches for {len(first_in)} contracts. Cost is checked batch by batch "
          f"(hard stop at ${MAX_COST:.0f}).", flush=True)
    spent, failed = 0.0, 0
    for j, (chunk, start, end) in enumerate(jobs, 1):
        syms = {raw_osi(c): c for c, _ in chunk}
        kw = dict(dataset=DATASET, schema=SCHEMA, stype_in="raw_symbol", symbols=list(syms), start=start, end=end)
        try:
            cost = _retry(lambda: client.metadata.get_cost(**kw), f"batch {j} cost")
            if spent + cost > MAX_COST:
                print(f"STOPPING: batch {j} would take spend to ${spent + cost:.2f} > ${MAX_COST:.0f}. "
                      f"Analyzing what was downloaded.", flush=True)
                for jj in jobs[j - 1:]:
                    for c, _ in jj[0]: _err.setdefault(c, "skipped: cost limit")
                break
            df = _retry(lambda: client.timeseries.get_range(**kw).to_df(), f"batch {j} download")
            spent += cost
        except Exception as e:
            failed += 1
            for c, _ in chunk: _err[c] = f"request error: {str(e)[:120]}"
            print(f"  batch {j} failed after retries: {str(e)[:160]}", flush=True)
            continue
        if not df.empty:
            df = df.reset_index()
            df["t"] = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
            df = df.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
            for raw, g in df.groupby("symbol"):
                c = syms.get(raw) or syms.get(str(raw).strip())
                if c: _bars[c] = g[["t", "o", "h", "l", "c", "v"]].sort_values("t").reset_index(drop=True)
        if j % 20 == 0 or j == len(jobs):
            print(f"  {j}/{len(jobs)} batches done | spent ${spent:.2f} | contracts with bars {len(_bars)}", flush=True)
    print(f"Download finished. Spent ${spent:.2f}. Contracts with bars: {len(_bars)} of {len(first_in)}. "
          f"Failed batches: {failed}", flush=True)

def contract_bars(sym):
    if sym in _bars: return _bars[sym], "ok"
    return None, _err.get(sym, "no trades printed for this contract in the window")

# ---------------- exit rule replay ----------------
def simulate(path, entry, rule):
    """path = DataFrame of bars from entry onward (closes). Returns exit multiple (exit/entry).
    Fills at bar close when a level is crossed on the close (conservative: no intrabar fills)."""
    if path.empty: return np.nan
    c = path["c"].values / entry
    kind = rule["kind"]
    if kind == "hold":
        return c[-1]
    if kind == "time":
        t0 = path["t"].iloc[0]
        idx = np.where((path["t"] - t0) >= pd.Timedelta(hours=rule["hours"]))[0]
        return c[idx[0]] if len(idx) else c[-1]
    if kind == "tp_sl":
        for x in c:
            if x >= 1 + rule["tp"]: return x
            if rule["sl"] is not None and x <= 1 - rule["sl"]: return x
        return c[-1]
    if kind == "scale":
        sl, t1, t2, trail = rule["sl"], rule["t1"], rule.get("t2"), rule.get("trail")
        half_done, first, peak = False, None, 0
        for x in c:
            if not half_done:
                if x >= 1 + t1:
                    half_done, first, peak = True, x, x
                    continue
                if sl is not None and x <= 1 - sl:
                    return x
            else:
                peak = max(peak, x)
                if x <= 1.0:                                  # stop moved to breakeven
                    return 0.5 * first + 0.5 * x
                if t2 is not None and x >= 1 + t2:
                    return 0.5 * first + 0.5 * x
                if trail is not None and x <= peak * (1 - trail):
                    return 0.5 * first + 0.5 * x
        return (0.5 * first + 0.5 * c[-1]) if half_done else c[-1]
    raise ValueError(kind)

RULES = {"0_actual": {"kind": "actual"}, "hold_to_window_end": {"kind": "hold"}}
for h in (1, 4, 24, 48, 120): RULES[f"time_{h}h"] = {"kind": "time", "hours": h}
for tp in (0.25, 0.5, 1.0, 2.0):
    for sl in (None, 0.3, 0.5):
        RULES[f"tp{int(tp*100)}_sl{'none' if sl is None else int(sl*100)}"] = {"kind": "tp_sl", "tp": tp, "sl": sl}
for t1 in (0.5, 1.0):
    for sl in (None, 0.5):
        for t2 in (2.0, 3.0):
            RULES[f"scale_half@{int(t1*100)}_be_t2@{int(t2*100)}_sl{'none' if sl is None else int(sl*100)}"] = {"kind": "scale", "t1": t1, "t2": t2, "sl": sl}
        for tr in (0.3, 0.5):
            RULES[f"scale_half@{int(t1*100)}_be_trail{int(tr*100)}_sl{'none' if sl is None else int(sl*100)}"] = {"kind": "scale", "t1": t1, "trail": tr, "sl": sl}

FIRST_IN = {}

# ---------------- main loop ----------------
def main():
    if not DB_KEY:
        raise SystemExit("Missing DATABENTO_API_KEY secret")
    os.makedirs(OUT, exist_ok=True)
    rows, paths = [], {}
    n = len(trades)
    for _, r in trades.dropna(subset=["exp"]).iterrows():
        t_in = r.t_in.tz_localize(ET) if r.t_in.tzinfo is None else r.t_in
        for root in ((r.sym, r.sym + "W") if r.sym in ("SPX", "NDX") else (r.sym,)):
            k = occ(root, pd.Timestamp(r.exp), r.cp, r.strike)
            FIRST_IN[k] = min(FIRST_IN.get(k, t_in), t_in)
    print(f"Unique contracts to fetch: {len(FIRST_IN)}", flush=True)
    fetch_all(FIRST_IN)
    for i, r in trades.iterrows():
        rec = {"sym": r.sym, "strike": r.strike, "type": r.cp, "entry_time": r.t_in, "exit_time": r.t_out,
               "entry_px": r.px_in, "exit_px": r.px_out, "expiry": r.exp, "expiry_match": r.exp_match,
               "realized_pct": r.px_out / r.px_in - 1,
               "exit_kind": r.get("exit_kind", "sold"), "time_quality": r.get("time_quality", "exact")}
        if pd.isna(r.exp):
            rec["status"] = "no expiry"; rows.append(rec); continue
        t_in = r.t_in.tz_localize(ET) if r.t_in.tzinfo is None else r.t_in
        t_out = r.t_out.tz_localize(ET) if r.t_out.tzinfo is None else r.t_out
        exp_close = pd.Timestamp(r.exp).tz_localize(ET) + timedelta(hours=16)
        window_end = min(exp_close, t_out + timedelta(days=POST_EXIT_DAYS))
        sym = occ(r.sym, pd.Timestamp(r.exp), r.cp, r.strike)
        rec["occ"] = sym
        bars, status = contract_bars(sym)
        if bars is None and r.sym in ("SPX", "NDX"):
            sym = occ(r.sym + "W", pd.Timestamp(r.exp), r.cp, r.strike)
            bars, status = contract_bars(sym)
        if bars is not None:
            bars = bars[bars.t <= window_end]
        rec["status"] = status
        if bars is None:
            rows.append(rec)
            if sum(1 for x in rows if x.get("status") not in ("ok", None)) <= 5:
                print(f"  no data for {sym}: {status}", flush=True)
            continue
        held = bars[(bars.t >= t_in - timedelta(minutes=15)) & (bars.t <= t_out)]
        after = bars[bars.t > t_out]
        fwd = bars[bars.t >= t_in - timedelta(minutes=15)]
        e = r.px_in
        if not held.empty:
            rec["peak_while_held_pct"] = held.c.max() / e - 1
            rec["peak_high_while_held_pct"] = held.h.max() / e - 1
            rec["worst_while_held_pct"] = held.c.min() / e - 1
            rec["peak_time"] = held.loc[held.c.idxmax(), "t"]
        if not after.empty:
            rec["peak_after_exit_pct"] = after.c.max() / e - 1
            rec["last_close_in_window_pct"] = after.c.iloc[-1] / e - 1
            rec["went_to_zero_after"] = bool(after.c.iloc[-1] <= 0.05)
        rec["bars"] = len(fwd)
        paths[i] = fwd
        rows.append(rec)
        if (i + 1) % 25 == 0: print(f"{i+1}/{n} trades processed", flush=True)

    df = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(f"{OUT}/exit_trades_all.csv", index=False)
    print("\nData status per trade:", flush=True)
    print(df["status"].value_counts().to_string(), flush=True)
    ok = df["status"] == "ok"
    d = df[ok].copy()
    if d.empty or "peak_while_held_pct" not in d:
        raise SystemExit("No trades had usable option bars - see status counts above.")
    for col in ("peak_while_held_pct", "peak_high_while_held_pct", "worst_while_held_pct",
                "peak_after_exit_pct", "last_close_in_window_pct", "went_to_zero_after"):
        if col not in d: d[col] = np.nan
    d["captured_of_peak"] = np.where(d.peak_while_held_pct > 0, d.realized_pct / d.peak_while_held_pct, np.nan)
    d["green_then_loss"] = (d.peak_while_held_pct >= GREEN_THRESHOLD) & (d.realized_pct < 0)
    d["sold_then_ran_2x_more"] = (d.peak_after_exit_pct >= d.realized_pct + 1.0)

    # replay rules
    rule_rows = []
    for name, rule in RULES.items():
        mult = []
        for i, r in d.iterrows():
            if rule["kind"] == "actual": mult.append(r.exit_px / r.entry_px)
            else: mult.append(simulate(paths[i], r.entry_px, rule))
        m = pd.Series(mult, index=d.index)
        ret = m - 1
        dollars = ret * d.entry_px * 100
        logr = np.log(m.clip(lower=0.01))
        half = len(d) // 2
        order = d.sort_values("entry_time").index
        early, late = ret.loc[order[:half]], ret.loc[order[half:]]
        rule_rows.append({
            "rule": name, "trades": int(m.notna().sum()),
            "avg_return_pct": ret.mean() * 100, "median_return_pct": ret.median() * 100,
            "win_rate_pct": (ret > 0).mean() * 100,
            "total_$_1_contract_each": dollars.sum(),
            "avg_log_return": logr.mean(),
            "t_stat_log": logr.mean() / (logr.std(ddof=1) / math.sqrt(logr.notna().sum())) if logr.notna().sum() > 2 else np.nan,
            "avg_ret_first_half_pct": early.mean() * 100, "avg_ret_second_half_pct": late.mean() * 100,
        })
        d[f"rule::{name}"] = ret
    summ = pd.DataFrame(rule_rows).sort_values("avg_log_return", ascending=False)

    df.to_csv(f"{OUT}/exit_trades_all.csv", index=False)
    d.to_csv(f"{OUT}/exit_trades_analyzed.csv", index=False)
    summ.to_csv(f"{OUT}/exit_rules_summary.csv", index=False)

    # plain-English report
    L = []
    L.append("# Exit Analysis - Tazmanian Trader (real trades, real OPRA option bars via Databento)\n")
    L.append(f"Trades in tab: {len(trades)} | with expiry found: {int(df.expiry.notna().sum())} | with option bars: {int(ok.sum())}")
    L.append(f"Bar size: {TF}. Peaks measured on bar CLOSES (conservative). Window: entry to min(expiry, exit + {POST_EXIT_DAYS} days).\n")
    L.append("## How the trades actually went")
    L.append(f"- Realized avg return: {d.realized_pct.mean()*100:.1f}% | median {d.realized_pct.median()*100:.1f}% | win rate {(d.realized_pct>0).mean()*100:.1f}%")
    L.append(f"- Went >= +{int(GREEN_THRESHOLD*100)}% green while held: {(d.peak_while_held_pct>=GREEN_THRESHOLD).mean()*100:.1f}% of trades")
    L.append(f"- Went >= +{int(GREEN_THRESHOLD*100)}% green but closed RED: {int(d.green_then_loss.sum())} trades ({d.green_then_loss.mean()*100:.1f}%)")
    L.append(f"- Median peak while held: {d.peak_while_held_pct.median()*100:.1f}% vs median realized {d.realized_pct.median()*100:.1f}%")
    L.append(f"- Winners: median share of peak captured: {d.loc[d.realized_pct>0,'captured_of_peak'].median()*100:.0f}%")
    L.append(f"- After exit, contract later reached at least +100 points more than your exit: {int(d.sold_then_ran_2x_more.sum())} trades")
    L.append(f"- After exit, contract ended the window near zero: {int(d.went_to_zero_after.fillna(False).sum())} trades")
    exp_ = d[d.exit_kind.astype(str).str.contains("expired")]
    if len(exp_):
        L.append(f"- Held to expiry and EXPIRED (never sold): {len(exp_)} trades. Of those, went >= +{int(GREEN_THRESHOLD*100)}% green first: {int((exp_.peak_while_held_pct>=GREEN_THRESHOLD).sum())}; went >= +50% green first: {int((exp_.peak_while_held_pct>=0.5).sum())}")
    L.append("\n### Split by timing quality")
    for q, g in d.groupby("time_quality"):
        L.append(f"- {q}: {len(g)} trades | realized avg {g.realized_pct.mean()*100:.1f}% | went +{int(GREEN_THRESHOLD*100)}% green {(g.peak_while_held_pct>=GREEN_THRESHOLD).mean()*100:.0f}% | green-then-red {int(g.green_then_loss.sum())}")
    L.append("Date-only trades assume a 9:45 entry and 15:45 exit, so their in-trade peaks are approximate. Trust the exact-time group more.\n")
    L.append("## Exit rules replayed on your exact entries (sorted by avg log return = compounding growth)")
    L.append("| Rule | Trades | Avg % | Median % | Win % | $ (1 contract each) | t-stat | 1st half avg % | 2nd half avg % |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for _, s in summ.iterrows():
        L.append(f"| {s.rule} | {s.trades} | {s.avg_return_pct:.1f} | {s.median_return_pct:.1f} | {s.win_rate_pct:.1f} | {s['total_$_1_contract_each']:,.0f} | {s.t_stat_log:.2f} | {s.avg_ret_first_half_pct:.1f} | {s.avg_ret_second_half_pct:.1f} |")
    L.append("\n## Read this before trusting any rule")
    L.append("- Many rules were tested on the same trades. The best one is partly luck. A rule counts only if it wins in BOTH halves (early and late trades) and its t-stat is >= 3.")
    L.append("- Fills are bar closes, not real bid/ask. Real exits will be somewhat worse, especially on cheap or illiquid contracts.")
    L.append("- These are your entries. The rule tells you how to EXIT your kind of trade, not what to buy.")
    misses = df[df.status != "ok"].status.value_counts()
    if len(misses):
        L.append("\n## Trades not analyzed (and why)")
        for k, v in misses.items(): L.append(f"- {k}: {v}")
    open(f"{OUT}/exit_analysis_report.md", "w").write("\n".join(L))
    print("\n".join(L[:12]))
    print("\nDone. See results/exit_analysis_report.md")

if __name__ == "__main__":
    main()
