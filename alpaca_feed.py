"""
Tazmanian Trader — Alpaca Market Data Adapter
==============================================
Pulls real bars from Alpaca's Market Data API and returns them in the exact
format tazmanian_backtest.run_backtest() and tazmanian_signal_engine.evaluate()
already expect: a pandas DataFrame with columns open/high/low/close/volume,
a DatetimeIndex localized to America/New_York.

The America/New_York localization is not cosmetic — session_bucket() in the
signal engine buckets a bar by ts.hour/ts.minute assuming those are ET clock
values. Alpaca returns UTC timestamps; skip the conversion and every
open/late_morning/midday/afternoon/power_hour edge lookup silently uses the
wrong bucket for roughly half the year (DST) and all of it outside EST.

Credentials: read ONLY from environment variables, never hardcoded here and
never logged. Set before running:

    export ALPACA_API_KEY_ID="your key id"
    export ALPACA_API_SECRET_KEY="your secret key"

    pip install alpaca-py pandas --break-system-packages
"""

from __future__ import annotations
import os
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed


def _client() -> StockHistoricalDataClient:
    key = os.environ.get("ALPACA_API_KEY_ID")
    secret = os.environ.get("ALPACA_API_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError(
            "ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY not set in the "
            "environment. Set them before calling fetch_bars() — never "
            "hardcode credentials into this file."
        )
    return StockHistoricalDataClient(key, secret)


def fetch_bars(symbol: str, start: str, end: str,
               timeframe_minutes: int = 15,
               feed: DataFeed = DataFeed.IEX) -> pd.DataFrame:
    """
    Returns a DataFrame with columns open/high/low/close/volume, indexed by
    a DatetimeIndex localized to America/New_York, ready to hand directly to
    tazmanian_backtest.run_backtest(bars, symbol, ...).

    symbol: single ticker, e.g. "QQQ", "INTC", "BA".
    start/end: "YYYY-MM-DD" strings (or anything pandas.Timestamp parses).
    timeframe_minutes: bar size. 15-min is Alpaca's free-tier-friendly
        granularity for intraday history; drop to 5 if your plan allows it.
    feed: DataFeed.IEX is available on Alpaca's free/paper tier. Switch to
        DataFeed.SIP only if your account is entitled to it.
    """
    client = _client()
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame(timeframe_minutes, TimeFrameUnit.Minute),
        start=pd.Timestamp(start, tz="America/New_York"),
        end=pd.Timestamp(end, tz="America/New_York"),
        feed=feed,
    )
    bar_set = client.get_stock_bars(request)
    df = bar_set.df

    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    # bar_set.df is MultiIndex (symbol, timestamp) when fetched via
    # symbol_or_symbols regardless of single/multi-symbol request.
    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")

    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index = df.index.tz_convert("America/New_York")
    df.index.name = None
    return df.sort_index()


def fetch_daily_bars(symbol: str, start: str, end: str,
                      feed: DataFeed = DataFeed.IEX) -> pd.DataFrame:
    """Same contract as fetch_bars(), but one row per trading day."""
    client = _client()
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=pd.Timestamp(start, tz="America/New_York"),
        end=pd.Timestamp(end, tz="America/New_York"),
        feed=feed,
    )
    bar_set = client.get_stock_bars(request)
    df = bar_set.df

    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    if isinstance(df.index, pd.MultiIndex):
        df = df.xs(symbol, level="symbol")

    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index = df.index.tz_convert("America/New_York")
    df.index.name = None
    return df.sort_index()


if __name__ == "__main__":
    bars = fetch_bars("QQQ", "2025-01-01", "2025-01-31")
    print(f"{len(bars)} bars fetched for QQQ, 2025-01-01 to 2025-01-31")
    print(bars.head())
