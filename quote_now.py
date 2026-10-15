"""Prints QQQ's latest trade (IEX, free real-time) and today's premarket range, as a GitHub annotation."""
import os, requests, pandas as pd
k = (os.environ.get("ALPACA_API_KEY_ID") or "").strip(); s = (os.environ.get("ALPACA_API_SECRET_KEY") or "").strip()
H = {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}
out = []
for sym in os.environ.get("SYMS", "QQQ,SPY").split(","):
    t = requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/trades/latest", headers=H, params={"feed": "iex"}, timeout=30).json()
    today = pd.Timestamp.now(tz="America/New_York").normalize()
    b = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=H, params={"symbols": sym, "timeframe": "5Min",
        "start": (today + pd.Timedelta(hours=4)).isoformat(), "feed": "iex", "limit": 1000}, timeout=30).json()
    bars = (b.get("bars") or {}).get(sym, [])
    hi = max([x["h"] for x in bars], default=None); lo = min([x["l"] for x in bars], default=None)
    out.append(f"{sym} last {t.get('trade', {}).get('p')} at {t.get('trade', {}).get('t')} | today since 4am: high {hi} low {lo} bars {len(bars)}")
msg = " %0A".join(out)
print(msg.replace(" %0A", "\n"))
print(f"::notice title=quote::{msg}")
