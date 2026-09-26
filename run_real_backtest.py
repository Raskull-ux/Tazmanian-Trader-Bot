"""
Tazmanian Trader — Real-Data Backtest Runner
=============================================
Pulls real bars from Alpaca via alpaca_feed.py and runs run_backtest() for
each symbol in WATCHLIST, at both MAX_HOLD_HOURS variants (24h confirmed
default, 120h untested swing variant), then prints a summary comparable to
the Confirmed Trades sheet (fire rate, win rate, total P&L per bucket).

Requires ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY set in the environment.
Does not read or write those values to disk anywhere in this script.

    python3 run_real_backtest.py
"""

from __future__ import annotations
import sys
import pandas as pd
from alpaca_feed import fetch_bars
from tazmanian_backtest import run_backtest

WATCHLIST = ["QQQ", "INTC", "BA"]
START = "2025-01-01"
END = "2026-09-26"
HOLD_VARIANTS = [("24h (confirmed default)", 24), ("120h / 5-day (untested swing variant)", 120)]


def summarize(trades: pd.DataFrame, bars_len: int) -> dict:
    if trades.empty:
        return {"fired": 0, "fire_rate_pct": 0.0, "win_rate_pct": 0.0, "total_pnl": 0.0}
    wins = (trades["pnl"] > 0).sum()
    return {
        "fired": len(trades),
        "fire_rate_pct": round(len(trades) / bars_len * 100, 3),
        "win_rate_pct": round(wins / len(trades) * 100, 1),
        "total_pnl": round(trades["pnl"].sum(), 2),
    }


def main():
    all_results = []
    for symbol in WATCHLIST:
        print(f"\n=== {symbol}: fetching {START} to {END} (15-min bars, IEX feed) ===")
        try:
            bars = fetch_bars(symbol, START, END, timeframe_minutes=15)
        except Exception as e:
            print(f"FAILED to fetch {symbol}: {e}", file=sys.stderr)
            continue

        if len(bars) < 200:
            print(f"Only {len(bars)} bars returned for {symbol} — not enough for the "
                  f"200 SMA (needs 200+). Skipping. Check date range / feed entitlement.")
            continue

        print(f"{len(bars)} bars fetched.")

        for label, hours in HOLD_VARIANTS:
            trades = run_backtest(bars, symbol, starting_cash=2000.0, max_hold_hours=hours)
            stats = summarize(trades, len(bars))
            stats.update({"symbol": symbol, "hold_variant": label})
            all_results.append(stats)
            print(f"  [{label}] fired={stats['fired']} "
                  f"fire_rate={stats['fire_rate_pct']}% "
                  f"win_rate={stats['win_rate_pct']}% "
                  f"total_pnl=${stats['total_pnl']}")

            if not trades.empty:
                out_path = f"backtest_{symbol}_{hours}h.csv"
                trades.to_csv(out_path, index=False)
                print(f"  -> trade log written to {out_path}")

    print("\n=== SUMMARY (compare against your real Confirmed Trades numbers) ===")
    if all_results:
        print(pd.DataFrame(all_results).to_string(index=False))
    else:
        print("No results — every symbol failed to fetch or had insufficient bars.")


if __name__ == "__main__":
    main()
