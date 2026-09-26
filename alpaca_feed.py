"""
Tazmanian Trader — Alpaca Data Adapter
=======================================
Pulls real OHLCV bars from Alpaca's Market Data API and returns them in the
exact schema tazmanian_signal_engine.evaluate() and tazmanian_backtest.run_backtest()
already expect: a pandas DataFrame with columns open/high/low/close/volume,
indexed by a tz-aware DatetimeIndex, one row per bar. No changes to either of
those two files are required — this module is the only thing that changes
when the data source changes.

Credentials are read from environment variables, never hardcoded here or
anywhere else in this repo:

    export ALPACA_API_KEY_ID="your-key-id"
    export ALPACA_API_SECRET_KEY="your-secret-key"

Get a free key at https://app.alpaca.markets (paper trading keys work fine
for market data — this module only calls the data API, never the trading API).

    pip install requests pandas --break-system-packages
"""

from __future__ import annotations
import os
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

DATA_BASE_URL = "https://data.alpaca.markets"


class AlpacaAuthError(RuntimeError):
    pass


class AlpacaFeed:
    """
    Thin wrapper over Alpaca's /v2/stocks/{symbol}/bars endpoint.

    feed: "iex" (free tier, real-time-delayed) or "sip" (paid, full-market).
    Free/paper accounts only have access to "iex" — that's the default here.
    """

    def __init__(self, api_key_id: Optional[str] = None, api_secret_key: Optional[str] = None,
                 feed: str = "iex"):
        self.api_key_id = api_key_id or os.environ.get("ALPACA_API_KEY_ID")
        self.api_secret_key = api_secret_key or os.environ.get("ALPACA_API_SECRET_KEY")
        if not self.api_key_id or not self.api_secret_key:
            raise AlpacaAuthError(
                "Missing Alpaca credentials. Set ALPACA_API_KEY_ID and "
                "ALPACA_API_SECRET_KEY as environment variables — never hardcode "
                "them in source."
            )
        self.feed = feed
        self._headers = {
            "APCA-API-KEY-ID": self.api_key_id,
            "APCA-API-SECRET-KEY": self.api_secret_key,
        }

    def get_bars(self, symbol: str, timeframe: str, start: str, end: str,
                 limit: int = 10000, max_retries: int = 5) -> pd.DataFrame:
        """
        timeframe: Alpaca's format — "1Day", "1Hour", "15Min", "5Min", "1Min".
        start/end: ISO8601 dates or datetimes, e.g. "2025-01-01" or
                   "2025-01-01T09:30:00-05:00".

        Returns a DataFrame indexed by tz-aware timestamp (converted to
        America/New_York) with columns: open, high, low, close, volume.
        Empty DataFrame (not an error) if the range has no bars, e.g. a
        weekend/holiday range or a symbol with no history that far back.
        """
        url = f"{DATA_BASE_URL}/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "limit": limit,
            "feed": self.feed,
            "adjustment": "raw",
        }

        rows = []
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token

            resp = self._get_with_retry(url, params, max_retries)
            payload = resp.json()
            bars = payload.get("bars") or []
            rows.extend(bars)

            page_token = payload.get("next_page_token")
            if not page_token:
                break

        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        df = pd.DataFrame(rows)
        # Alpaca's bar schema: t (RFC3339 timestamp), o, h, l, c, v, n, vw
        df["timestamp"] = pd.to_datetime(df["t"], utc=True).dt.tz_convert("America/New_York")
        df = df.set_index("timestamp").sort_index()
        df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        return df[["open", "high", "low", "close", "volume"]]

    def _get_with_retry(self, url: str, params: dict, max_retries: int) -> requests.Response:
        backoff = 1.0
        for attempt in range(max_retries):
            resp = requests.get(url, headers=self._headers, params=params, timeout=30)
            if resp.status_code == 200:
                return resp
            if resp.status_code in (401, 403):
                raise AlpacaAuthError(
                    f"Alpaca rejected credentials ({resp.status_code}): {resp.text}"
                )
            if resp.status_code == 429 or resp.status_code >= 500:
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
        resp.raise_for_status()
        return resp  # unreachable, satisfies type checkers


def get_bars_for_backtest(symbol: str, start: str, end: str,
                           timeframe: str = "1Day", feed: str = "iex") -> pd.DataFrame:
    """
    Convenience entry point matching what tazmanian_backtest.run_backtest()
    needs directly:

        from alpaca_feed import get_bars_for_backtest
        bars = get_bars_for_backtest("QQQ", "2025-01-01", "2026-01-01")
        trades = run_backtest(bars, "QQQ", max_hold_hours=24)

    Use timeframe="1Day" for the 200-SMA / session-edge rules as written
    (they're daily-bar rules per the signal engine). Use an intraday
    timeframe ("5Min" etc.) only if you also wire up rvol_time_matched(),
    which the current evaluate() does not call.
    """
    feed_client = AlpacaFeed(feed=feed)
    return feed_client.get_bars(symbol, timeframe, start, end)


if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "QQQ"
    bars = get_bars_for_backtest(symbol, "2025-01-01", "2026-01-01")
    print(f"{symbol}: {len(bars)} daily bars")
    print(bars.head())
    print(bars.tail())
