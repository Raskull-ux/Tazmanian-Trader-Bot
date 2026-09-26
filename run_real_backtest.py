"""
Tazmanian Trader — Real-Data Backtest Runner
==============================================
Pulls real daily bars for the watchlist via alpaca_feed, runs
tazmanian_backtest.run_backtest() for both the confirmed 24h hold and the
untested 120h/5-day variant, and prints a summary directly comparable to
the Confirmed Trades numbers (297 trades, +$6,451 total, ~51% win rate
blended across setups).

Usage:
    export ALPACA_API_KEY_ID="..."
    export ALPACA_API_SECRET_KEY="..."
    python3 run_real_backtest.py

Requires outbound network access to data.alpaca.markets. If this
environment's network policy blocks that host, this script will raise on
the first get_bars_for_backtest() call — see alpaca_feed.py and the
session's network settings.
"""

from __future__ import annotations
import sys
import pandas as pd

from alpaca_feed import get_bars_for_backtest
from tazmanian_backtest import run_backtest

WATCHLIST = ["QQQ", "INTC", "BA"]
HOLD_WINDOWS_HOURS = [24, 120]
START = "2025-01-01"
END = "2026-01-01"


def summarize(trades: pd.DataFrame, symbol: str, hold_hours: int) -> dict:
    if trades.empty:
        return {
            "symbol": symbol, "hold_hours": hold_hours, "n_trades": 0,
            "win_rate": None, "total_pnl": 0.0, "avg_pnl": None,
        }
    wins = (trades["pnl"] > 0).sum()
    return {
        "symbol": symbol,
        "hold_hours": hold_hours,
        "n_trades": len(trades),
        "win_rate": round(100 * wins / len(trades), 1),
        "total_pnl": round(trades["pnl"].sum(), 2),
        "avg_pnl": round(trades["pnl"].mean(), 2),
    }


def main():
    results = []
    all_trades = []

    for symbol in WATCHLIST:
        print(f"Fetching {symbol} daily bars {START} to {END}...")
        bars = get_bars_for_backtest(symbol, START, END, timeframe="1Day")
        print(f"  {len(bars)} bars fetched.")
        if len(bars) < 200:
            print(f"  SKIP {symbol}: fewer than 200 bars, 200-SMA rule can't fire.")
            continue

        for hold_hours in HOLD_WINDOWS_HOURS:
            trades = run_backtest(bars, symbol, starting_cash=2000.0, max_hold_hours=hold_hours)
            trades["hold_window_hours"] = hold_hours
            all_trades.append(trades)
            summary = summarize(trades, symbol, hold_hours)
            results.append(summary)
            print(f"  [{symbol} / {hold_hours}h hold] {summary}")

    print("\n" + "=" * 70)
    print("SUMMARY — real-data backtest vs. Confirmed Trades (297 trades, "
          "+$6,451 total, 24h-hold-dominant)")
    print("=" * 70)
    for r in results:
        wr = f"{r['win_rate']}%" if r['win_rate'] is not None else "n/a"
        print(f"{r['symbol']:>6}  hold={r['hold_hours']:>3}h  "
              f"n={r['n_trades']:>4}  win_rate={wr:>6}  "
              f"total_pnl=${r['total_pnl']:>10,.2f}")

    if all_trades:
        combined = pd.concat(all_trades, ignore_index=True)
        combined.to_csv("real_backtest_trades.csv", index=False)
        print(f"\nFull trade log written to real_backtest_trades.csv "
              f"({len(combined)} rows).")
    else:
        print("\nNo trades generated across any symbol/hold-window combination.")


if __name__ == "__main__":
    main()
