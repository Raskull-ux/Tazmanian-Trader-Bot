"""
Repairs the extended-hours data on the data_ext branch. The first pull got rate-limited (it shared the
Alpaca key with other jobs) and the old code quietly kept whatever it had, so many names stop early.
This version:
  - resumes each symbol from its last saved 5-min bar (no re-downloading what's already there)
  - NEVER gives up quietly on a rate limit: waits it out; any other failure is recorded, not hidden
  - writes COMPLETENESS.csv so every name's coverage is visible
Reads existing files from ./existing (data_ext checkout), writes repaired files to ./repaired.
"""
import os, time
import pandas as pd, requests
import deep_data_pull as base

SRC, DST = "existing", "repaired"


def bars(sym, tf, start, end, adj):
    rows, token = [], None
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip",
             "adjustment": adj, "limit": 10000}
        if token:
            p["page_token"] = token
        fails, limited = 0, 0
        while True:
            try:
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=base.H, params=p, timeout=90)
            except Exception as e:
                fails += 1
                if fails > 8:
                    raise RuntimeError(f"{sym} {tf}: network error {e}")
                time.sleep(3 * fails); continue
            if r.status_code == 429:
                limited += 1
                time.sleep(min(3 * limited, 30)); continue
            if r.status_code >= 500:
                fails += 1
                if fails > 8:
                    raise RuntimeError(f"{sym} {tf}: HTTP {r.status_code}")
                time.sleep(3 * fails); continue
            if r.status_code != 200:
                raise RuntimeError(f"{sym} {tf}: HTTP {r.status_code} {r.text[:150]}")
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


def main():
    base.H = base.keys()
    for sub in ("m5", "daily"):
        os.makedirs(f"{DST}/{sub}", exist_ok=True)
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    syms = base.symbols()
    shard, nsh = int(os.environ.get("SHARD", "0")), int(os.environ.get("NSHARDS", "1"))
    syms = syms[shard::nsh]
    status = []
    t0 = time.time()
    for n, sym in enumerate(syms, 1):
        try:
            dp = f"{SRC}/daily/{sym}.parquet"
            if os.path.exists(dp):
                d = pd.read_parquet(dp)
            else:
                d = bars(sym, "1Day", "2015-01-01", end, "split")
                raw = bars(sym, "1Day", "2015-01-01", end, "raw")[["t", "c"]].rename(columns={"c": "c_raw"})
                d = d.merge(raw, on="t", how="left")
                d["t"] = d.t.dt.normalize()
                for c in "ohlc":
                    d[c] = d[c].astype("float64")
                d.to_parquet(f"{DST}/daily/{sym}.parquet", index=False)
            last_daily = pd.to_datetime(d.t).max().normalize()
            mp = f"{SRC}/m5/{sym}.parquet"
            m_old = pd.read_parquet(mp) if os.path.exists(mp) else None
            start = "2016-01-01"
            if m_old is not None and len(m_old):
                last = pd.to_datetime(m_old.t).max()
                if last.normalize() >= last_daily:
                    status.append(dict(sym=sym, status="already complete", first=m_old.t.min(), last=last, bars=len(m_old)))
                    print(f"[{n}/{len(syms)}] {sym}: already complete", flush=True)
                    continue
                start = (last + pd.Timedelta(minutes=5)).tz_localize("America/New_York").tz_convert("UTC").isoformat()
            new = bars(sym, "5Min", start, end, "split")
            if len(new):
                tod = new.t.dt.hour * 60 + new.t.dt.minute
                new = new[(tod >= 240) & (tod < 1200)]
                for c in "ohlcv":
                    new[c] = new[c].astype("float32")
            m = pd.concat([m_old, new]) if m_old is not None else new
            m = m.drop_duplicates("t").sort_values("t").reset_index(drop=True)
            m.to_parquet(f"{DST}/m5/{sym}.parquet", index=False, compression="zstd")
            last = pd.to_datetime(m.t).max()
            ok = last.normalize() >= last_daily
            status.append(dict(sym=sym, status="repaired" if ok else "STILL SHORT", first=m.t.min(), last=last,
                               bars=len(m)))
            print(f"[{n}/{len(syms)}] {sym}: +{len(new)} bars, now {m.t.min()} -> {last} "
                  f"{'OK' if ok else 'STILL SHORT'} ({time.time() - t0:.0f}s)", flush=True)
        except Exception as e:
            status.append(dict(sym=sym, status=f"FAILED: {e}"))
            print(f"[{n}/{len(syms)}] {sym}: FAILED {e}", flush=True)
    pd.DataFrame(status).to_csv(f"{DST}/completeness_shard{shard}.csv", index=False)


if __name__ == "__main__":
    main()
