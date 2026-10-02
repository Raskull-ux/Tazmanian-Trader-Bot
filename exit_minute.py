"""
Minute-level exit test on Taz's EXACT-TIME trades (Robinhood email timestamps).
Reads the 'Exact Entry-Exit Times' tab (+ expiries from 'Raw Fills (All Accounts)'),
pulls REAL 1-minute OPRA bars from Databento (cost-checked, cached), and replays exit rules
from the true entry minute. No assumed times, no mock data.
Env: DATABENTO_API_KEY, MAX_COST_USD (default 15)
"""
import os, sys, math, time, hashlib, threading
from datetime import timedelta
import numpy as np, pandas as pd
try:
    import databento as db
except ImportError:
    import subprocess; subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "databento"]); import databento as db

XLSX = sys.argv[1] if len(sys.argv) > 1 else "Tazmanian_Trade_Record.xlsx"
OUT, CACHE = "results_minute", "results_minute/bar_cache"
ET = "America/New_York"
MAX_COST = float(os.environ.get("MAX_COST_USD", "15"))
POST_DAYS = 3

def num(x):
    try: return float(str(x).replace(",", "").replace("$", ""))
    except: return np.nan
def cp_(x):
    s = str(x).strip().upper(); return "C" if s.startswith("C") else ("P" if s.startswith("P") else None)
def read_tab(sheet, must):
    raw = pd.read_excel(XLSX, sheet_name=sheet, header=None)
    for i in range(min(15, len(raw))):
        vals = [str(v).strip() for v in raw.iloc[i].tolist()]
        if all(m in vals for m in must):
            df = raw.iloc[i + 1:].copy(); df.columns = vals; return df.dropna(how="all")
    raise SystemExit(f"header {must} not found in {sheet}")

xl = pd.ExcelFile(XLSX); print("Sheets:", xl.sheet_names, flush=True)
ex = next((s for s in xl.sheet_names if "entry" in s.lower() and "exit" in s.lower()), None)
rf = next((s for s in xl.sheet_names if "raw" in s.lower() and "fill" in s.lower()), None)
if not ex:
    raise SystemExit("This workbook has no 'Exact Entry-Exit Times' tab. Upload the 5-tab version.")
T = read_tab(ex, ["Symbol", "Strike", "Entry Time", "Exit Time"])
T["sym"] = T["Symbol"].astype(str).str.strip().str.upper(); T["strike"] = T["Strike"].map(num); T["cp"] = T["Type"].map(cp_)
T["t_in"] = pd.to_datetime(T["Entry Time"], errors="coerce"); T["t_out"] = pd.to_datetime(T["Exit Time"], errors="coerce")
T["px_in"] = T["Entry $"].map(num); T["px_out"] = T["Exit $"].map(num)
T = T.dropna(subset=["sym", "strike", "cp", "t_in", "t_out", "px_in", "px_out"])
T = T[(T.px_in > 0) & (T.t_out >= T.t_in)].reset_index(drop=True)
F = read_tab(rf, ["Symbol", "Expiry", "Strike"])
F["sym"] = F["Symbol"].astype(str).str.strip().str.upper(); F["strike"] = F["Strike"].map(num); F["cp"] = F["Type"].map(cp_)
F["exp"] = pd.to_datetime(F["Expiry"], errors="coerce").dt.normalize(); F["d"] = pd.to_datetime(F["Date"], errors="coerce").dt.normalize()
F["px"] = F["Price"].map(num) if "Price" in F else np.nan
F["side"] = F["Side"].astype(str).str.upper() if "Side" in F else ""
def expiry(r):
    m = F[(F.sym == r.sym) & (F.strike == r.strike) & (F.cp == r.cp) & (F.d == r.t_in.normalize()) & (F.exp >= r.t_in.normalize())]
    b = m[m.side.str.contains("BUY")]; m = b if not b.empty else m
    p = m[(m.px - r.px_in).abs() < 0.011]; m = p if not p.empty else m
    return m.exp.value_counts().idxmax() if not m.empty else pd.NaT
T["exp"] = T.apply(expiry, axis=1)
T = T[T.exp.notna() & (T.t_in >= pd.Timestamp("2023-03-28"))].reset_index(drop=True)
T["t_in"] = T.t_in.dt.tz_localize(ET); T["t_out"] = T.t_out.dt.tz_localize(ET)
T["occ"] = [f"{s}{e:%y%m%d}{c}{int(round(k*1000)):08d}" for s, e, c, k in zip(T.sym, T.exp, T.cp, T.strike)]
print(f"Exact-time trades with expiry: {len(T)} | contracts: {T.occ.nunique()}", flush=True)

# ---------- Databento 1-minute bars, one request per contract window ----------
def osi(o): return o[:-15].ljust(6) + o[-15:]
def _timeout(fn, secs=240):
    box = {}
    def run():
        try: box["v"] = fn()
        except Exception as e: box["e"] = e
    th = threading.Thread(target=run, daemon=True); th.start(); th.join(secs)
    if th.is_alive(): raise TimeoutError("stalled")
    if "e" in box: raise box["e"]
    return box["v"]
def retry(fn, what, n=6):
    for k in range(n):
        try: return _timeout(fn)
        except Exception as e:
            if k == n - 1: raise
            w = min(60, 5 * 2 ** k); print(f"   {what}: {str(e)[:80]} -> retry in {w}s", flush=True); time.sleep(w)
os.makedirs(CACHE, exist_ok=True)
client = db.Historical(os.environ["DATABENTO_API_KEY"])
yday = pd.Timestamp.now(tz="UTC").normalize() - timedelta(days=1)
jobs = []
for o, g in T.groupby("occ"):
    exp_close = g.exp.iloc[0].tz_localize(ET) + timedelta(hours=16, minutes=15)
    start = g.t_in.min() - timedelta(minutes=2)
    end = min(exp_close, g.t_out.max() + timedelta(days=POST_DAYS))
    jobs.append((o, start.tz_convert("UTC"), min(end.tz_convert("UTC"), yday)))
BARS, spent = {}, 0.0
print(f"Databento 1-minute: {len(jobs)} contract requests, hard stop ${MAX_COST:.0f}", flush=True)
for j, (o, s, e) in enumerate(jobs, 1):
    cp = os.path.join(CACHE, hashlib.md5(f"{o}{s}".encode()).hexdigest()[:16] + ".pkl.gz")
    if os.path.exists(cp): df = pd.read_pickle(cp)
    else:
        kw = dict(dataset="OPRA.PILLAR", schema="ohlcv-1m", stype_in="raw_symbol", symbols=[osi(o)], start=s, end=e)
        try:
            c = retry(lambda: client.metadata.get_cost(**kw), f"{o} cost")
            if spent + c > MAX_COST:
                print(f"STOP: cost limit reached at request {j}. Analyzing what was downloaded.", flush=True); break
            df = retry(lambda: client.timeseries.get_range(**kw).to_df(), f"{o} download"); spent += c; df.to_pickle(cp)
        except Exception as ex_:
            print(f"   {o} failed: {str(ex_)[:120]}", flush=True); continue
    if not df.empty:
        df = df.reset_index(); df["t"] = pd.to_datetime(df.ts_event, utc=True).dt.tz_convert(ET)
        BARS[o] = df.rename(columns={"open": "o", "high": "h", "low": "l", "close": "c"})[["t", "o", "h", "l", "c"]].sort_values("t")
    if j % 25 == 0: print(f"  {j}/{len(jobs)} | spent ${spent:.2f} | with bars {len(BARS)}", flush=True)
print(f"Download done. Spent ${spent:.2f}. Contracts with bars: {len(BARS)}/{len(jobs)}", flush=True)

# ---------- per-trade measurements from the TRUE entry minute ----------
def sim(c, tp=None, sl=None, half=None, trail=None, mins=None, tms=None):
    first, peak = None, 0
    for k, x in enumerate(c):
        if mins is not None and tms[k] >= mins:
            return x if first is None else 0.5 * first + 0.5 * x
        if first is None:
            if half is not None and x >= 1 + half: first, peak = 1 + half, x; continue
            if half is None and tp is not None and x >= 1 + tp: return 1 + tp          # limit sell fills at target
            if sl is not None and x <= 1 - sl: return x                                # stop fills at bar close
        else:
            peak = max(peak, x)
            if x <= 1.0: return 0.5 * first + 0.5 * 1.0                               # breakeven stop on runner
            if tp is not None and x >= 1 + tp: return 0.5 * first + 0.5 * (1 + tp)
            if trail is not None and x <= peak * (1 - trail): return 0.5 * first + 0.5 * x
    last = c[-1] if len(c) else 1.0
    return 0.5 * first + 0.5 * last if first is not None else last
RULES = {"actual": {}}
for tp in (0.2, 0.3, 0.5, 1.0):
    for sl in (None, 0.2, 0.3, 0.5): RULES[f"tp{int(tp*100)}_sl{'none' if sl is None else int(sl*100)}"] = dict(tp=tp, sl=sl)
for h in (0.3, 0.5, 1.0):
    for sl in (0.3, 0.5):
        RULES[f"half@{int(h*100)}_BE_trail30_sl{int(sl*100)}"] = dict(half=h, trail=0.3, sl=sl)
        RULES[f"half@{int(h*100)}_BE_rest@200_sl{int(sl*100)}"] = dict(half=h, tp=2.0, sl=sl)
for m in (5, 15, 30, 60): RULES[f"time_{m}min"] = dict(mins=m)
RULES["hold_to_expiry_or_3d"] = dict(tp=None)

rows, paths = [], {}
for i, r in T.iterrows():
    b = BARS.get(r.occ)
    rec = dict(occ=r.occ, sym=r.sym, entry=r.t_in, exit=r.t_out, px_in=r.px_in, px_out=r.px_out,
               hold_min=(r.t_out - r.t_in).total_seconds() / 60, realized=r.px_out / r.px_in - 1)
    if b is None: rec["status"] = "no bars"; rows.append(rec); continue
    fwd = b[b.t >= r.t_in.floor("min") + timedelta(minutes=1)]                     # bars that START after the fill minute
    fwd = fwd[fwd.t <= min(r.exp.tz_localize(ET) + timedelta(hours=16, minutes=15), r.t_out + timedelta(days=POST_DAYS))]
    if fwd.empty: rec["status"] = "no bars after entry"; rows.append(rec); continue
    held = fwd[fwd.t < r.t_out.floor("min")]; after = fwd[fwd.t >= r.t_out.floor("min") + timedelta(minutes=1)]
    rec["status"] = "ok"
    rec["peak_held"] = held.c.max() / r.px_in - 1 if not held.empty else np.nan
    rec["peak_after"] = after.c.max() / r.px_in - 1 if not after.empty else np.nan
    rec["end_window"] = fwd.c.iloc[-1] / r.px_in - 1
    rows.append(rec)
    paths[i] = (fwd.c.values / r.px_in, ((fwd.t - r.t_in).dt.total_seconds() / 60).values)
D = pd.DataFrame(rows); os.makedirs(OUT, exist_ok=True); D.to_csv(f"{OUT}/minute_trades.csv", index=False)
ok = D[D.status == "ok"].copy(); idx = [i for i in T.index if i in paths]
print("Status:", D.status.value_counts().to_dict(), flush=True)

order = T.loc[idx].sort_values("t_in").index; half_n = len(order) // 2
res = []
for name, kw in RULES.items():
    m = []
    for i in order:
        c, tm = paths[i]
        m.append(T.loc[i, "px_out"] / T.loc[i, "px_in"] if name == "actual" else sim(c, tms=tm, **kw))
    m = np.array(m); ret = m - 1; lg = np.log(np.clip(m, 0.01, None))
    res.append(dict(rule=name, n=len(m), avg_pct=ret.mean() * 100, median_pct=np.median(ret) * 100, win_pct=(ret > 0).mean() * 100,
                    avg_log=lg.mean(), t_log=lg.mean() / (lg.std(ddof=1) / math.sqrt(len(lg))),
                    early_avg_pct=ret[:half_n].mean() * 100, late_avg_pct=ret[half_n:].mean() * 100,
                    early_log=lg[:half_n].mean(), late_log=lg[half_n:].mean()))
S = pd.DataFrame(res).sort_values("avg_log", ascending=False); S.to_csv(f"{OUT}/minute_rules.csv", index=False)
L = ["# Minute-level exit test — exact Robinhood fill times, real 1-minute OPRA bars", "",
     f"Trades: {len(ok)} with bars (of {len(D)}). Spent this run: ${spent:.2f}.", "",
     f"- Hold time: median {ok.hold_min.median():.0f} min",
     f"- Actual: avg {ok.realized.mean()*100:.1f}% | median {ok.realized.median()*100:.1f}% | win {(ok.realized>0).mean()*100:.1f}%",
     f"- Peak while held (minute closes): median {ok.peak_held.median()*100:.1f}%",
     f"- Went >= +20% while held, closed red: {int(((ok.peak_held>=0.2)&(ok.realized<0)).sum())} of {int((ok.realized<0).sum())} losers",
     f"- Winners: median share of in-trade peak captured: {(lambda w:(w.realized/w.peak_held).median())(ok[(ok.realized>0)&(ok.peak_held>0)])*100:.0f}%", "",
     "## Exit rules from the true entry minute (sorted by avg log return = compounding)",
     "Limit targets fill at the target; stops fill at the minute close; nothing assumed about fill times.",
     "A rule only counts if it beats 'actual' in BOTH early and late halves.", "",
     S.round(3).to_markdown(index=False)]
open(f"{OUT}/minute_report.md", "w").write("\n".join(L)); print("\n".join(L[:9]))
