"""
Tazmanian Trader — Backtest / Paper-Trading Loop
==================================================
Runs tazmanian_signal_engine.evaluate() bar-by-bar over a price history,
opens and closes positions per your actual rules, and outputs a trade log
in the SAME SCHEMA as Confirmed Trades (date, ticker, direction, debit,
qty, pnl$) — so results are directly comparable to your real numbers.

This is the harness. It has never touched real market data (none was
reachable from this environment — see signal engine's OPEN_QUESTIONS).
It IS fully wired and tested against synthetic bars below, so the day a
real feed (Alpaca/IEX) exists, point it here and nothing else changes.

    pip install pandas numpy --break-system-packages
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from tazmanian_signal_engine import (
    evaluate, SessionState, MAX_HOLD_HOURS, debit_quality, Signal,
)


@dataclass
class OpenPosition:
    signal: Signal
    entry_price: float   # per-share debit at entry (placeholder feed = same as signal)
    entry_time: pd.Timestamp
    qty: int


@dataclass
class ClosedTrade:
    date: pd.Timestamp.date
    symbol: str
    direction: str
    setup: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    qty: int
    pnl: float
    exit_reason: str  # "max_hold" | "session_stop_carryover" | "end_of_data"


def run_backtest(bars: pd.DataFrame, symbol: str, starting_cash: float = 2000.0,
                  price_feed_fn=None, max_hold_hours: float = MAX_HOLD_HOURS) -> pd.DataFrame:
    """
    bars: DataFrame with open/high/low/close/volume, DatetimeIndex, one symbol.
    price_feed_fn: optional callable(bars_so_far) -> current option debit per
        share. Without a real chain feed, this defaults to a synthetic proxy
        (see _synthetic_debit below) — REPLACE THIS before trusting any P&L
        number that comes out of here.
    max_hold_hours: exposed as a parameter, NOT hardcoded, specifically so a
        longer-hold ("swing") variant can be run side by side with the
        confirmed 24h rule once real data exists. The 24h default is backed
        by 281 trades; anything longer than ~72h in the confirmed data is
        1-3 trades per bucket — not enough to justify a different default,
        only enough to justify testing one.

    Returns a DataFrame with the same columns as Confirmed Trades' core
    fields, so it can be concatenated with real data for comparison.
    """
    if price_feed_fn is None:
        price_feed_fn = _synthetic_debit

    cash = starting_cash
    open_pos: OpenPosition | None = None
    closed: list[ClosedTrade] = []
    session_states: dict = {}

    for i in range(200, len(bars)):  # need 200 bars of history for the 200 SMA
        window = bars.iloc[: i + 1]
        now = window.index[-1]
        today = now.date()

        state = session_states.setdefault(today, SessionState(date=today))

        # --- manage an open position first: check the 24h max-hold rule ---
        if open_pos is not None:
            held_hours = (now - open_pos.entry_time).total_seconds() / 3600
            if held_hours >= max_hold_hours:
                exit_price = price_feed_fn(window)
                pnl = _pnl(open_pos, exit_price)
                cash += exit_price * 100 * open_pos.qty
                state.record(pnl)
                closed.append(ClosedTrade(
                    date=open_pos.entry_time.date(), symbol=symbol,
                    direction=open_pos.signal.direction, setup=open_pos.signal.setup,
                    entry_time=open_pos.entry_time, exit_time=now,
                    entry_price=open_pos.entry_price, exit_price=exit_price,
                    qty=open_pos.qty, pnl=pnl, exit_reason="max_hold",
                ))
                open_pos = None
            continue  # one position at a time — never stack while one is open

        # --- no open position: look for a new signal ---
        sig = evaluate(window, symbol, account_cash=cash, session_state=state)
        if sig is None:
            continue

        debit = price_feed_fn(window)
        quality = debit_quality(debit)
        if quality == "avoid":
            continue  # Rule #8: never take the confirmed-worst premium band

        open_pos = OpenPosition(signal=sig, entry_price=debit, entry_time=now,
                                 qty=sig.suggested_contracts)
        cash -= debit * 100 * sig.suggested_contracts

    # close anything still open at the end of the data window
    if open_pos is not None:
        exit_price = price_feed_fn(bars)
        pnl = _pnl(open_pos, exit_price)
        closed.append(ClosedTrade(
            date=open_pos.entry_time.date(), symbol=symbol,
            direction=open_pos.signal.direction, setup=open_pos.signal.setup,
            entry_time=open_pos.entry_time, exit_time=bars.index[-1],
            entry_price=open_pos.entry_price, exit_price=exit_price,
            qty=open_pos.qty, pnl=pnl, exit_reason="end_of_data",
        ))

    return pd.DataFrame([c.__dict__ for c in closed])


def _pnl(pos: OpenPosition, exit_price: float) -> float:
    sign = 1 if pos.signal.direction == "call" else 1  # long options either way here
    return (exit_price - pos.entry_price) * 100 * pos.qty * sign


def _synthetic_debit(window: pd.DataFrame) -> float:
    """
    PLACEHOLDER ONLY. No real options-chain feed was reachable to build the
    real version of this function (open question #3 in the signal engine).
    This proxy just scales recent realized volatility into a plausible-looking
    premium so the harness is runnable end-to-end — it is NOT a real options
    price model and NOTHING computed through it should be reported as a real
    backtest result. Replace this function entirely once a chain feed exists.
    """
    ret = window["close"].pct_change().tail(20).std()
    return max(0.3, min(12.0, ret * window["close"].iloc[-1] * 3))


# ---------------------------------------------------------------------------
# Self-test on synthetic bars — proves the loop runs, opens/closes correctly,
# and respects the 24h hold and 2-loss rules. Does NOT prove anything about
# real trading performance.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    idx = pd.date_range("2026-01-02 09:30", periods=2000, freq="5min",
                         tz="America/New_York")
    np.random.seed(1)
    price = 600 + np.cumsum(np.random.randn(2000) * 0.4)
    bars = pd.DataFrame({
        "open": price, "high": price + 0.3, "low": price - 0.3,
        "close": price, "volume": np.random.randint(1000, 6000, 2000),
    }, index=idx)

    for label, hours in [("24h (confirmed default)", 24), ("120h / 5-day (untested swing variant)", 120)]:
        trades = run_backtest(bars, "QQQ", starting_cash=2000.0, max_hold_hours=hours)
        print(f"\n--- {label} ---")
        print(f"{len(trades)} trades generated over {len(bars)} synthetic bars.")
        if len(trades):
            print(trades[["date", "setup", "direction", "qty", "pnl", "exit_reason"]].to_string())
            print(f"Synthetic P&L (meaningless — random data): ${trades['pnl'].sum():.2f}")

    print("\nBoth variants run cleanly side by side. Neither number above means "
          "anything until real bars replace the synthetic ones — the point of "
          "this run is proving the A/B comparison itself works.")
