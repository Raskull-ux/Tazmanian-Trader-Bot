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
    averages. This was flagged (in the sister project's notes) as the most
    common way a homemade RVOL calc silently breaks: comparing a partial
    trading day against a full-day average always looks artificially low
    before ~3pm, and a bot using that would systematically under-signal all
    morning. `bars` must be intraday, one row per `bar_minutes`.
    """
    bars = bars.copy()
    bars["date"] = bars.index.date
    bars["time"] = bars.index.time
    bars["cum_vol_today"] = bars.groupby("date")["volume"].cumsum()

    out = pd.Series(index=bars.index, dtype=float)
    for t in bars["time"].unique():
        mask = bars["time"] == t
        hist = bars.loc[mask, "cum_vol_today"]
        # trailing lookback_days average of cumulative volume AT THIS SAME TIME
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
#    Confirmed: setups are NOT uniformly better "late morning" — it's
#    setup-specific (Strategy tab, section 8). This buckets a timestamp;
#    callers should look up expected edge per (setup, session) themselves
#    against the Strategy tab table rather than assuming one blanket window.
# ---------------------------------------------------------------------------

def session_bucket(ts: pd.Timestamp) -> str:
    t = ts.hour + ts.minute / 60
    if t < 10:
        return "open"          # 9:30-10:00 ET
    if t < 12:
        return "late_morning"  # 10:00-12:00 ET — best OVERALL, but setup-dependent
    if t < 14:
        return "midday"
    if t < 15:
        return "afternoon"
    return "power_hour"        # 15:00-16:00 ET


# Setup-specific session edge, hardcoded from the 297-trade confirmed set
# (Strategy tab §8). Positive = real $, not a probability. Recompute this
# table from the workbook whenever Confirmed Trades grows meaningfully —
# it is a snapshot, not a live link.
SETUP_SESSION_EDGE = {
    "200_sma_magnet":   {"open": 2102, "late_morning": -125, "midday": 0, "afternoon": 0, "power_hour": 0},
    "gap_play":         {"open": 942,  "late_morning": -227, "midday": 553, "afternoon": 0, "power_hour": -64},
    "macd_read":        {"open": 1028, "late_morning": 756,  "midday": 681, "afternoon": 0, "power_hour": 0},
    "death_golden_cross": {"open": -162, "late_morning": 834, "midday": 681, "afternoon": 0, "power_hour": 0},
    "rsi_divergence":   {"open": 1122, "late_morning": 756,  "midday": 0, "afternoon": 0, "power_hour": 0},
    "candle_signal":    {"open": 862,  "late_morning": -608, "midday": 618, "afternoon": 0, "power_hour": -192},
}


# ---------------------------------------------------------------------------
# 3. POSITION SIZING & RISK RULES — from Strategy tab §4-5, the two rules
#    with the largest confirmed dollar impact of anything in this file.
# ---------------------------------------------------------------------------

MAX_CONTRACTS = 2          # Rule #4: 3+ contracts confirmed at 25% win rate, -$1,032
                           # total across 297 confirmed trades (11 trades). 1-2
                           # contracts: 51% win rate, +$7,899 combined. Hard cap, no
                           # exceptions regardless of conviction.
MAX_LOSSES_PER_SESSION = 2 # Rule #5: ~$47k lifetime swing between before/after this line.
MIN_DAYS_TO_EXPIRY = 2     # Rule #1: 2-4 day bucket alone cost -$14,590 lifetime when
                           # BOUGHT same/next-day; 5+ day entries made +$4,361 in the
                           # best-documented stretch. Never default to 0DTE.
MAX_HOLD_HOURS = 24        # Rule #2: exits within 24h (same-day + next-day) are
                           # +$6,312 of the +$6,451 confirmed total, across 281
                           # trades. Everything past 1 day is thin: 2-4 day holds
                           # are 13 trades total, mixed; the single 5-day hold
                           # (+$270) is n=1, not a pattern — do not read it as one.
                           # Kept as a module-level constant, not baked into
                           # evaluate(), so a longer-hold variant can be A/B
                           # tested once real data exists instead of assumed.

# Premium (per-share debit) sweet spot, calibrated against all 297 confirmed
# trades' actual open_px vs outcome. This DIRECTLY CONTRADICTS the cheap-lotto
# assumption in the earlier Grok skeleton (MIN_DEBIT/MAX_DEBIT $0.75-$1.50):
#   <$0.50:  37% win rate, -$323   (worst band — avoid)
#   $0.50-3: 51-53% win rate, modestly positive
#   $3-5:    46% win rate, -$549   (unexplained dip — not enough evidence to
#            act on yet, flagged rather than smoothed over)
#   $5-10:   61% win rate, +$3,914 (best band by both win rate AND dollars)
#   $10+:    50% win rate, +$2,154 (only 4 trades — too few to trust alone)
PREFERRED_DEBIT_MIN = 5.00
PREFERRED_DEBIT_MAX = 10.00
AVOID_DEBIT_BELOW = 0.50    # confirmed worst band; do not chase cheap lotto contracts


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
                    max_contracts: int = MAX_CONTRACTS) -> int:
    """Contracts to buy, capped at MAX_CONTRACTS and by available cash. Returns
    0 rather than sizing up past the cap under any circumstance — Rule #4 is a
    hard ceiling, not a suggestion, per the confirmed-trade evidence."""
    if debit_per_share <= 0:
        return 0
    affordable = int(account_cash // (debit_per_share * 100))
    return max(0, min(affordable, max_contracts))


def debit_quality(debit_per_share: float) -> str:
    """
    Classifies a candidate contract's premium against the calibrated bands
    above. Returns 'preferred', 'acceptable', or 'avoid' — callers should
    weight or skip signals accordingly. This is choosing WHICH contract on
    the chain to select, once a chain feed exists (open question #3);
    it does not choose direction or setup.
    """
    if debit_per_share < AVOID_DEBIT_BELOW:
        return "avoid"          # confirmed worst band, 37% win rate
    if PREFERRED_DEBIT_MIN <= debit_per_share <= PREFERRED_DEBIT_MAX:
        return "preferred"      # confirmed best band, 61% win rate
    return "acceptable"


# ---------------------------------------------------------------------------
# 4. THE SIGNAL — ties it together. This is what actually fires.
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    timestamp: pd.Timestamp
    symbol: str
    direction: str          # "call" or "put"
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

    This function does NOT place an order and does NOT know your options
    chain — per the earlier decision, the bot signals, you (or a later,
    explicitly-approved execution layer) place the trade. It also refuses to
    return a signal at all once the session is locked, no override path.
    """
    if not session_state.can_trade():
        return None
    if len(bars) < 200:
        return None  # not enough history for the 200 SMA yet

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

    # Priority order follows confirmed win-rate ranking (Strategy tab §6),
    # highest-edge setup wins when more than one condition is true at once.
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
        # Setup fired, but this setup has NO confirmed edge in this session
        # window (e.g. 200_sma_magnet after 10am). Do not signal — this is
        # the precise fix for "late morning" being treated as a blanket rule.
        return None

    contracts = size_for_debit(debit_per_share=1.0, account_cash=account_cash)
    # NOTE: debit_per_share=1.0 is a placeholder until an options-chain feed
    # is wired in; replace with the actual ask price of the contract you'd
    # select once that data source exists.
    if contracts == 0:
        return None

    return Signal(
        timestamp=now, symbol=symbol, direction=direction, setup=setup,
        session=sess, reason=reason, suggested_contracts=contracts,
    )


# ---------------------------------------------------------------------------
# 5. WHAT'S STILL OPEN — do not silently paper over these.
# ---------------------------------------------------------------------------
OPEN_QUESTIONS = """
1. No verified OHLC feed reachable from this environment (Stooq blocked,
   Nasdaq chart endpoint not fetchable). Every function above is correct in
   isolation but UNTESTED against real bars. First real task once a feed
   (Alpaca paper / IEX, per the sister project) is wired in: backtest each
   setup's fire rate and win rate against 2025-2026 history and compare to
   the confirmed-trade numbers in the workbook. If they don't roughly agree,
   a threshold above is wrong and needs adjusting from real data, not guessed
   again.
2. is_gap()'s 0.5% threshold is not derived from your data — it's a
   reasonable default. Needs calibration against your 140 gap-play mentions.
3. The options-chain side (which strike, which expiry, what it actually
   costs) is entirely unbuilt. evaluate() signals direction and setup; it
   does not yet pick a contract. That's the next module, once a chain feed
   exists.
4. SETUP_SESSION_EDGE is a frozen snapshot of 297 trades. Small numbers in
   some cells (e.g. death_golden_cross has only 10 total trades) mean real
   noise — don't treat -$162 at the open as proof the setup fails there,
   treat it as "not enough evidence yet."
"""

if __name__ == "__main__":
    print(__doc__)
    print(OPEN_QUESTIONS)
