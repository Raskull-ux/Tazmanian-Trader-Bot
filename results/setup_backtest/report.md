# Setup Backtest v3 — 2026-01-03 to 2026-10-04

Universe scanned: 14 names, 5-min SIP bars. Extended-hours indicators: True.

Stock-move test only: tells whether the setup picks moves in the right direction and reaches its targets. Option P&L comes next.

## All signals

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 75 | 51% | +0.02% | 1.27 | 23% | 1% | 55% | 0.19% |

## HOD

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 70 | 50% | +0.02% | 1.14 | 21% | 1% | 57% | 0.20% |

## SMA200

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 5 | 60% | +0.04% | 0.69 | 40% | 0% | 20% | 0.15% |

## By time of entry

| Window | Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|---|
| 09:45-10:30 | 0 | | | | | | | |
| 10:30-12:00 | 17 | 29% | -0.02% | -0.54 | 24% | 0% | 71% | 0.21% |
| 12:00-14:00 | 37 | 49% | +0.03% | 1.48 | 24% | 0% | 62% | 0.20% |
| 14:00-15:30 | 21 | 71% | +0.04% | 1.26 | 19% | 5% | 29% | 0.18% |

## How trades ended

- stop_50sma: 38 (51%)
- eod: 24 (32%)
- breakeven_stop: 9 (12%)
- stop_setup_high: 3 (4%)
- t2: 1 (1%)

## Which level was T1

- low_of_day: 23
- gap_fill_yday_close: 17
- hourly_sma50: 9
- hourly_sma100: 8
- yday_low: 8
- daily_sma8: 4
- hourly_sma200: 4
- none below: 2

## Most frequent names

| Ticker | Signals | Avg |
|---|---|---|
| SPY | 43 | +0.02% |
| QQQ | 22 | +0.04% |
| KRE | 7 | -0.01% |
| NVDA | 2 | +0.16% |
| AAPL | 1 | -0.34% |

## Option estimate — ATM put, by expiry and profit target

Each cell: % of signals that hit the target / average option return per trade (after 4% round-trip cost) / t-stat. Misses exit at the stock stop or 3:55 pm.

| Expiry | +30% target | +50% target | +100% target | Avg best option gain |
|---|---|---|---|---|
| 0 days | 24% / -19.7% / t -5.33 | 13% / -24.6% / t -6.20 | 3% / -30.4% / t -8.26 | +16% |
| 1 day | 13% / -5.9% / t -3.31 | 1% / -7.9% / t -5.07 | 0% / -8.3% / t -5.85 | +10% |
| 3 days | 3% / -4.8% / t -4.55 | 0% / -5.2% / t -5.54 | 0% / -5.2% / t -5.54 | +7% |
| 7 days | 0% / -4.2% / t -6.48 | 0% / -4.2% / t -6.48 | 0% / -4.2% / t -6.48 | +5% |
| 14 days | 0% / -3.9% / t -8.25 | 0% / -3.9% / t -8.25 | 0% / -3.9% / t -8.25 | +4% |

Estimate only: Black-Scholes with a realized-vol IV proxy, no real fills. Real option P&L (Databento) confirms whatever survives.

Pass bar before trusting any setup: t-stat ≥ 3 on enough signals (roughly 400+), then option P&L must confirm.

## Tuning grid (walk-forward) — metric: opt1_50 (1-day put, +50% target)

Settings are picked on signals BEFORE 2026-07-04 (train) and judged on signals AFTER it (test). Only the test column counts; the train column is where tuning can fool itself.

| Box bars | HOD zone | RSI div pts | Box break | Train n | Train avg | Train t | Test n | Test avg | Test t |
|---|---|---|---|---|---|---|---|---|---|
| 6 | 0.5% | 3 | False | 132 | -5.6% | -3.09 | 83 | -8.2% | -4.89 |
| 12 | 0.3% | 3 | True | 46 | -6.8% | -3.04 | 29 | -9.5% | -5.11 |
| 6 | 0.5% | 0 | False | 150 | -7.2% | -4.39 | 94 | -8.4% | -5.53 |
| 6 | 0.5% | 3 | True | 90 | -7.9% | -4.16 | 55 | -10.3% | -5.94 |
| 9 | 0.3% | 3 | True | 49 | -8.1% | -3.53 | 31 | -10.1% | -5.59 |
| 6 | 0.3% | 3 | False | 81 | -8.1% | -4.37 | 56 | -5.9% | -2.73 |
| 12 | 0.5% | 3 | True | 74 | -8.3% | -4.29 | 44 | -10.7% | -7.03 |
| 9 | 0.5% | 3 | False | 120 | -8.3% | -4.95 | 74 | -7.9% | -4.40 |

Best on train: box 6 bars, zone 0.5%, RSI div 3, box break False -> TEST -8.2% per trade on 83 signals (t -4.89).
