# Setup Backtest v4 — 2026-01-03 to 2026-10-04

Universe scanned: 10 names, 5-min SIP bars. Extended-hours indicators: True.

Stock-move test only: tells whether the setup picks moves in the right direction and reaches its targets. Option P&L comes next.

## All signals

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 1 | 0% | -0.12% | nan | 0% | 0% | 100% | 0.08% |

## HOD

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 0 | | | | | | | |

## SMA200

| Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|
| 1 | 0% | -0.12% | nan | 0% | 0% | 100% | 0.08% |

## By time of entry

| Window | Signals | Win | Avg stock move (put direction) | t-stat | Hit T1 | Hit T2 | Stopped | Avg best move |
|---|---|---|---|---|---|---|---|---|
| 09:45-10:30 | 0 | | | | | | | |
| 10:30-12:00 | 1 | 0% | -0.12% | nan | 0% | 0% | 100% | 0.08% |
| 12:00-14:00 | 0 | | | | | | | |
| 14:00-15:30 | 0 | | | | | | | |

## How trades ended

- stop_50sma: 1 (100%)

## Which level was T1

- hourly_sma50: 1

## Most frequent names

| Ticker | Signals | Avg |
|---|---|---|
| SPY | 1 | -0.12% |

## Option estimate — ATM put, by expiry and profit target

Each cell: % of signals that hit the target / average option return per trade (after 4% round-trip cost) / t-stat. Misses exit at the stock stop or 3:55 pm.

| Expiry | +30% target | +50% target | +100% target | Avg best option gain |
|---|---|---|---|---|
| 0 days | 0% / -29.0% / t nan | 0% / -29.0% / t nan | 0% / -29.0% / t nan | +3% |
| 1 day | 0% / -17.9% / t nan | 0% / -17.9% / t nan | 0% / -17.9% / t nan | +2% |
| 3 days | 0% / -12.5% / t nan | 0% / -12.5% / t nan | 0% / -12.5% / t nan | +2% |
| 7 days | 0% / -9.5% / t nan | 0% / -9.5% / t nan | 0% / -9.5% / t nan | +1% |
| 14 days | 0% / -7.7% / t nan | 0% / -7.7% / t nan | 0% / -7.7% / t nan | +1% |

Estimate only: Black-Scholes with a realized-vol IV proxy, no real fills. Real option P&L (Databento) confirms whatever survives.

Pass bar before trusting any setup: t-stat ≥ 3 on enough signals (roughly 400+), then option P&L must confirm.

## Tuning grid (walk-forward) — metric: opt1_50 (1-day put, +50% target)

Settings are picked on signals BEFORE 2026-07-04 (train) and judged on signals AFTER it (test). Only the test column counts; the train column is where tuning can fool itself.

| Box bars | HOD zone (ATR) | RSI div pts | Box break | Min room (ATR) | Train n | Train avg | Train t | Test n | Test avg | Test t |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | 2 | 3 | False | 0 | 43 | -4.3% | -1.12 | 18 | -5.5% | -1.11 |
| 6 | 2 | 0 | False | 0 | 48 | -5.4% | -1.56 | 19 | -5.9% | -1.24 |
| 6 | 2 | 3 | False | 2 | 26 | -6.1% | -1.24 | 9 | +3.2% | 0.35 |
| 6 | 2 | 0 | False | 2 | 28 | -6.8% | -1.47 | 10 | +1.7% | 0.20 |
| 12 | 2 | 0 | False | 0 | 20 | -9.1% | -1.92 | 8 | +2.6% | 0.27 |
| 6 | 2 | 3 | True | 0 | 24 | -9.5% | -1.98 | 7 | -4.2% | -0.47 |
| 6 | 2 | 0 | True | 0 | 29 | -10.5% | -2.63 | 7 | -4.2% | -0.47 |

Best on train: box 6 bars, zone 2 ATR, room 0 ATR, RSI div 3, box break False -> TEST -5.5% per trade on 18 signals (t -1.11).
