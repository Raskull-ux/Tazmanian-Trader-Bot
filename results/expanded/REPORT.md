# Expanded universe test (Taz's 75 + sector peers + liquid names)

Stocks with data: 851 | signal rows: 1,357,056

Drop first = price falls 2 ATR before rising 2 ATR within 20 days. Compare every row to the baseline.

| Setup | Signals | Drop first | 2016-21 | 2022-26 | vs baseline | 10d median |
|---|---|---|---|---|---|---|
| 10/20 cross | 45,414 | 45.8% | 43.7% | 47.6% | +0.7 pts (z +3.1) | +0.28% |
| 10/200 cross | 9,502 | 43.9% | 43.7% | 44.0% | -1.1 pts (z -2.2) | +0.43% |
| 20/200 cross | 6,927 | 44.4% | 42.1% | 46.4% | -0.6 pts (z -1.0) | +0.58% |
| 8/20 cross | 47,940 | 46.2% | 44.4% | 47.8% | +1.2 pts (z +5.1) | +0.32% |
| 8/200 cross | 10,485 | 44.3% | 44.5% | 44.2% | -0.7 pts (z -1.4) | +0.43% |
| MACD cross down at top | 17,827 | 47.5% | 45.5% | 49.9% | +2.5 pts (z +6.6) | +0.40% |
| baseline | 336,755 | 45.0% | 43.0% | 46.9% | +0.0 pts (z +0.0) | +0.48% |
| grade A/A- (mechanical) | 218,772 | 44.9% | 43.0% | 46.8% | -0.1 pts (z -1.2) | +0.51% |
| grade B (mechanical) | 387,127 | 44.4% | 43.2% | 45.5% | -0.6 pts (z -7.9) | +0.54% |
| long staircase at top, RSI<50 | 1,145 | 49.3% | 48.8% | 49.7% | +4.2 pts (z +2.9) | -0.02% |
| pocket | 32,039 | 44.9% | 42.6% | 46.7% | -0.2 pts (z -0.6) | +0.35% |
| pocket+sideways+8EMA tag | 11,015 | 45.0% | 43.2% | 46.5% | -0.1 pts (z -0.1) | +0.34% |
| pre-cross (first day) | 76,149 | 46.3% | 44.0% | 48.5% | +1.3 pts (z +7.1) | +0.43% |
| staircase, green higher high under top, RSI<50 | 6,031 | 48.8% | 48.6% | 49.1% | +3.8 pts (z +5.9) | +0.06% |

## Your 75 vs the peers

| Setup | Your 75: drop first (n) | Peers: drop first (n) |
|---|---|---|
| 10/20 cross | 45.0% (3,979) | 45.8% (41,435) |
| 10/200 cross | 43.7% (817) | 43.9% (8,685) |
| 20/200 cross | 40.8% (579) | 44.8% (6,348) |
| 8/20 cross | 46.5% (4,208) | 46.2% (43,732) |
| 8/200 cross | 44.8% (887) | 44.3% (9,598) |
| MACD cross down at top | 47.6% (1,516) | 47.5% (16,311) |
| baseline | 44.1% (29,920) | 45.1% (306,835) |
| grade A/A- (mechanical) | 44.5% (17,921) | 45.0% (200,851) |
| grade B (mechanical) | 44.3% (34,385) | 44.4% (352,742) |
| long staircase at top, RSI<50 | 53.3% (105) | 48.8% (1,040) |
| pocket | 45.3% (2,514) | 44.8% (29,525) |
| pocket+sideways+8EMA tag | 45.6% (853) | 44.9% (10,162) |
| pre-cross (first day) | 46.5% (6,677) | 46.3% (69,472) |
| staircase, green higher high under top, RSI<50 | 53.1% (531) | 48.4% (5,500) |

## Best setup by sector (100+ signals, vs that sector's own baseline)

| Setup | Sector ETF | Signals | Drop first | Sector baseline | Edge |
|---|---|---|---|---|---|
| long staircase at top, RSI<50 | XLF | 127 | 55.9% | 45.1% | +10.8 pts |
| 8/200 cross | XLRE | 131 | 54.2% | 44.3% | +9.9 pts |
| pocket+sideways+8EMA tag | XLP | 240 | 56.2% | 46.7% | +9.6 pts |
| long staircase at top, RSI<50 | XLY | 137 | 54.7% | 45.2% | +9.5 pts |
| MACD cross down at top | XLU | 344 | 51.7% | 43.1% | +8.6 pts |
| MACD cross down at top | XLRE | 303 | 51.5% | 44.3% | +7.2 pts |
| staircase, green higher high under top, RSI<50 | XLE | 377 | 54.1% | 47.1% | +7.0 pts |
| pocket | XLP | 710 | 53.4% | 46.7% | +6.7 pts |
| staircase, green higher high under top, RSI<50 | SPY | 1,338 | 51.7% | 45.6% | +6.2 pts |
| long staircase at top, RSI<50 | SPY | 194 | 51.5% | 45.6% | +6.0 pts |
| staircase, green higher high under top, RSI<50 | XLI | 344 | 48.5% | 43.9% | +4.6 pts |
| staircase, green higher high under top, RSI<50 | XLF | 832 | 49.4% | 45.1% | +4.3 pts |
| MACD cross down at top | XLF | 2,572 | 49.2% | 45.1% | +4.1 pts |
| pocket+sideways+8EMA tag | XLF | 1,580 | 49.1% | 45.1% | +4.0 pts |
| staircase, green higher high under top, RSI<50 | XLC | 241 | 49.4% | 45.4% | +4.0 pts |
