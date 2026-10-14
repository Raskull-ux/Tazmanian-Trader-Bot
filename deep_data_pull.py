"""
Deep data pull (NOT a test). Downloads 10 years of charts for every name Taz has called or traded,
plus the core ETF/stock list, and publishes them to the repo's `data` branch so the deep analysis
can run on them (whole-chart study, pattern tests across names).

Per symbol, saved as data/<tf>/<SYM>.parquet:
  m5     5-minute bars INCLUDING pre-market and after-hours (4:00-20:00 ET), 2016 -> now, split-adjusted
         (Taz charts with extended hours on in thinkorswim, so moving averages must include those bars)
  daily  daily bars 2015 -> now, split-adjusted, plus raw close (c_raw) to match option strikes
Plus data/vix.parquet (daily VIX from Yahoo).
Hourly, 4-hour and weekly bars are built from these inside the analysis (same way TradingView builds them).
"""
import os, time, sys
import pandas as pd, numpy as np, requests

OUT = "deepdata"
H = None


def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing in this repo's secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


def bars(sym, tf, start, end, adj):
    rows, token = [], None
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip",
             "adjustment": adj, "limit": 10000}
        if token:
            p["page_token"] = token
        r = None
        for i in range(7):
            try:
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=90)
            except Exception as e:
                print("  net error", e); time.sleep(2 ** i); continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r is None or r.status_code != 200:
            print(f"  {sym} {tf}: {getattr(r, 'status_code', '?')} {getattr(r, 'text', '')[:150]}")
            break
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v"])
    if len(d):
        d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


def symbols():
    s = set()
    try:
        g = pd.read_csv("results/call_grades/graded_calls.csv")
        s |= set(g[g.tier == "A"].ticker)
    except Exception as e:
        print("calls:", e)
    try:
        x = pd.read_excel("Tazmanian_Trade_Record (2).xlsx", sheet_name="Exact Entry-Exit Times", header=3)
        s |= set(x.iloc[:, 0].dropna().astype(str))
    except Exception as e:
        print("trades:", e)
    s |= set("QQQ SPY IWM DIA XLK SMH XLF XLE XLV ARKK TLT".split())
    s |= set(("AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX MU INTC BA JPM BAC XOM DIS UBER SHOP CRWD PLTR "
              "COIN SOFI HOOD MSTR CMG ORCL CRM MRNA PANW COST NKE SNOW RKLB ABNB LULU ULTA CVNA").split())
    return sorted(x for x in s if isinstance(x, str) and x.isalpha() and len(x) <= 5)


def main():
    global H
    H = keys()
    for sub in ("m5", "daily"):
        os.makedirs(f"{OUT}/{sub}", exist_ok=True)
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    syms = symbols()
    shard, nsh = int(os.environ.get("SHARD", "0")), int(os.environ.get("NSHARDS", "1"))
    syms = syms[shard::nsh]
    print(len(syms), "symbols in this shard:", " ".join(syms), flush=True)
    t0 = time.time()
    for n, sym in enumerate(syms, 1):
        d = bars(sym, "1Day", "2015-01-01", end, "split")
        if len(d) == 0:
            print(f"[{n}/{len(syms)}] {sym}: no daily data, skipped", flush=True); continue
        raw = bars(sym, "1Day", "2015-01-01", end, "raw")[["t", "c"]].rename(columns={"c": "c_raw"})
        d = d.merge(raw, on="t", how="left")
        d["t"] = d.t.dt.normalize()
        for c in "ohlc":
            d[c] = d[c].astype("float64")
        d.to_parquet(f"{OUT}/daily/{sym}.parquet", index=False)
        m = bars(sym, "5Min", "2016-01-01", end, "split")
        if len(m):
            tod = m.t.dt.hour * 60 + m.t.dt.minute
            m = m[(tod >= 240) & (tod < 1200)].reset_index(drop=True)   # 4:00 AM - 8:00 PM ET, like Taz's TOS chart
            for c in "ohlc":
                m[c] = m[c].astype("float32")
            m["v"] = m.v.astype("float32")
            m.to_parquet(f"{OUT}/m5/{sym}.parquet", index=False, compression="zstd")
        print(f"[{n}/{len(syms)}] {sym}: daily {len(d)}  5min {len(m)}  ({time.time() - t0:.0f}s)", flush=True)
    if shard != 0:
        return
    try:
        import yfinance as yf
        v = yf.download("^VIX", start="2015-01-01", progress=False, auto_adjust=False)
        if isinstance(v.columns, pd.MultiIndex):
            v.columns = v.columns.get_level_values(0)
        v = v.reset_index()[["Date", "Close"]].rename(columns={"Date": "t", "Close": "vix"})
        v.to_parquet(f"{OUT}/vix.parquet", index=False)
        print("VIX rows", len(v))
    except Exception as e:
        print("VIX failed:", e)


if __name__ == "__main__":
    main()
