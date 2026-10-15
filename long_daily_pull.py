"""Long daily history (Yahoo, free) for index ETFs: QQQ/SPY/IWM/DIA since inception. Saves results/long_daily/<SYM>.csv"""
import os
import pandas as pd, yfinance as yf

os.makedirs("results/long_daily", exist_ok=True)
for s in ["QQQ", "SPY", "IWM", "DIA", "^NDX", "^GSPC"]:
    d = yf.download(s, start="1985-01-01", progress=False, auto_adjust=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
    d.columns = ["t", "o", "h", "l", "c", "v"]
    d.to_csv(f"results/long_daily/{s.replace('^', 'IDX_')}.csv", index=False)
    print(s, len(d), d.t.iloc[0], d.t.iloc[-1])
