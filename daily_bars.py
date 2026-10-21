"""Print recent daily OHLC bars (regular session, Yahoo) as GitHub annotations. SYMS env, DAYS env."""
import os
import yfinance as yf

syms = [s.strip().upper() for s in os.environ.get("SYMS", "QQQ").split(",") if s.strip()]
days = int(os.environ.get("DAYS", "12"))
for s in syms:
    d = yf.Ticker(s).history(period="1mo", interval="1d", auto_adjust=False).tail(days)
    rows = [f"{i:%m/%d} o{r.Open:.2f} h{r.High:.2f} l{r.Low:.2f} c{r.Close:.2f} v{int(r.Volume)}" for i, r in d.iterrows()]
    print(f"::notice title={s} daily::" + " %0A".join(rows))
