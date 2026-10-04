# Setup Backtest v1 — 2026-01-03 to 2026-10-04

Universe scanned: 2 names, 5-min SIP bars. Extended-hours indicators: True.

Stock-move test only: tells whether the setup picks moves in the right direction and reaches its targets. Option P&L comes next.

## All signals

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 97 | 55% | +0.02% | 1.33 | 20% | 4% | 63% | 0.18% |

## HOD

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 89 | 55% | +0.02% | 1.59 | 19% | 4% | 63% | 0.18% |

## SMA200

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 8 | 50% | -0.03% | -0.58 | 25% | 0% | 62% | 0.15% |

## By time of entry

| Window | Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|---|
| 09:45-10:30 | 2 | 100% | +0.25% | 1.70 | 50% | 0% | 50% | 0.46% |
| 10:30-12:00 | 22 | 32% | -0.04% | -1.12 | 18% | 5% | 77% | 0.19% |
| 12:00-14:00 | 47 | 60% | +0.04% | 2.09 | 23% | 4% | 64% | 0.18% |
| 14:00-15:30 | 26 | 62% | +0.02% | 0.61 | 12% | 4% | 50% | 0.13% |

## How trades ended

- stop_50sma: 51 (53%)
- eod: 22 (23%)
- breakeven_stop: 10 (10%)
- stop_setup_high: 10 (10%)
- t2: 4 (4%)

## Which level was T1

- low_of_day: 29
- gap_fill_yday_close: 16
- hourly_sma50: 15
- yday_low: 13
- hourly_sma100: 11
- hourly_sma200: 7
- daily_sma8: 3
- none below: 3

## Most frequent names

| Ticker | Signals | Avg |
|---|---|---|
| SPY | 60 | +0.02% |
| QQQ | 37 | +0.02% |

Pass bar before trusting any setup: t-stat ≥ 3 on enough signals (roughly 400+), then option P&L must confirm.
