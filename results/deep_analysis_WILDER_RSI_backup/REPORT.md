# Deep analysis: your calls, your trades, your patterns

# PART 1: Your 292 top calls, dissected

Calls measured: **290** (controls: 848 random entries, same names, same minute of day, nearby days).

## 1. How the calls played out (stock moves, short side)
|                        |   n | fell 1 ATR before rising 1 ATR (5 days)   | avg move by close of day 3   | avg move by day 5   | median rise AGAINST you before the 10-day low   | median biggest drop within 5 days   |   10-day low came on day (median) |
|:-----------------------|----:|:------------------------------------------|:-----------------------------|:--------------------|:------------------------------------------------|:------------------------------------|----------------------------------:|
| Your calls             | 290 | 49.7%                                     | +0.10%                       | +0.33%              | 1.29%                                           | 2.37%                               |                                 6 |
| Random control entries | 848 | 48.1%                                     | -0.74%                       | -1.03%              | 1.07%                                           | 2.64%                               |                                 4 |

**Being early, measured.** After your call the stock went on to make a higher high within 3 days in 97% of calls; it pushed at least 0.5 ATR higher in 60% and at least 1 ATR higher in 36%. Controls: 98% / 67% / 40%.

## 2. Fixing early: every entry x every exit (average result in R, 1R = entry to technical stop)
Stop = highest high of the hour before entry, a hair above. Targets = real support levels under price (prior day/week lows, daily 10/20/50/200 SMAs, unfilled gaps, daily + hourly swing lows, 5-day volume POC / value area). Calls where the entry never triggered count as **0R (no trade)** in 'per call'.

| entry               | triggered   |   sold higher than call price by (median %) |   median hours after call |   median stop size (ATR) | level1         | level2         | level3         | half_L1_rest_L3   | day_close      | hourly_close_above_20   | daily_close_above_10   | hold_3_days    | hold_5_days    |
|:--------------------|:------------|--------------------------------------------:|--------------------------:|-------------------------:|:---------------|:---------------|:---------------|:------------------|:---------------|:------------------------|:-----------------------|:---------------|:---------------|
| at_call             | 100%        |                                        0    |                       0   |                     0.25 | +0.03 (t 0.2)  | +0.12 (t 1.0)  | -0.01 (t -0.5) | +0.01 (t 0.0)     | +0.01 (t 0.3)  | -0.23 (t -1.8)          | -0.30 (t -1.5)         | -0.19 (t -1.4) | -0.21 (t -1.5) |
| reject_5m200        | 95%         |                                       -0.11 |                       5.8 |                     0.29 | +0.10 (t 0.5)  | +0.11 (t 1.0)  | +0.01 (t 0.3)  | +0.09 (t 0.6)     | -0.03 (t -0.4) | -0.05 (t -0.6)          | -0.18 (t -1.1)         | -0.02 (t -0.3) | -0.08 (t -0.7) |
| hourly_20_retest    | 45%         |                                       -0.58 |                      21.2 |                     0.31 | +0.13 (t 0.7)  | +0.21 (t 1.0)  | +0.01 (t 0.5)  | +0.09 (t 0.7)     | +0.04 (t 0.2)  | +0.18 (t 0.6)           | -0.12 (t -0.2)         | +0.14 (t 0.5)  | -0.00 (t 0.2)  |
| hourly_20_50_cross  | 38%         |                                       -1.55 |                      26.5 |                     0.25 | -0.36 (t -1.6) | -0.20 (t -0.4) | -0.37 (t -1.2) | -0.34 (t -1.3)    | -0.10 (t 0.1)  | -0.43 (t -1.5)          | -0.75 (t -2.7)         | -0.41 (t -1.6) | -0.53 (t -2.1) |
| break_prior_day_low | 77%         |                                       -0.76 |                      20   |                     0.44 | -0.00 (t 0.2)  | -0.06 (t 0.1)  | -0.16 (t -0.8) | -0.09 (t -0.3)    | +0.01 (t 0.2)  | -0.14 (t -0.7)          | -0.24 (t -0.6)         | +0.01 (t 0.1)  | -0.21 (t -0.8) |
| m15_macd_cross      | 98%         |                                       -0.11 |                       4   |                     0.29 | +0.09 (t 0.5)  | +0.07 (t 0.4)  | +0.04 (t 0.0)  | +0.09 (t 0.2)     | +0.05 (t 1.0)  | +0.07 (t -0.0)          | -0.12 (t -0.3)         | +0.08 (t 0.1)  | +0.03 (t 0.0)  |
| failed_breakout     | 88%         |                                       -0.12 |                       0.5 |                     0.26 | +0.08 (t 0.6)  | +0.01 (t 0.1)  | -0.21 (t -2.0) | -0.02 (t -0.2)    | +0.05 (t 1.1)  | -0.29 (t -2.2)          | -0.21 (t -0.8)         | -0.17 (t -1.1) | -0.28 (t -1.2) |
| next_open           | 100%        |                                       -0.1  |                      23.6 |                     0.25 | -0.06 (t -1.0) | +0.05 (t 0.6)  | +0.17 (t 1.1)  | +0.00 (t -0.3)    | +0.09 (t 0.8)  | +0.04 (t 0.1)           | +0.03 (t -0.0)         | +0.17 (t 0.5)  | +0.08 (t 0.2)  |
| after_red_day       | 71%         |                                       -0.48 |                      24   |                     0.25 | +0.07 (t 0.0)  | +0.01 (t 0.1)  | +0.22 (t 1.1)  | +0.02 (t -0.1)    | +0.02 (t -0.1) | -0.08 (t -1.0)          | -0.29 (t -1.1)         | +0.21 (t 0.4)  | -0.17 (t -1.3) |

Same table on the RANDOM control entries (if a fix helps controls just as much, it is a general short-entry rule, not a fix for your timing):
| entry               | triggered   |   level1 |   level2 |   level3 |   half_L1_rest_L3 |   day_close |   hourly_close_above_20 |   daily_close_above_10 |   hold_3_days |   hold_5_days |
|:--------------------|:------------|---------:|---------:|---------:|------------------:|------------:|------------------------:|-----------------------:|--------------:|--------------:|
| at_call             | 100%        |    -0.08 |    -0.13 |    -0.18 |             -0.13 |        0.04 |                   -0.21 |                  -0.43 |         -0.2  |         -0.27 |
| reject_5m200        | 93%         |    -0.18 |    -0.15 |    -0.21 |             -0.2  |       -0.02 |                   -0.27 |                  -0.42 |         -0.24 |         -0.38 |
| hourly_20_retest    | 46%         |     0.11 |     0.21 |    -0.07 |              0.03 |        0.08 |                   -0.1  |                  -0.34 |         -0.01 |         -0.16 |
| hourly_20_50_cross  | 38%         |     0.09 |     0.06 |     0    |              0.02 |        0.01 |                    0.01 |                  -0.22 |          0.16 |         -0.11 |
| break_prior_day_low | 74%         |    -0.04 |    -0.01 |    -0.16 |             -0.11 |        0.07 |                   -0.14 |                  -0.43 |         -0.09 |         -0.26 |
| m15_macd_cross      | 98%         |    -0.05 |    -0.1  |    -0.21 |             -0.11 |        0.07 |                   -0.12 |                  -0.28 |         -0.15 |         -0.26 |
| failed_breakout     | 85%         |    -0.01 |    -0.08 |    -0.1  |             -0.06 |        0.02 |                   -0.15 |                  -0.36 |         -0.12 |         -0.19 |
| next_open           | 100%        |    -0.05 |    -0.03 |     0.01 |             -0.02 |        0.06 |                   -0.09 |                  -0.2  |         -0.18 |         -0.22 |
| after_red_day       | 73%         |    -0.06 |    -0.05 |    -0.07 |             -0.06 |        0.01 |                   -0.22 |                  -0.33 |         -0.25 |         -0.33 |

Stability check, calls only, first half vs second half (before / after July 2025):
| entry            | exit                  |   early avg R |   late avg R |   early n |   late n |   all t | both halves positive   |
|:-----------------|:----------------------|--------------:|-------------:|----------:|---------:|--------:|:-----------------------|
| next_open        | level3                |         0.301 |        0.085 |       109 |      162 |   1.142 | True                   |
| after_red_day    | level3                |         0.058 |        0.34  |        80 |      109 |   1.132 | True                   |
| failed_breakout  | day_close             |         0.09  |        0.028 |       105 |      149 |   1.114 | True                   |
| m15_macd_cross   | day_close             |         0.052 |        0.047 |       113 |      171 |   0.994 | True                   |
| reject_5m200     | level2                |        -0.023 |        0.203 |       103 |      161 |   0.992 | False                  |
| hourly_20_retest | level2                |         0.239 |        0.194 |        46 |       79 |   0.985 | True                   |
| at_call          | level2                |         0.167 |        0.083 |       109 |      168 |   0.953 | True                   |
| next_open        | day_close             |         0.07  |        0.104 |       118 |      172 |   0.841 | True                   |
| hourly_20_retest | level1                |         0.333 |        0.009 |        48 |       79 |   0.745 | True                   |
| hourly_20_retest | half_L1_rest_L3       |         0.311 |       -0.041 |        46 |       79 |   0.735 | False                  |
| hourly_20_retest | hourly_close_above_20 |         0.617 |       -0.093 |        51 |       80 |   0.588 | False                  |
| failed_breakout  | level1                |         0.208 |       -0.012 |        99 |      147 |   0.572 | False                  |
| reject_5m200     | half_L1_rest_L3       |         0.084 |        0.097 |       103 |      161 |   0.572 | True                   |
| next_open        | level2                |         0.163 |       -0.026 |       110 |      167 |   0.56  | False                  |
| reject_5m200     | level1                |         0.059 |        0.125 |       106 |      164 |   0.548 | True                   |
| hourly_20_retest | level3                |         0.094 |       -0.046 |        45 |       77 |   0.541 | False                  |
| next_open        | hold_3_days           |         0.37  |        0.028 |       118 |      172 |   0.516 | True                   |
| hourly_20_retest | hold_3_days           |         0.511 |       -0.102 |        51 |       80 |   0.509 | False                  |
| m15_macd_cross   | level1                |         0.073 |        0.102 |       109 |      170 |   0.499 | True                   |
| after_red_day    | hold_3_days           |         0.007 |        0.354 |        86 |      120 |   0.436 | True                   |

## 3. Where the move went (at-call entry): how many support levels it reached in 5 days
0 levels: 98 calls | 1 levels: 29 calls | 2 levels: 42 calls | 3 levels: 25 calls | 4 levels: 17 calls | 5 levels: 26 calls | 6 levels: 11 calls | 7 levels: 6 calls | 8 levels: 8 calls | 9 levels: 8 calls | 10 levels: 5 calls | 11 levels: 4 calls | 12 levels: 2 calls | 13 levels: 5 calls | 14 levels: 3 calls | 18 levels: 1 calls

Deepest level reached, by type (most common first):
| level type            |   calls |
|:----------------------|--------:|
| none                  |      98 |
| hourly swing low      |      51 |
| daily swing low       |      33 |
| unfilled gap          |      23 |
| prior week low        |      21 |
| daily 10 SMA          |      15 |
| daily 20 SMA          |      10 |
| 5-day value area low  |       8 |
| daily 50 SMA          |       7 |
| 5-day value area high |       7 |
| prior day low         |       6 |
| 5-day volume POC      |       6 |

- Level 1 sat a median **0.40 ATR** under the entry
- Level 2 sat a median **0.66 ATR** under the entry
- Level 3 sat a median **0.93 ATR** under the entry

## 4. What separates your winning calls from your losing calls
Win = stock fell 1 ATR before rising 1 ATR within 5 days. A condition only matters if the gap shows up in BOTH halves (before and after July 2025). Numeric features split at their median.
| feature              | early: win when TRUE    | early: win when FALSE   | late: win when TRUE     | late: win when FALSE   |
|:---------------------|:------------------------|:------------------------|:------------------------|:-----------------------|
| d_macd_cross_down_3d | 67% (n 18)              | 44% (n 100)             | 67% (n 15)              | 50% (n 157)            |
| h4_rsi_above_ma      | 54% (n 68)              | 39% (n 50)              | 60% (n 84)              | 43% (n 88)             |
| d_vol_vs_20          | 43% above 0.94 (n 58)   | 52% (n 60)              | 46% above 0.94 (n 87)   | 56% (n 85)             |
| w_rsi                | 54% above 58.38 (n 56)  | 42% (n 62)              | 55% above 58.38 (n 89)  | 47% (n 83)             |
| minute_of_day        | 51% above 620.00 (n 62) | 44% (n 56)              | 60% above 620.00 (n 82) | 43% (n 90)             |
| h1_rsi               | 55% above 53.24 (n 64)  | 39% (n 54)              | 54% above 53.24 (n 81)  | 48% (n 91)             |
| today_gap_atr        | 41% above 0.03 (n 48)   | 58% (n 42)              | 50% above 0.03 (n 64)   | 56% (n 70)             |
| vix                  | 43% above 17.28 (n 69)  | 53% (n 49)              | 48% above 17.28 (n 75)  | 54% (n 97)             |
| h4_20_below_50       | 52% (n 46)              | 44% (n 72)              | 54% (n 77)              | 49% (n 95)             |
| h1_vs_sma20_atr      | 51% above 0.07 (n 61)   | 44% (n 57)              | 54% above 0.07 (n 84)   | 49% (n 88)             |
| d_vs_sma200_atr      | 52% above 4.59 (n 58)   | 43% (n 60)              | 53% above 4.59 (n 87)   | 49% (n 85)             |
| m15_20_below_50      | 41% (n 51)              | 52% (n 67)              | 49% (n 79)              | 53% (n 93)             |
| h1_macd_above_sig    | 49% (n 63)              | 45% (n 55)              | 54% (n 90)              | 48% (n 82)             |
| m15_rsi_above_ma     | 45% (n 56)              | 50% (n 62)              | 49% (n 83)              | 53% (n 89)             |
| m5_20_below_50       | 44% (n 56)              | 51% (n 62)              | 49% (n 82)              | 53% (n 90)             |

Same features on random control entries (gap in pct points, early / late):
| feature              |   early_gap |   late_gap |
|:---------------------|------------:|-----------:|
| d_vs_sma200_atr      |         7.8 |       12.7 |
| h1_vs_sma20_atr      |        -3.7 |       -5.1 |
| w_rsi                |         3.4 |        8   |
| minute_of_day        |        -2.2 |       -8.1 |
| d_macd_cross_down_3d |         4.9 |        2   |
| vix                  |        -1.5 |      -12   |
| today_gap_atr        |        -3.2 |       -1.1 |
| h4_rsi_above_ma      |        -1.1 |       -0   |
| d_vol_vs_20          |         0.8 |       -3   |
| h1_rsi               |         3   |       -1.8 |
| h4_20_below_50       |         4.6 |       -0.3 |
| m15_20_below_50      |         6.6 |       -3.5 |
| h1_macd_above_sig    |        -2.4 |        0.8 |
| m15_rsi_above_ma     |         1.2 |       -6.7 |
| m5_20_below_50       |       -11   |        6.6 |

Last 4 daily candles before the call (G = green, R = red), win rate and count:
| d_seq4   |   win % |   calls |
|:---------|--------:|--------:|
| RGGG     |      56 |      25 |
| GGRR     |      52 |      24 |
| GGGG     |      50 |      23 |
| GGRG     |      39 |      22 |
| RRGR     |      64 |      22 |
| GRGG     |      35 |      20 |
| GRGR     |      45 |      20 |
| GGGR     |      47 |      19 |
| RRRR     |      47 |      19 |
| RGRG     |      63 |      19 |
| RRGG     |      53 |      19 |
| RGGR     |      33 |      15 |
| RRRG     |      47 |      15 |
| GRRR     |      50 |      12 |
| GRRG     |      67 |       9 |
| RGRR     |      50 |       7 |

## 5. Calls by month
| month   |   calls |   win |   avg_5d_move |   median_rise_against |
|:--------|--------:|------:|--------------:|----------------------:|
| 2024-03 |       1 |    50 |         -0.53 |                  0.32 |
| 2024-04 |       3 |    33 |          0.95 |                  1.58 |
| 2024-05 |       4 |    25 |         -1.21 |                  0.91 |
| 2024-06 |       2 |    25 |         -3.54 |                  0.16 |
| 2024-07 |       5 |    70 |          2.12 |                  1.48 |
| 2024-08 |       1 |     0 |         -2.95 |                  0.02 |
| 2024-09 |       2 |    50 |         -0.26 |                  0.34 |
| 2024-10 |       5 |    60 |          2.55 |                  0.29 |
| 2024-11 |      10 |    10 |         -4.79 |                  2.02 |
| 2024-12 |      12 |    67 |          0.41 |                  0.5  |
| 2025-01 |      11 |    50 |          0.29 |                  1.98 |
| 2025-02 |      13 |    54 |          2.71 |                  1.28 |
| 2025-03 |      21 |    48 |          1.88 |                  1.67 |
| 2025-04 |      14 |    54 |          1.26 |                  1.15 |
| 2025-05 |       7 |    43 |         -0.84 |                  0.73 |
| 2025-06 |       7 |    50 |         -0.17 |                  1.49 |
| 2025-07 |       7 |    79 |          0.93 |                  1.11 |
| 2025-08 |      11 |    36 |          0.58 |                  1.9  |
| 2025-09 |      14 |    43 |          0.52 |                  0.59 |
| 2025-10 |      11 |    32 |         -4.68 |                  1.86 |
| 2025-11 |       5 |    80 |          0.49 |                  0.67 |
| 2025-12 |      11 |    32 |         -2.23 |                  3.19 |
| 2026-01 |      15 |    73 |          4.96 |                  1.4  |
| 2026-02 |      16 |    59 |          0.6  |                  1.7  |
| 2026-03 |      20 |    72 |          3.72 |                  1.52 |
| 2026-04 |       9 |     6 |         -5.51 |                  0.51 |
| 2026-05 |      10 |    25 |         -2.03 |                  3.47 |
| 2026-06 |       9 |    50 |         -2.7  |                  0.72 |
| 2026-07 |      14 |    54 |          1.99 |                  1.31 |
| 2026-08 |      13 |    54 |         -0.1  |                  0.98 |
| 2026-09 |       7 |    64 |          0.53 |                  0.46 |

By ticker (5+ calls):
| sym   |   calls |   win |   avg_5d |
|:------|--------:|------:|---------:|
| KRE   |       5 |    80 |     1.65 |
| INTC  |       7 |    79 |     4.77 |
| AMZN  |       6 |    75 |     1.36 |
| UNH   |       5 |    70 |     6.84 |
| COIN  |      11 |    64 |     2.28 |
| PLTR  |      14 |    61 |     0.02 |
| SPY   |       9 |    56 |     0.2  |
| GOOG  |       5 |    50 |    -2.89 |
| BABA  |       5 |    50 |     0.62 |
| QQQ   |      59 |    48 |    -0.63 |
| NVDA  |      24 |    48 |     0.25 |
| META  |      23 |    48 |     1.26 |
| AMD   |      20 |    48 |     0.49 |
| AAPL  |      10 |    45 |    -0.11 |
| WMT   |       7 |    43 |     0.28 |
| AVGO  |      12 |    42 |    -0.7  |
| NFLX  |       5 |    40 |    -1.64 |
| SLV   |       5 |    40 |     3.31 |
| TSLA  |      20 |    38 |    -1.97 |
| CVNA  |       6 |    25 |    -0.16 |
| MSFT  |       5 |    20 |    -1.94 |

# PART 2: Your 576 real trades, with the real option prices

## 1. Month by month (percent on the contract, from your own fill prices; no dollars)
| month   |   trades |   win_rate |   median_pct |   reached_2x_while_held |   up_20pct_then_closed_red |   went_50pts_higher_after_you_sold |
|:--------|---------:|-----------:|-------------:|------------------------:|---------------------------:|-----------------------------------:|
| 2024-04 |       15 |         40 |        -59   |                      27 |                         40 |                                 27 |
| 2024-05 |       18 |         17 |        -55.4 |                      28 |                         44 |                                 17 |
| 2024-06 |       17 |         12 |        -50.4 |                      18 |                         35 |                                  6 |
| 2024-07 |       27 |         33 |        -29.5 |                      11 |                         19 |                                 56 |
| 2024-08 |       18 |         39 |        -43   |                      28 |                         28 |                                 22 |
| 2024-09 |       27 |         15 |        -39.3 |                      11 |                         41 |                                 19 |
| 2024-10 |       33 |         27 |        -44.8 |                      15 |                         36 |                                 33 |
| 2024-11 |       20 |         20 |        -61.9 |                      15 |                         50 |                                 15 |
| 2024-12 |       28 |         21 |        -56.1 |                      21 |                         32 |                                 32 |
| 2025-01 |       18 |         39 |        -33.8 |                      28 |                         28 |                                 44 |
| 2025-02 |       25 |         32 |        -23.1 |                      28 |                         20 |                                 28 |
| 2025-03 |       28 |         50 |          0.8 |                       7 |                         14 |                                 71 |
| 2025-04 |       30 |         40 |        -25   |                      17 |                         23 |                                 33 |
| 2025-05 |       18 |         22 |        -48.4 |                      17 |                         44 |                                 11 |
| 2025-06 |       23 |         26 |        -50.9 |                       9 |                         35 |                                 26 |
| 2025-07 |        7 |         14 |        -28.1 |                       0 |                         14 |                                  0 |
| 2025-08 |       21 |         29 |        -44.8 |                      14 |                         33 |                                 24 |
| 2025-09 |       33 |         30 |        -35   |                      12 |                         33 |                                 18 |
| 2025-10 |       25 |         36 |        -15.2 |                      24 |                         28 |                                 60 |
| 2025-11 |       13 |         77 |         50   |                      23 |                         15 |                                 77 |
| 2025-12 |       32 |         16 |        -63.5 |                      22 |                         53 |                                 31 |
| 2026-01 |       27 |         33 |        -24.2 |                      19 |                         22 |                                 48 |
| 2026-02 |       25 |         52 |          5.7 |                       8 |                         24 |                                 44 |
| 2026-03 |       27 |         48 |         -7.3 |                       0 |                         22 |                                 59 |
| 2026-04 |       21 |         24 |        -50   |                      10 |                         52 |                                 14 |

## 2. Sold early? The next support level after you sold (puts)
Winning puts: 164. The stock reached the next support level under your exit price, before rising back above your entry/stop, within 3 days in **41%** of them (n 156).
When it did: your exit was a median **+56%**; the same put at that next level was a median **+208%** (it got there a median 2.8 hours after you sold).
Losing puts (for contrast): next level reached after your exit in 13% (n 352).

Which level was next, and how often it got hit (winning puts):
| next_level_name                  |   n |   reached |
|:---------------------------------|----:|----------:|
| hourly swing low                 |  32 |        47 |
| daily swing low                  |  20 |        40 |
| unfilled gap                     |  12 |        25 |
| 5-day value area high            |   7 |        43 |
| daily 10 SMA                     |   7 |        29 |
| daily 50 SMA                     |   7 |        14 |
| 5-day value area low             |   6 |        17 |
| daily 20 SMA                     |   6 |        50 |
| hourly swing low + prior day low |   5 |        20 |

## 3. Exit rules replayed on your actual put contracts (real 1-minute option prices)
Same entry as you, same contract. Each rule exits where the STOCK hits the level / rule; the price is what the option actually traded at that minute. Only trades where the exit landed inside the price window we have (entry to 3 days after your exit) are counted, and 'yours' is shown on the SAME trades.
| exit rule             |   trades |   rule avg % |   rule median % |   rule win % |   yours avg % (same trades) |   yours median % |   rule minus yours, avg |    t |
|:----------------------|---------:|-------------:|----------------:|-------------:|----------------------------:|-----------------:|------------------------:|-----:|
| level1                |      426 |         -3.5 |           -24.5 |         36.6 |                       -10.9 |            -35.3 |                     7.4 |  1.1 |
| level2                |      403 |         -0.5 |           -33   |         29.5 |                       -12.8 |            -36.6 |                    12.2 |  1.9 |
| level3                |      376 |          0.8 |           -37.7 |         22.9 |                       -15.7 |            -37.5 |                    16.4 |  1.7 |
| day_close             |      311 |        -10.3 |           -33.9 |         19.6 |                       -18.4 |            -45.8 |                     8.1 |  0.1 |
| hourly_close_above_20 |      379 |        -37.5 |           -39.3 |          8.7 |                       -24.3 |            -42.9 |                   -13.1 | -2.8 |
| daily_close_above_10  |      327 |        -48.1 |           -46.6 |          4.3 |                       -32.7 |            -48.5 |                   -15.4 | -3.1 |
| hold_3_days           |      328 |        -39.1 |           -45.8 |          5.5 |                       -32.3 |            -48.4 |                    -6.8 | -0.7 |
| hold_5_days           |      328 |        -48.4 |           -46.8 |          4.3 |                       -32.5 |            -48.4 |                   -15.8 | -3.1 |

## 4. Waiting for confirmation on the SAME contract
Option price at the confirmation signal vs your fill (negative = cheaper = you entered too early).
| confirmation        | fired within 2 days   | median option price vs your fill   | share cheaper than your fill   |   then exit level1: avg % |   level1 median % |   then exit hourly_close_above_20: avg % |   hourly_close_above_20 median % |   then exit day_close: avg % |   day_close median % |
|:--------------------|:----------------------|:-----------------------------------|:-------------------------------|--------------------------:|------------------:|-----------------------------------------:|---------------------------------:|-----------------------------:|---------------------:|
| reject_5m200        | 72%                   | -7%                                | 56%                            |                       4.4 |             -20.2 |                                    -34.7 |                            -39.4 |                        -10.8 |                -39.4 |
| hourly_20_retest    | 24%                   | -5%                                | 49%                            |                      20.9 |              14.5 |                                    -42.9 |                            -42   |                         39.1 |                -33.7 |
| break_prior_day_low | 49%                   | +11%                               | 25%                            |                       0.8 |             -10.9 |                                    -38.4 |                            -43.3 |                        -19.6 |                -33.9 |
| failed_breakout     | 82%                   | +1%                                | 43%                            |                      -1.4 |             -23.5 |                                    -38.7 |                            -40   |                        -10.7 |                -32.1 |
| m15_macd_cross      | 82%                   | -13%                               | 58%                            |                       2.8 |             -20.8 |                                    -34.5 |                            -38.6 |                          1.8 |                -25.5 |

Puts where NONE of the confirmations ever came within 2 days: 12 of 522; your median result on those: -55% (vs -38% on the rest).

## 5. What separates your winning puts from your losing puts (conditions at YOUR entry)
| feature               | early: win when TRUE    | early: win when FALSE   | late: win when TRUE     | late: win when FALSE   |
|:----------------------|:------------------------|:------------------------|:------------------------|:-----------------------|
| spy_above_50          | 27% (n 179)             | 34% (n 58)              | 30% (n 210)             | 42% (n 71)             |
| d_from_60d_high_atr   | 32% above 1.67 (n 115)  | 25% (n 122)             | 40% above 1.67 (n 144)  | 26% (n 137)            |
| spy_above_20          | 26% (n 151)             | 33% (n 86)              | 30% (n 207)             | 42% (n 74)             |
| spy_rsi               | 26% above 57.21 (n 112) | 31% (n 125)             | 28% above 57.21 (n 147) | 39% (n 134)            |
| w_macd_above_sig      | 21% (n 135)             | 39% (n 101)             | 30% (n 138)             | 36% (n 143)            |
| d_macd_above_sig      | 34% (n 135)             | 22% (n 102)             | 35% (n 165)             | 30% (n 116)            |
| d_greens_last10       | 26% above 5.00 (n 118)  | 31% (n 119)             | 31% above 5.00 (n 137)  | 35% (n 144)            |
| d_rsi                 | 27% above 57.86 (n 127) | 31% (n 110)             | 28% above 57.86 (n 132) | 38% (n 149)            |
| d_macd_cross_down_3d  | 7% (n 30)               | 32% (n 207)             | 30% (n 27)              | 33% (n 254)            |
| d_vs_sma50_atr        | 27% above 1.89 (n 124)  | 31% (n 113)             | 31% above 1.89 (n 135)  | 35% (n 146)            |
| m5_rsi_above_ma       | 27% (n 105)             | 30% (n 132)             | 30% (n 142)             | 36% (n 139)            |
| d_days_since_20d_high | 32% above 5.00 (n 116)  | 26% (n 121)             | 35% above 5.00 (n 132)  | 32% (n 149)            |
| h4_vs_sma200_atr      | 27% above 1.55 (n 125)  | 30% (n 112)             | 30% above 1.55 (n 134)  | 36% (n 147)            |
| m5_vs_sma20_atr       | 27% above 0.00 (n 117)  | 30% (n 120)             | 25% above 0.00 (n 142)  | 41% (n 139)            |
| w_rsi_above_ma        | 27% (n 113)             | 30% (n 123)             | 31% (n 135)             | 35% (n 146)            |

By entry time:
| minute_of_day   |   trades |   win |   median_pct |
|:----------------|---------:|------:|-------------:|
| 9:30-9:35       |      139 |    34 |     -41.3793 |
| 9:35-10:00      |       74 |    27 |     -44.5595 |
| 10:00-10:30     |       24 |    42 |     -18.0921 |
| 10:30-11:30     |       59 |    20 |     -44.8276 |
| 11:30-1:00      |       72 |    31 |     -35.4211 |
| 1:00-3:00       |       90 |    40 |     -23.736  |
| 3:00-4:00       |       59 |    22 |     -32.0755 |

# PART 4: Extra checks

## Same entries x exits with a WIDER stop (nearest hourly swing high), average R, calls / controls
| entry               |   median stop (ATR) | level1                 | level2                 | level3                 | half_L1_rest_L3        | day_close              | hourly_close_above_20   | hold_3_days            |
|:--------------------|--------------------:|:-----------------------|:-----------------------|:-----------------------|:-----------------------|:-----------------------|:------------------------|:-----------------------|
| at_call             |                0.43 | +0.04 (t 1.4) / -0.06  | +0.09 (t 1.5) / -0.08  | +0.03 (t 0.6) / -0.15  | +0.03 (t 0.7) / -0.10  | -0.01 (t 0.5) / +0.02  | -0.16 (t -0.8) / -0.12  | +0.01 (t 0.2) / -0.12  |
| reject_5m200        |                0.4  | +0.13 (t 1.5) / -0.17  | +0.07 (t 0.7) / -0.17  | -0.00 (t -0.1) / -0.23 | +0.11 (t 1.1) / -0.20  | +0.04 (t 1.0) / +0.02  | +0.03 (t 0.5) / -0.21   | +0.11 (t 0.6) / -0.24  |
| hourly_20_retest    |                0.39 | -0.00 (t -0.3) / -0.01 | +0.05 (t -0.1) / +0.05 | -0.03 (t -0.5) / -0.17 | -0.02 (t -0.4) / -0.07 | -0.05 (t -2.0) / +0.08 | +0.04 (t 0.2) / -0.12   | +0.01 (t -0.0) / -0.11 |
| hourly_20_50_cross  |                0.4  | +0.05 (t 0.8) / +0.07  | +0.18 (t 0.9) / +0.06  | +0.02 (t 0.2) / +0.01  | +0.08 (t 1.0) / +0.03  | -0.03 (t 0.4) / +0.01  | -0.15 (t 0.6) / -0.06   | -0.03 (t 0.4) / +0.09  |
| break_prior_day_low |                0.44 | +0.03 (t 0.5) / -0.01  | +0.06 (t -0.0) / +0.01 | -0.08 (t -2.2) / -0.10 | -0.04 (t -1.1) / -0.06 | -0.02 (t 0.7) / +0.06  | -0.06 (t -0.4) / -0.09  | +0.05 (t -0.1) / -0.04 |
| m15_macd_cross      |                0.46 | +0.03 (t 0.8) / -0.03  | +0.04 (t 0.3) / -0.05  | -0.06 (t -0.7) / -0.15 | +0.02 (t 0.3) / -0.08  | +0.03 (t 1.5) / +0.05  | +0.07 (t 0.8) / -0.10   | +0.11 (t 1.1) / -0.15  |
| failed_breakout     |                0.43 | +0.08 (t 2.1) / +0.01  | +0.04 (t 1.5) / -0.03  | -0.08 (t 0.4) / -0.04  | +0.01 (t 1.5) / -0.04  | -0.02 (t 0.8) / +0.06  | -0.23 (t -0.4) / -0.06  | -0.03 (t 0.5) / -0.04  |
| next_open           |                0.44 | -0.04 (t 0.2) / -0.07  | -0.03 (t 1.0) / -0.08  | +0.04 (t 0.9) / -0.05  | -0.01 (t 1.2) / -0.06  | +0.02 (t 1.6) / +0.03  | -0.03 (t 0.8) / -0.04   | +0.10 (t 1.2) / -0.11  |
| after_red_day       |                0.45 | +0.05 (t 0.5) / -0.05  | +0.01 (t -0.2) / -0.06 | +0.13 (t -0.3) / -0.06 | +0.03 (t 0.3) / -0.04  | +0.03 (t 1.3) / +0.01  | -0.01 (t 0.3) / -0.12   | +0.19 (t 0.1) / -0.15  |

## The two conditions that split winning and losing calls (HYPOTHESIS: picked from ~70 tested)
| group                                      |   calls |   win % |   win % before Jul 2025 |   win % after |   avg 5-day move % |
|:-------------------------------------------|--------:|--------:|------------------------:|--------------:|-------------------:|
| 4H RSI above its MA AND called after 10:20 |      88 |      62 |                      57 |            67 |               1.06 |
| only 4H RSI above its MA                   |      64 |      50 |                      48 |            51 |               1.68 |
| only after 10:20                           |      60 |      47 |                      42 |            50 |              -0.41 |
| neither                                    |      78 |      37 |                      37 |            38 |              -1.03 |
| all calls                                  |     290 |      50 |                      47 |            51 |               0.33 |

## FORWARD TEST: the two conditions on fresh calls (Sep 15 - Oct 7 2026, not used to find them)
| group          |   calls |   win |   avg_5d_move |
|:---------------|--------:|------:|--------------:|
| both           |       9 |    39 |         -2.16 |
| neither        |       3 |    67 |          3.06 |
| one of the two |      10 |    50 |          0.68 |

Verdict: NOT confirmed. With only 22 fresh calls this can't prove or kill it, but the 'both' group did not win more. Keep it as an untested idea, not a rule.

## Winning puts: sell where you sold vs hold for the next support level (real option prices)
| bail-out rule                 |   trades |   yours avg % |   yours median % |   held avg % |   held median % | held beat yours   |    t | outcomes                                          |
|:------------------------------|---------:|--------------:|-----------------:|-------------:|----------------:|:------------------|-----:|:--------------------------------------------------|
| bail 0.25 ATR above your exit |      144 |            82 |               48 |           92 |              28 | 34%               | 0.56 | bailed 91, reached next level 39, window ended 14 |
| bail at your entry price      |      137 |            77 |               46 |          110 |              38 | 49%               | 1.67 | reached next level 63, bailed 44, window ended 30 |

# PART 3: Your patterns, tested on every name 2016 -> now

Pass rule (set before running): beats being short that same name that same year (daily) or that same name / year / time of day (intraday). Discovery 2016-2022 needs win-rate excess t >= 2 and a positive move; holdout 2023-now (never used to define anything) needs t >= 1.5 and a positive move.

| pattern                                       | type     | 2016-2022                                                        | 2023-now                                                         | VERDICT      |
|:----------------------------------------------|:---------|:-----------------------------------------------------------------|:-----------------------------------------------------------------|:-------------|
| WEEKLY sandwich (red, small green, big red)   | daily    | n 50: win 44% (-6.3 pts, t -1.3); move -2.22% (-2.40 vs base)    | n 32: win 37% (-11.9 pts, t -1.7); move -1.81% (-1.50 vs base)   | fail         |
| bear flag (break of flag low)                 | daily    | n 668: win 55% (+6.1 pts, t 0.4); move +0.58% (+0.80 vs base)    | n 402: win 49% (+1.5 pts, t -1.3); move -0.72% (-0.13 vs base)   | fail         |
| bear flag (break of prior day low)            | daily    | n 1147: win 52% (+3.4 pts, t 0.2); move +0.31% (+0.56 vs base)   | n 681: win 51% (+4.4 pts, t 0.4); move -0.36% (+0.25 vs base)    | fail         |
| bear flag, deep pole 4 ATR                    | daily    | n 240: win 57% (+9.2 pts, t 1.4); move +1.41% (+1.71 vs base)    | n 137: win 49% (+1.6 pts, t -0.6); move -1.27% (-0.68 vs base)   | fail         |
| daily 10 SMA crosses under 50 SMA             | daily    | n 1363: win 48% (-0.3 pts, t -1.1); move -0.05% (+0.21 vs base)  | n 859: win 49% (+2.0 pts, t -0.5); move +0.11% (+0.63 vs base)   | fail         |
| daily 10/50 cross, first retest of 10 SMA     | daily    | n 978: win 48% (-0.0 pts, t 0.2); move -0.32% (-0.07 vs base)    | n 637: win 47% (-0.6 pts, t 0.3); move -0.73% (-0.21 vs base)    | fail         |
| double top (break of middle low)              | daily    | n 803: win 52% (+2.9 pts, t -0.5); move -0.10% (+0.06 vs base)   | n 499: win 48% (+0.0 pts, t -0.8); move -0.78% (-0.30 vs base)   | fail         |
| double top (early: red day off 2nd top)       | daily    | n 1454: win 49% (+0.8 pts, t -0.2); move -0.15% (+0.12 vs base)  | n 842: win 50% (+2.8 pts, t -0.6); move -0.59% (+0.02 vs base)   | fail         |
| falling three (red, 3 greens, big red)        | daily    | n 22: win 64% (+12.2 pts, t 1.1); move +1.72% (+1.45 vs base)    | n 21: win 48% (+1.1 pts, t -0.4); move -1.29% (-0.66 vs base)    | fail         |
| falling three (textbook)                      | daily    | n 60: win 50% (+0.2 pts, t -0.0); move -0.06% (-0.05 vs base)    | n 42: win 52% (+4.5 pts, t 0.2); move -0.22% (+0.04 vs base)     | fail         |
| head and shoulders (neckline break)           | daily    | n 181: win 50% (+1.4 pts, t -0.3); move -0.11% (+0.02 vs base)   | n 122: win 51% (+2.9 pts, t 0.2); move -0.51% (-0.02 vs base)    | fail         |
| red-green-green-red                           | daily    | n 6651: win 49% (+0.9 pts, t 0.3); move -0.26% (+0.06 vs base)   | n 4371: win 47% (+0.3 pts, t 0.3); move -0.74% (-0.12 vs base)   | fail         |
| red-green-green-red after 20-day high         | daily    | n 3501: win 50% (+3.0 pts, t 1.3); move -0.17% (+0.28 vs base)   | n 2244: win 49% (+2.5 pts, t 2.3); move -0.46% (+0.26 vs base)   | holdout only |
| red-green-green-red under 20 SMA              | daily    | n 2728: win 48% (-1.3 pts, t -1.1); move -0.36% (-0.22 vs base)  | n 1869: win 47% (-0.4 pts, t 0.2); move -0.93% (-0.43 vs base)   | fail         |
| sandwich (red, small green, big red)          | daily    | n 212: win 40% (-8.0 pts, t -1.5); move -1.49% (-1.16 vs base)   | n 98: win 46% (-2.0 pts, t -0.4); move -0.14% (+0.26 vs base)    | fail         |
| sandwich + 10 SMA under 20 SMA                | daily    | n 108: win 38% (-10.5 pts, t -2.2); move -2.01% (-1.83 vs base)  | n 52: win 49% (+0.1 pts, t -0.6); move -0.82% (-0.53 vs base)    | fail         |
| 5m 200 SMA rejection (10:00-15:00)            | intraday | n 50438: win 51% (+0.3 pts, t -0.1); move +0.00% (+0.01 vs base) | n 32787: win 51% (+0.4 pts, t 0.7); move -0.03% (+0.00 vs base)  | fail         |
| dump by 10 + wedge into 5m 200, rejected      | intraday | n 7649: win 51% (+0.5 pts, t 0.2); move +0.01% (+0.01 vs base)   | n 5331: win 51% (+0.6 pts, t 1.0); move +0.02% (+0.05 vs base)   | fail         |
| dump by 10, chop up into 5m 200, rejected     | intraday | n 11429: win 51% (+0.1 pts, t -0.5); move -0.01% (-0.01 vs base) | n 7861: win 51% (+0.7 pts, t 1.3); move +0.01% (+0.04 vs base)   | fail         |
| dump to 10, bounce 10-12, lose 5m 20 after 12 | intraday | n 8201: win 51% (-0.1 pts, t -0.1); move -0.03% (-0.02 vs base)  | n 5778: win 51% (+0.8 pts, t 1.2); move +0.02% (+0.03 vs base)   | fail         |
| hourly 20 SMA crosses under 50 SMA            | intraday | n 6126: win 51% (+0.2 pts, t -0.7); move +0.01% (+0.01 vs base)  | n 3976: win 50% (+0.1 pts, t -0.5); move -0.06% (-0.04 vs base)  | fail         |
| hourly 20/50 death cross, retest of the 20    | intraday | n 19351: win 51% (+0.4 pts, t -1.5); move +0.01% (+0.01 vs base) | n 12380: win 50% (+0.2 pts, t -1.3); move -0.04% (-0.02 vs base) | fail         |
| rising wedge into 5m 200 SMA, close under     | intraday | n 34364: win 51% (+0.3 pts, t 0.4); move +0.01% (+0.01 vs base)  | n 22244: win 50% (+0.2 pts, t 0.7); move -0.03% (-0.01 vs base)  | fail         |

Daily: win = fell 1 ATR before rising 1 ATR within 5 sessions, short at the next open; move = 5-day. Intraday: win = fell 0.5 ATR before rising 0.5 ATR by the close, short at the signal bar's close; move = to the close.

**Noise check:** the identical pipeline on scrambled charts passed 0 of 23 patterns (should be 0).