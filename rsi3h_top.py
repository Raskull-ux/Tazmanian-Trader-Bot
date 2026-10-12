"""
Chart data pull (NOT a test, nothing to read): downloads the stock charts behind Taz's 576 exact-time trades
so Claude can study every trade directly: volume profile, moving averages, crosses, RSI, on every timeframe.

Saves to results/chart_data/:
  minute/<SYM>.csv.gz   1-minute bars incl. extended hours (4:00-20:00) for every day Taz traded that symbol,
                        plus the 5 sessions before each trade day (for intraday volume profile)
  hourly/<SYM>.csv.gz   1-hour bars incl. extended hours, Jan 2024 -> May 2026
  daily/<SYM>.csv.gz    daily bars 2022 -> now, split-adjusted AND raw close (to line charts up with strikes)
Needs the repo's Alpaca keys. About 20-40 minutes.
"""
import os, time
import pandas as pd, requests

OUT = "results/chart_data"


def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing in this repo's secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


H = None


def bars(sym, tf, start, end, adj):
    rows, token = [], None
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": adj, "limit": 10000}
        if token:
            p["page_token"] = token
        for i in range(6):
            r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params=p, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r.status_code != 200:
            print(f"  {sym} {tf} {start}: {r.status_code} {r.text[:120]}"); break
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"], b["v"], b.get("vw")) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v", "vwap"])
    if len(d):
        d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


def main():
    global H
    H = keys()
    for sub in ("minute", "hourly", "daily"):
        os.makedirs(f"{OUT}/{sub}", exist_ok=True)
    x = pd.read_excel("Tazmanian_Trade_Record (2).xlsx", sheet_name="Exact Entry-Exit Times", header=3)
    x.columns = ["sym", "strike", "type", "entry", "exit", "hold", "in_px", "out_px"]
    x = x.dropna(subset=["sym", "entry"])
    x["entry"] = pd.to_datetime(x.entry); x["exit"] = pd.to_datetime(x.exit)
    now = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    syms = sorted(x.sym.unique())
    print(f"{len(x)} trades, {len(syms)} symbols")
    for n, sym in enumerate(syms, 1):
        t = x[x.sym == sym]
        # trading days needed: each entry..exit day, plus the 7 calendar days before entry (~5 sessions)
        days = set()
        for r in t.itertuples():
            for dday in pd.date_range(r.entry.normalize() - pd.Timedelta(days=7), r.exit.normalize()):
                if dday.weekday() < 5:
                    days.add(dday)
        days = sorted(days)
        # group consecutive days into ranges to cut requests
        ranges, s0, prev = [], None, None
        for dday in days:
            if s0 is None:
                s0 = prev = dday
            elif (dday - prev).days <= 3:
                prev = dday
            else:
                ranges.append((s0, prev)); s0 = prev = dday
        if s0 is not None:
            ranges.append((s0, prev))
        mins = []
        for a, b in ranges:
            m = bars(sym, "1Min", f"{a:%Y-%m-%d}T08:00:00Z", f"{b + pd.Timedelta(days=1):%Y-%m-%d}T04:00:00Z", "raw")
            if len(m):
                mins.append(m)
        if mins:
            pd.concat(mins).drop_duplicates("t").sort_values("t").to_csv(f"{OUT}/minute/{sym}.csv.gz", index=False, compression="gzip")
        hr = bars(sym, "1Hour", "2024-01-01T00:00:00Z", "2026-06-01T00:00:00Z", "raw")
        if len(hr):
            hr.to_csv(f"{OUT}/hourly/{sym}.csv.gz", index=False, compression="gzip")
        ds = bars(sym, "1Day", "2022-01-01T00:00:00Z", now, "split")
        dr = bars(sym, "1Day", "2022-01-01T00:00:00Z", now, "raw")
        if len(ds):
            ds = ds.merge(dr[["t", "c"]].rename(columns={"c": "c_raw"}), on="t", how="left")
            ds.to_csv(f"{OUT}/daily/{sym}.csv.gz", index=False, compression="gzip")
        print(f"  [{n}/{len(syms)}] {sym}: {len(t)} trades, {sum(len(m) for m in mins)} minute bars, {len(hr)} hourly, {len(ds)} daily", flush=True)
    print("DONE")


if __name__ == "__main__":
    main()
