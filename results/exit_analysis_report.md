# Exit Analysis - Tazmanian Trader (real trades, real OPRA option bars via Databento)

Trades in tab: 4993 | with expiry found: 4993 | with option bars: 4993
Bar size: 1-hour. Peaks measured on bar CLOSES (conservative). Window: entry to min(expiry, exit + 35 days).

## How the trades actually went
- Realized avg return: -3.1% | median -15.6% | win rate 37.8%
- Went >= +20% green while held: 65.9% of trades
- Went >= +20% green but closed RED: 1638 trades (32.8%)
- Median peak while held: 47.3% vs median realized -15.6%
- Winners: median share of peak captured: 41%
- After exit, contract later reached at least +100 points more than your exit: 1040 trades
- After exit, contract ended the window near zero: 2817 trades
- Held to expiry and EXPIRED (never sold): 289 trades. Of those, went >= +20% green first: 178; went >= +50% green first: 146

### Split by timing quality
- date-only (approx 9:45 in / 15:45 out): 4993 trades | realized avg -3.1% | went +20% green 66% | green-then-red 1638
Date-only trades assume a 9:45 entry and 15:45 exit, so their in-trade peaks are approximate. Trust the exact-time group more.

## Exit rules replayed on your exact entries (sorted by avg log return = compounding growth)
| Rule | Trades | Avg % | Median % | Win % | $ (1 contract each) | t-stat | 1st half avg % | 2nd half avg % |
|---|---|---|---|---|---|---|---|---|
| tp25_sl30 | 4993 | 40.3 | 25.1 | 51.6 | 83,138 | -2.99 | 34.1 | 46.4 |
| tp25_sl50 | 4993 | 42.6 | 28.3 | 59.5 | 112,118 | -6.24 | 37.2 | 48.0 |
| tp50_sl30 | 4993 | 38.7 | -31.6 | 41.8 | 88,738 | -7.36 | 32.2 | 45.2 |
| time_1h | 4993 | 19.4 | -7.0 | 41.2 | 38,459 | -14.10 | 21.1 | 17.8 |
| tp50_sl50 | 4993 | 40.2 | -50.0 | 48.4 | 115,891 | -12.60 | 34.6 | 45.8 |
| tp100_sl30 | 4993 | 34.2 | -34.3 | 29.4 | 87,275 | -15.28 | 27.0 | 41.3 |
| scale_half@50_be_t2@200_sl50 | 4993 | 33.4 | -50.0 | 46.8 | 79,428 | -17.27 | 28.5 | 38.3 |
| scale_half@50_be_t2@300_sl50 | 4993 | 30.4 | -50.0 | 46.7 | 63,326 | -18.93 | 26.1 | 34.6 |
| scale_half@50_be_trail30_sl50 | 4993 | 21.5 | -50.0 | 47.5 | 36,087 | -19.69 | 20.4 | 22.5 |
| scale_half@50_be_trail50_sl50 | 4993 | 17.8 | -50.0 | 46.9 | 25,713 | -21.77 | 17.6 | 18.1 |
| tp200_sl30 | 4993 | 26.6 | -37.1 | 18.6 | 56,193 | -24.92 | 20.1 | 33.1 |
| tp100_sl50 | 4993 | 35.4 | -52.0 | 35.0 | 110,623 | -21.82 | 29.7 | 41.1 |
| scale_half@100_be_t2@200_sl50 | 4993 | 31.1 | -52.0 | 35.0 | 85,825 | -24.46 | 26.6 | 35.6 |
| scale_half@100_be_t2@300_sl50 | 4993 | 28.0 | -52.0 | 35.0 | 67,244 | -26.15 | 24.3 | 31.7 |
| scale_half@100_be_trail30_sl50 | 4993 | 18.1 | -52.0 | 35.0 | 35,924 | -27.54 | 17.0 | 19.1 |
| scale_half@100_be_trail50_sl50 | 4993 | 15.7 | -52.0 | 35.0 | 31,240 | -28.99 | 16.2 | 15.2 |
| tp200_sl50 | 4993 | 28.5 | -54.5 | 23.5 | 79,284 | -32.15 | 24.1 | 32.9 |
| time_4h | 4993 | -3.3 | -18.6 | 32.5 | -7,894 | -33.09 | 5.0 | -11.5 |
| 0_actual | 4993 | -3.1 | -15.6 | 37.8 | -2,783 | -30.92 | -12.6 | 6.5 |
| tp25_slnone | 4993 | 46.4 | 32.4 | 69.4 | 154,441 | -25.40 | 43.8 | 49.0 |
| tp50_slnone | 4993 | 44.9 | 53.3 | 58.5 | 160,874 | -33.71 | 43.2 | 46.6 |
| scale_half@50_be_t2@200_slnone | 4993 | 36.3 | 18.7 | 56.5 | 119,893 | -36.67 | 35.1 | 37.5 |
| scale_half@50_be_t2@300_slnone | 4993 | 33.4 | 17.8 | 56.4 | 109,000 | -37.56 | 33.1 | 33.7 |
| scale_half@50_be_trail30_slnone | 4993 | 23.5 | 25.0 | 57.2 | 69,274 | -37.96 | 26.4 | 20.6 |
| scale_half@50_be_trail50_slnone | 4993 | 21.6 | 18.6 | 56.5 | 74,781 | -38.95 | 27.3 | 15.9 |
| time_24h | 4993 | -9.5 | -63.3 | 24.9 | -6,113 | -52.51 | -1.4 | -17.7 |
| tp100_slnone | 4993 | 40.0 | -85.1 | 44.7 | 165,741 | -45.30 | 39.1 | 40.9 |
| scale_half@100_be_t2@200_slnone | 4993 | 34.5 | -85.1 | 44.7 | 143,597 | -47.11 | 34.5 | 34.5 |
| scale_half@100_be_t2@300_slnone | 4993 | 31.6 | -85.1 | 44.7 | 133,998 | -48.07 | 33.1 | 30.2 |
| scale_half@100_be_trail30_slnone | 4993 | 19.9 | -85.1 | 44.7 | 84,407 | -48.97 | 23.3 | 16.4 |
| scale_half@100_be_trail50_slnone | 4993 | 19.7 | -85.1 | 44.7 | 98,328 | -49.62 | 27.3 | 12.2 |
| time_48h | 4993 | -7.9 | -84.4 | 22.4 | 33,365 | -63.45 | 0.1 | -16.0 |
| tp200_slnone | 4993 | 34.0 | -95.5 | 32.5 | 165,200 | -57.71 | 34.7 | 33.3 |
| time_120h | 4993 | -4.4 | -94.7 | 20.0 | 65,911 | -75.70 | 7.3 | -16.0 |
| hold_to_window_end | 4993 | -2.2 | -96.8 | 19.0 | 143,753 | -83.51 | 12.8 | -17.3 |

## Read this before trusting any rule
- Many rules were tested on the same trades. The best one is partly luck. A rule counts only if it wins in BOTH halves (early and late trades) and its t-stat is >= 3.
- Fills are bar closes, not real bid/ask. Real exits will be somewhat worse, especially on cheap or illiquid contracts.
- These are your entries. The rule tells you how to EXIT your kind of trade, not what to buy.