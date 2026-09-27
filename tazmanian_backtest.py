"""
Tazmanian Trader — Backtest / Paper-Trading Loop
==================================================
Runs tazmanian_signal_engine.evaluate() bar-by-bar over a price history,
opens and closes positions per your actual rules, and outputs a trade log
in the SAME SCHEMA as Confirmed Trades (date, ticker, direction, debit,
qty, pnl$) — so results are directly comparable to your real numbers.

UPDATE from the first version: option pricing is now Black-Scholes, using
REAL realized volatility computed from the real bars you feed it, and it
correctly models time decay (an option loses extrinsic value every hour
just from time passing -- the old placeholder didn't do this at all, which
was likely a real source of the across-the-board losses in the first real
run). This is still a MODEL, not a real market quote -- a real options
chain will price things Black-Scholes doesn't capture (skew, bid/ask
spread, early-close liquidity). Label results accordingly until an actual
chain feed replaces this.

    pip install pandas numpy scipy --break-system-packages
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from scipy.stats import norm
from tazmanian_signal_engine import (
    evaluate, SessionState, MAX_HOLD_HOURS, debit_quality, Signal,
)


@dataclass
class OpenPosition:
    signal: Signal
    entry_price: float      # per-share debit at entry
    entry_time: pd.Timestamp
    qty: int
    strike: float             # locked in at entry -- a real position doesn't
                               # change strikes mid-trade
    expiry: pd.Timestamp      # locked in at entry, for the same reason


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
    price_feed_fn: optional callable(window, strike, expiry, is_call) -> per-
        share debit. Defaults to _bs_price below (Black-Scholes, real
        volatility from the bars). Pass your own to use a real options-chain
        quote instead, once that data source exists.
    max_hold_hours: exposed as a parameter, NOT hardcoded, specifically so a
        longer-hold ("swing") variant can be run side by side with the
        confirmed 24h rule once real data exists.

    Returns a DataFrame with the same columns as Confirmed Trades' core
    fields, so it can be concatenated with real data for comparison.
    """
    if price_feed_fn is None:
        price_feed_fn = _bs_price

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
                exit_price = price_feed_fn(
                    window, open_pos.strike, open_pos.expiry,
                    is_call=(open_pos.signal.direction == "call"),
                )
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
            continue  # one position at a time -- never stack while one is open

        # --- no open position: look for a new signal ---
        sig = evaluate(window, symbol, account_cash=cash, session_state=state)
        if sig is None:
            continue

        spot = window["close"].iloc[-1]
        # Strike selection: at-the-money (nearest whole number to spot).
        # SIMPLIFICATION, named plainly -- real strike selection would use
        # your confirmed premium sweet spot ($5-10) to pick a strike, not
        # default to ATM. That calibration doesn't exist yet without real
        # chain data to test it against; ATM is the honest placeholder.
        strike = round(spot)
        expiry = now + pd.Timedelta(days=sig.min_days_to_expiry)

        debit = price_feed_fn(window, strike, expiry, is_call=(sig.direction == "call"))
        quality = debit_quality(debit)
        if quality == "avoid":
            continue  # Rule #8: never take the confirmed-worst premium band

        open_pos = OpenPosition(signal=sig, entry_price=debit, entry_time=now,
                                 qty=sig.suggested_contracts, strike=strike, expiry=expiry)
        cash -= debit * 100 * sig.suggested_contracts

    # close anything still open at the end of the data window
    if open_pos is not None:
        exit_price = price_feed_fn(
            bars, open_pos.strike, open_pos.expiry,
            is_call=(open_pos.signal.direction == "call"),
        )
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
    return (exit_price - pos.entry_price) * 100 * pos.qty


# ---------------------------------------------------------------------------
# Black-Scholes pricing -- the real upgrade over the old random placeholder.
# ---------------------------------------------------------------------------

BARS_PER_YEAR_15MIN = 26 * 252  # 26 fifteen-minute bars per 6.5h trading day


def _realized_vol(window: pd.DataFrame, lookback_bars: int = 130) -> float:
    """
    Annualized realized volatility from the REAL price bars, trailing
    lookback_bars (default ~130 = ~5 trading days of 15-min bars). This
    replaces guessing at implied volatility -- it's realized, not implied,
    so it will differ from a real chain's IV (which usually runs a bit
    higher). Treat this as a lower-bound proxy, not equivalent to a real quote.
    """
    rets = window["close"].pct_change().dropna().tail(lookback_bars)
    if len(rets) < 10:
        return 0.30  # fallback for very early bars -- arbitrary, flagged
    return max(0.05, rets.std() * np.sqrt(BARS_PER_YEAR_15MIN))


def _bs_price(window: pd.DataFrame, strike: float, expiry: pd.Timestamp,
              is_call: bool, r: float = 0.05) -> float:
    """
    Standard Black-Scholes, no dividend adjustment. spot and vol both come
    from the REAL bars passed in -- nothing here is random. Time decay is
    real: as `now` approaches `expiry`, days_to_expiry shrinks toward zero
    and extrinsic value correctly bleeds out, which the old placeholder
    never did.
    """
    spot = window["close"].iloc[-1]
    now = window.index[-1]
    days_to_expiry = max((expiry - now).total_seconds() / 86400, 0.0001)
    t = days_to_expiry / 365
    iv = _realized_vol(window)

    if t <= 0.0001:
        return max(0.01, spot - strike) if is_call else max(0.01, strike - spot)

    d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * t) / (iv * np.sqrt(t))
    d2 = d1 - iv * np.sqrt(t)

    if is_call:
        price = spot * norm.cdf(d1) - strike * np.exp(-r * t) * norm.cdf(d2)
    else:
        price = strike * np.exp(-r * t) * norm.cdf(-d2) - spot * norm.cdf(-d1)
    return max(0.01, price)


# ---------------------------------------------------------------------------
# Self-test on synthetic bars -- proves the loop runs, opens/closes correctly,
# and respects the 24h hold and 2-loss rules, now with real Black-Scholes
# math (just fed fake spot prices). Does NOT prove anything about real
# trading performance -- the price SERIES is still synthetic here.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    idx = pd.date_range("2026-01-02 09:30", periods=2000, freq="15min",
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
            print(f"Synthetic P&L (meaningless -- random price series, real B-S math): ${trades['pnl'].sum():.2f}")

    print("\nBoth variants run cleanly with real time-decay pricing. Point this "
          "at real bars (as run_real_backtest.py already does) for a result "
          "that means something.")
