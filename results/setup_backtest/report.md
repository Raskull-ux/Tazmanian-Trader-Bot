# Setup Backtest v2 — 2026-01-03 to 2026-10-04

Universe scanned: 2 names, 5-min SIP bars. Extended-hours indicators: True.

Stock-move test only: tells whether the setup picks moves in the right direction and reaches its targets. Option P&L comes next.

## All signals

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 65 | 54% | +0.03% | 1.49 | 22% | 0% | 54% | 0.19% |

## HOD

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 62 | 53% | +0.03% | 1.41 | 21% | 0% | 55% | 0.19% |

## SMA200

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 3 | 67% | +0.04% | 0.45 | 33% | 0% | 33% | 0.16% |

## By time of entry

| Window | Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|---|
| 09:45-10:30 | 0 | | | | | | | |
| 10:30-12:00 | 16 | 25% | -0.04% | -0.85 | 19% | 0% | 75% | 0.20% |
| 12:00-14:00 | 33 | 55% | +0.04% | 1.86 | 27% | 0% | 58% | 0.20% |
| 14:00-15:30 | 16 | 81% | +0.05% | 2.44 | 12% | 0% | 25% | 0.15% |

## How trades ended

- stop_50sma: 33 (51%)
- eod: 22 (34%)
- breakeven_stop: 8 (12%)
- stop_setup_high: 2 (3%)

## Which level was T1

- low_of_day: 21
- gap_fill_yday_close: 12
- yday_low: 8
- hourly_sma50: 7
- hourly_sma100: 7
- daily_sma8: 4
- hourly_sma200: 4
- none below: 2

## Most frequent names

| Ticker | Signals | Avg |
|---|---|---|
| SPY | 43 | +0.02% |
| QQQ | 22 | +0.04% |

Pass bar before trusting any setup: t-stat ≥ 3 on enough signals (roughly 400+), then option P&L must confirm.
