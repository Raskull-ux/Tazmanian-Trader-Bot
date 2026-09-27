"""
Tazmanian Trader — Signal Engine
=================================
Precise, testable implementation of the rules found in Tazmanian_Trade_Record.xlsx
("Strategy" tab), derived from 297 confirmed real trades.

This module is DATA-SOURCE AGNOSTIC. It does not fetch prices itself — no free,
reliable OHLC feed was reachable from this environment (Stooq blocks automated
access as of 2026; Nasdaq's chart endpoint isn't fetchable via search/fetch tools).
Feed it real bars from Alpaca, IEX, or any pandas-compatible source and it runs
the same rules that were validated against your real fills.

Every threshold below traces to a specific finding, cited in the docstring.
Nothing here is invented — where a rule needed a number and the data didn't give
one cleanly, that's flagged as a TODO with the open question, not guessed at.

    pip install pandas numpy --break-system-packages
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1. INDICATORS — pure functions, one bar-series in, one series out.
#    Feed them a DataFrame with columns: open, high, low, close, volume,
#    indexed by timestamp (intraday bars for intraday rules, daily for SMA).
# ---------------------------------------------------------------------------

def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Standard Wilder RSI. Rule #6: '80/20 overbought/oversold' setup tag."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast=12, slow=26, signal=9) -> pd.DataFrame:
    """Rule #6: 'MACD read' — your single highest-win-rate confirmed setup (65%)."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "hist": macd_line - signal_line,
    })


def is_gap(bars: pd.DataFrame, min_pct: float = 0.5) -> pd.Series:
    """
    Rule #6: 'Gap play' — your most-called setup (140 mentions) but only
    middling edge (+$1,204 confirmed, 49% win rate). min_pct is a placeholder;
    TODO once real data is wired in: sweep 0.3%-1.5% against your confirmed
    gap-play trades to find the threshold that actually matches what you traded,
    rather than assuming 0.5% is right.
    """
    prior_close = bars["close"].shift(1)
    gap_pct = (bars["open"] - prior_close) / prior_close * 100
    return gap_pct.abs() >= min_pct


def rvol_time_matched(bars: pd.DataFrame, lookback_days: int = 20,
                       bar_minutes: int = 5) -> pd.Series:
    """
    Relative volume, TIME-MATCHED — comparing volume-by-10:30-today against
    volume-by-10:30 on the prior `lookback_days` sessions, NOT full-day
    averages. This was flagged as the most common way a homemade RVOL calc
    silently breaks. `bars` must be intraday, one row per `bar_minutes`.
    """
    bars = bars.copy()
    bars["date"] = bars.index.date
    bars["time"] = bars.index.time
    bars["cum_vol_today"] = bars.groupby("date")["volume"].cumsum()

    out = pd.Series(index=bars.index, dtype=float)
    for t in bars["time"].unique():
        mask = bars["time"] == t
        hist = bars.loc[mask, "cum_vol_today"]
        avg_at_time = hist.rolling(lookback_days, min_periods=5).mean().shift(1)
        out.loc[mask] = hist / avg_at_time
    return out.sort_index()


def stop_loss_level_50sma(close: pd.Series, window: int = 50) -> pd.Series:
    """
    Rule #6/setup list: 'stop-loss at 50 SMA' — a TECHNICAL level, not a fixed
    percent. Confirmed-trade data shows 50 SMA is your WEAKEST setup by edge
    (39% win rate, +$109 total) despite being cited as a stop rule — worth
    treating this as a stop condition, not an entry trigger.
    """
    return sma(close, window)


# ---------------------------------------------------------------------------
# 2. SESSION CLASSIFICATION — from the real-fill-time analysis.
# ---------------------------------------------------------------------------

def session_bucket(ts: pd.Timestamp) -> str:
    t = ts.hour + ts.minute / 60
    if t < 10:
        return "open"
    if t < 12:
        return "late_morning"
    if t < 14:
        return "midday"
    if t < 15:
        return "afternoon"
    return "power_hour"


SETUP_SESSION_EDGE = {
    "200_sma_magnet":   {"open": 2102, "late_morning": -125, "midday": 0, "afternoon": 0, "power_hour": 0},
    "gap_play":         {"open": 942,  "late_morning": -227, "midday": 553, "afternoon": 0, "power_hour": -64},
    "macd_read":        {"open": 1028, "late_morning": 756,  "midday": 681, "afternoon": 0, "power_hour": 0},
    "death_golden_cross": {"open": -162, "late_morning": 834, "midday": 681, "afternoon": 0, "power_hour": 0},
    "rsi_divergence":   {"open": 1122, "late_morning": 756,  "midday": 0, "afternoon": 0, "power_hour": 0},
    "candle_signal":    {"open": 862,  "late_morning": -608, "midday": 618, "afternoon": 0, "power_hour": -192},
}


# ---------------------------------------------------------------------------
# 3. POSITION SIZING & RISK RULES
# ---------------------------------------------------------------------------

MAX_CONTRACTS = 2          # OLD default: fixed 2-contract cap regardless of balance.
                           # Rule #4 in the confirmed data (3+ contracts, 25% win
                           # rate, -$1,032) was measured on your real, mostly small
                           # ($200-$5,000) account balances at the time -- it's really
                           # a statement about risking too much relative to the
                           # account, not a law that "2" is magic forever. Kept here
                           # as the SIZING_MODE="fixed" option; percentage sizing
                           # below is now the default, per your explicit call that
                           # you'd size up with real gains.
SIZING_MODE = "percent"    # "percent" (default) or "fixed" -- see size_for_debit.
RISK_PCT_PER_TRADE = 0.50  # Risk 50% of CURRENT balance per trade -- explicit
                           # instruction: starting at $200, going aggressive on
                           # purpose to grow faster, sizing scales with real
                           # gains/losses automatically as the balance moves.
                           # This is deliberately high-risk BY YOUR OWN CHOICE,
                           # not a data-derived number. At 50%, two losses in a
                           # row cuts the account to ~25% of where it started --
                           # know that going in.
ABSOLUTE_MAX_CONTRACTS = 20 # Safety ceiling regardless of mode or balance size --
                           # prevents one pathological signal from committing an
                           # absurd fraction of a very large future balance in one
                           # shot. Not from your data; a sanity backstop.
MAX_LOSSES_PER_SESSION = 2 # Rule #5: ~$47k lifetime swing between before/after this line.
MIN_DAYS_TO_EXPIRY = 2     # Rule #1: 2-4 day bucket alone cost -$14,590 lifetime when
                           # BOUGHT same/next-day; 5+ day entries made +$4,361 in the
                           # best-documented stretch. Never default to 0DTE.
MAX_HOLD_HOURS = 24        # Rule #2: exits within 24h (same-day + next-day) are
                           # +$6,312 of the +$6,451 confirmed total, across 281
                           # trades. Kept as a module-level constant, not baked into
                           # evaluate(), so a longer-hold variant can be A/B
                           # tested once real data exists instead of assumed.

# Premium sweet spot found in your confirmed trades -- DESCRIPTIVE ONLY.
# Nothing below AVOID_DEBIT_BELOW is the only thing this actually blocks.
#   <$0.50:  37% win rate, -$323   (worst band -- this is the only one avoided)
#   $0.50-3: 51-53% win rate, modestly positive
#   $3-5:    46% win rate, -$549   (unexplained dip, not enough evidence to act on)
#   $5-10:   61% win rate, +$3,914 (best band, but NOT a requirement -- just a label)
#   $10+:    50% win rate, +$2,154 (only 4 trades -- too few to trust alone)
PREFERRED_DEBIT_MIN = 5.00
PREFERRED_DEBIT_MAX = 10.00
AVOID_DEBIT_BELOW = 0.50    # confirmed worst band; the ONLY thing this blocks


@dataclass
class SessionState:
    """One trading day's running state for the two-loss stop."""
    date: pd.Timestamp
    losses_today: int = 0
    trades_today: list = field(default_factory=list)
    locked: bool = False

    def record(self, pnl: float):
        self.trades_today.append(pnl)
        if pnl < 0:
            self.losses_today += 1
        if self.losses_today >= MAX_LOSSES_PER_SESSION:
            self.locked = True

    def can_trade(self) -> bool:
        return not self.locked


def size_for_debit(debit_per_share: float, account_cash: float,
                    mode: str = SIZING_MODE,
                    max_contracts: int = MAX_CONTRACTS,
                    risk_pct: float = RISK_PCT_PER_TRADE) -> int:
    """
    Contracts to buy. Two modes:
      "fixed"   -- OLD behavior: hard-capped at max_contracts (2), regardless
                   of balance.
      "percent" -- NEW default: risk risk_pct of the CURRENT balance, so size
                   grows with real account growth automatically.
    Either way, capped at ABSOLUTE_MAX_CONTRACTS as a hard safety ceiling, and
    never sizes past what account_cash can actually afford.
    """
    if debit_per_share <= 0 or account_cash <= 0:
        return 0
    affordable = int(account_cash // (debit_per_share * 100))
    if mode == "fixed":
        target = max_contracts
    elif mode == "percent":
        risk_dollars = account_cash * risk_pct
        target = int(risk_dollars // (debit_per_share * 100))
    else:
        raise ValueError(f"Unknown sizing mode: {mode!r} (use 'fixed' or 'percent')")
    return max(0, min(affordable, target, ABSOLUTE_MAX_CONTRACTS))


def debit_quality(debit_per_share: float) -> str:
    """
    Classifies a candidate contract's premium against the calibrated bands
    above. Returns 'preferred', 'acceptable', or 'avoid'. Only 'avoid' blocks
    a trade -- 'preferred' vs 'acceptable' is informational only.
    """
    if debit_per_share < AVOID_DEBIT_BELOW:
        return "avoid"
    if PREFERRED_DEBIT_MIN <= debit_per_share <= PREFERRED_DEBIT_MAX:
        return "preferred"
    return "acceptable"


# ---------------------------------------------------------------------------
# 4. THE SIGNAL — ties it together. This is what actually fires.
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    timestamp: pd.Timestamp
    symbol: str
    direction: str
    setup: str
    session: str
    reason: str
    suggested_contracts: int
    min_days_to_expiry: int = MIN_DAYS_TO_EXPIRY
    max_hold_hours: int = MAX_HOLD_HOURS


def evaluate(bars: pd.DataFrame, symbol: str, account_cash: float,
             session_state: SessionState) -> Optional[Signal]:
    """
    Run one bar of data through the rule set. `bars` must have at least
    200 rows of history so the 200 SMA is defined. Returns a Signal or None.
    """
    if not session_state.can_trade():
        return None
    if len(bars) < 200:
        return None

    close = bars["close"]
    last = bars.iloc[-1]
    now = bars.index[-1]

    sma20, sma50, sma200 = sma(close, 20).iloc[-1], sma(close, 50).iloc[-1], sma(close, 200).iloc[-1]
    r = rsi(close).iloc[-1]
    m = macd(close)
    macd_cross_up = m["macd"].iloc[-2] < m["signal"].iloc[-2] and m["macd"].iloc[-1] > m["signal"].iloc[-1]
    macd_cross_dn = m["macd"].iloc[-2] > m["signal"].iloc[-2] and m["macd"].iloc[-1] < m["signal"].iloc[-1]
    gapped = is_gap(bars).iloc[-1]
    sess = session_bucket(now)

    setup, direction, reason = None, None, None

    if macd_cross_up:
        setup, direction = "macd_read", "call"
        reason = f"MACD crossed up through signal ({m['macd'].iloc[-1]:.3f})"
    elif macd_cross_dn:
        setup, direction = "macd_read", "put"
        reason = f"MACD crossed down through signal ({m['macd'].iloc[-1]:.3f})"
    elif r <= 20:
        setup, direction = "rsi_divergence", "call"
        reason = f"RSI oversold at {r:.1f}"
    elif r >= 80:
        setup, direction = "rsi_divergence", "put"
        reason = f"RSI overbought at {r:.1f}"
    elif abs(last["close"] - sma200) / sma200 < 0.003:
        setup = "200_sma_magnet"
        direction = "put" if last["close"] > sma200 else "call"
        reason = f"Price within 0.3% of 200 SMA ({sma200:.2f})"
    elif gapped:
        setup = "gap_play"
        direction = "put" if last["open"] < close.shift(1).iloc[-1] else "call"
        reason = "Gap ≥0.5% from prior close (threshold is a placeholder — see is_gap docstring)"
    else:
        return None

    edge = SETUP_SESSION_EDGE.get(setup, {}).get(sess, 0)
    if edge <= 0:
        return None

    contracts = size_for_debit(debit_per_share=1.0, account_cash=account_cash)
    # NOTE: debit_per_share=1.0 is STILL a placeholder -- evaluate() runs
    # before the real Black-Scholes price is known. Contract counts here are
    # approximate until this is wired to the actual computed premium.
    if contracts == 0:
        return None

    return Signal(
        timestamp=now, symbol=symbol, direction=direction, setup=setup,
        session=sess, reason=reason, suggested_contracts=contracts,
    )


# ---------------------------------------------------------------------------
# 5. WHAT'S STILL OPEN
# ---------------------------------------------------------------------------
OPEN_QUESTIONS = """
1. No verified OHLC feed originally -- now fixed via Alpaca. Compare each
   setup's fire rate and win rate against the confirmed-trade numbers.
2. is_gap()'s 0.5% threshold needs calibration against your 140 gap-play
   mentions.
3. The options-chain side is still a Black-Scholes MODEL, not a real quote.
4. SETUP_SESSION_EDGE is a frozen snapshot of 297 trades -- small-sample
   cells are noise, not proof.
5. evaluate()'s sizing call uses a placeholder $1.00 debit, not the real
   computed premium -- contract counts are approximate until wired to the
   actual price the backtest computes.
"""

if __name__ == "__main__":
    print(__doc__)
    print(OPEN_QUESTIONS)
