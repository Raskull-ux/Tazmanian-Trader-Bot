"""Live intraday pull for the day-trade read: 5m bars with extended hours (60 days) + daily (2 years), saved to results/live/."""
import os, time, pandas as pd, yfinance as yf
SYMS = os.environ.get("SYMS", "QQQ,SPY,NVDA,META,AAPL,AMD,TSLA,AVGO,MSFT,GOOGL,AMZN,NFLX,HOOD,PLTR,CMG,SLV").split(",")
os.makedirs("results/live", exist_ok=True)
fr, dl = [], []
for s in SYMS:
    s = s.strip().replace(".", "-")
    m = d = None
    for _ in range(3):
        try:
            m = yf.Ticker(s).history(period="60d", interval="5m", prepost=True, auto_adjust=False)
            d = yf.Ticker(s).history(period="2y", interval="1d", auto_adjust=False); break
        except Exception as e:
            print("retry", s, e); time.sleep(3)
    if m is None or d is None or m.empty or d.empty:
        print("skip", s, "(no data)"); continue
    m = m[["Open", "High", "Low", "Close", "Volume"]].copy(); m.columns = ["o", "h", "l", "c", "v"]
    m.index = m.index.tz_convert("America/New_York").tz_localize(None); m["sym"] = s; fr.append(m)
    d = d[["Open", "High", "Low", "Close", "Volume"]].copy(); d.columns = ["o", "h", "l", "c", "v"]
    d.index = d.index.tz_localize(None).normalize(); d["sym"] = s; dl.append(d)
    print(s, len(m), m.index[-1], m.c.iloc[-1])
pd.concat(fr).reset_index(names="t").to_csv("results/live/m5.csv.gz", index=False)
pd.concat(dl).reset_index(names="t").to_csv("results/live/daily.csv.gz", index=False)
print(f"::notice title=pulled::{len(SYMS)} symbols, last 5m bar {fr[0].index[-1]}")
