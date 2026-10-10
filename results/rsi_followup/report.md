# RSI follow-up — trade path and option estimates

Option = buy at-the-money, ~21 days to expiry, priced with Black-Scholes using the real volatility index (VIX/VXN/RVX) day by day for ETFs, realized vol x1.2 for stocks. Random = the same option trade on every day of that symbol and period. Edge = signal minus random. t clustered by month.

## PASS CHECK (set before running): exit (b) +50% target else day 10; edge > 0 every period, t >= 3, 100+ trades

| Signal | Group | Entry | Edge 2000-15 / 16-21 / 22-26 | All years | Verdict |
|---|---|---|---|---|---|
| RSI 30 → calls | ETF | signal close | +6.2% / -1.3% / +20.3% | +7.4% (t 3.8, n 434) | fail |
| RSI 30 → calls | ETF | confirm (RSI back through the line) | -5.6% / -18.5% / +3.7% | -6.6% (t -0.5, n 415) | fail |
| RSI 30 → calls | MEGA | signal close | +6.9% / +25.0% / +16.2% | +12.6% (t 4.1, n 381) | **PASS** |
| RSI 30 → calls | MEGA | confirm (RSI back through the line) | -1.8% / +5.3% / +11.1% | +2.6% (t 1.0, n 331) | fail |
| RSI 70 → puts | ETF | signal close | -0.9% / +12.1% / -2.3% | +3.2% (t 4.0, n 942) | fail |
| RSI 70 → puts | ETF | confirm (RSI back through the line) | -0.5% / +3.1% / +1.2% | +1.0% (t 1.1, n 741) | fail |
| RSI 70 → puts | MEGA | signal close | +0.4% / +5.8% / -7.1% | +0.5% (t 2.2, n 938) | fail |
| RSI 70 → puts | MEGA | confirm (RSI back through the line) | +1.0% / +6.8% / -1.5% | +2.2% (t 1.6, n 712) | fail |
| RSI 80 → puts | ETF | signal close | +7.9% / +12.6% / +32.8% | +16.1% (t 1.6, n 119) | fail |
| RSI 80 → puts | ETF | confirm (RSI back through the line) | -3.6% / -6.2% / +15.7% | +0.3% (t -0.4, n 112) | fail |
| RSI 80 → puts | MEGA | signal close | +3.9% / +14.4% / +2.8% | +7.1% (t 2.0, n 202) | fail |
| RSI 80 → puts | MEGA | confirm (RSI back through the line) | -0.4% / +11.0% / -4.9% | +2.4% (t 0.8, n 181) | fail |

## RSI 30 → CALLS

### Option estimate (average return per trade, and vs random)

| Group / split | Entry | Trades | Hold 10 days | +50% target else day 10 | +50% target / −50% stop | Win rate (b) | Random (b) |
|---|---|---|---|---|---|---|---|
| ETF: all | signal close | 434 | +20.2% (edge +11.6, t 3.1) | +4.5% (edge +7.4, t 3.8) | +5.1% (edge +5.7, t 3.5) | 58% | -2.9% |
| ETF: 50 over 200 | signal close | 275 | +19.8% (edge +9.7, t 2.2) | +5.6% (edge +7.6, t 3.4) | +6.0% (edge +5.9, t 3.1) | 59% | -2.1% |
| ETF: 50 under 200 | signal close | 159 | +20.9% (edge +15.0, t 1.9) | +2.7% (edge +7.1, t 1.2) | +3.5% (edge +5.3, t 1.4) | 57% | -4.3% |
| ETF: vol index under 25 | signal close | 139 | +32.6% (edge +25.0, t 1.3) | +7.2% (edge +10.4, t 1.4) | +8.4% (edge +9.2, t 1.5) | 59% | -3.3% |
| ETF: vol index 25+ | signal close | 295 | +14.3% (edge +5.3, t 2.4) | +3.3% (edge +6.0, t 3.2) | +3.6% (edge +4.0, t 2.7) | 58% | -2.7% |
| ETF: QQQ only | signal close | 42 | +25.1% (edge +17.2, t 1.5) | +6.5% (edge +9.4, t 1.8) | +6.2% (edge +6.8, t 1.4) | 60% | -2.9% |
| ETF: all | confirm (RSI back through the line) | 415 | +4.2% (edge -4.6, t 0.6) | -9.4% (edge -6.6, t -0.5) | -6.7% (edge -6.1, t -0.6) | 44% | -2.9% |
| ETF: 50 over 200 | confirm (RSI back through the line) | 254 | +5.7% (edge -4.6, t -0.4) | -8.4% (edge -6.4, t -0.1) | -6.9% (edge -7.1, t -0.3) | 43% | -2.0% |
| ETF: 50 under 200 | confirm (RSI back through the line) | 161 | +1.8% (edge -4.4, t 0.7) | -11.1% (edge -6.8, t -1.0) | -6.2% (edge -4.5, t -0.8) | 46% | -4.2% |
| ETF: vol index under 25 | confirm (RSI back through the line) | 168 | +11.5% (edge +2.5, t 0.0) | -8.5% (edge -6.0, t -0.6) | -4.6% (edge -4.3, t -0.6) | 45% | -2.5% |
| ETF: vol index 25+ | confirm (RSI back through the line) | 247 | -0.8% (edge -9.4, t 0.7) | -10.1% (edge -7.0, t -0.0) | -8.1% (edge -7.3, t -0.4) | 43% | -3.1% |
| ETF: QQQ only | confirm (RSI back through the line) | 41 | +4.7% (edge -3.4, t 0.4) | -15.5% (edge -12.7, t -0.7) | -12.7% (edge -12.2, t -1.0) | 37% | -2.8% |
| MEGA: all | signal close | 381 | +25.9% (edge +12.8, t 2.5) | +5.5% (edge +12.6, t 4.1) | +5.7% (edge +10.7, t 3.5) | 61% | -7.1% |
| MEGA: 50 over 200 | signal close | 213 | +29.7% (edge +15.8, t 1.6) | +11.6% (edge +18.1, t 3.3) | +12.5% (edge +17.1, t 3.3) | 66% | -6.6% |
| MEGA: 50 under 200 | signal close | 168 | +21.1% (edge +9.0, t 1.3) | -2.1% (edge +5.6, t 1.1) | -3.0% (edge +2.5, t 0.6) | 54% | -7.7% |
| MEGA: all | confirm (RSI back through the line) | 331 | +12.0% (edge -1.3, t 0.4) | -4.4% (edge +2.6, t 1.0) | -4.6% (edge +0.4, t 0.5) | 51% | -7.0% |
| MEGA: 50 over 200 | confirm (RSI back through the line) | 182 | +10.8% (edge -3.3, t -0.4) | -3.5% (edge +2.9, t 0.2) | -3.3% (edge +1.3, t -0.2) | 51% | -6.4% |
| MEGA: 50 under 200 | confirm (RSI back through the line) | 149 | +13.3% (edge +1.2, t 0.5) | -5.5% (edge +2.2, t 0.4) | -6.2% (edge -0.7, t -0.0) | 52% | -7.7% |

### Path (the stock/ETF itself, 10 days after entry)

| Group | Entry | Trades | Avg move your way | Worst move against you: median / 75th pct / 90th pct | +3% your way before −3% against | Median days to +3% |
|---|---|---|---|---|---|---|
| ETF | signal close | 434 | +1.51% | -3.4% / -7.0% / -12.5% | 51% | 2 |
| ETF | confirm (RSI back through the line) | 415 | -0.26% | -4.0% / -7.4% / -14.3% | 40% | 3 |
| ETF | next open (stock only) | 434 | +1.50% | — | — | — |
| MEGA | signal close | 381 | +1.65% | -4.9% / -10.2% / -16.4% | 49% | 2 |
| MEGA | confirm (RSI back through the line) | 331 | +0.60% | -4.9% / -10.4% / -19.4% | 50% | 2 |
| MEGA | next open (stock only) | 381 | +1.46% | — | — | — |

## RSI 70 → PUTS

### Option estimate (average return per trade, and vs random)

| Group / split | Entry | Trades | Hold 10 days | +50% target else day 10 | +50% target / −50% stop | Win rate (b) | Random (b) |
|---|---|---|---|---|---|---|---|
| ETF: all | signal close | 942 | -12.9% (edge -0.2, t 1.7) | -14.2% (edge +3.2, t 4.0) | -9.9% (edge +1.0, t 3.4) | 43% | -17.3% |
| ETF: 50 over 200 | signal close | 795 | -11.9% (edge +1.0, t 1.9) | -14.9% (edge +2.7, t 3.7) | -10.5% (edge +0.6, t 3.1) | 43% | -17.5% |
| ETF: 50 under 200 | signal close | 147 | -18.4% (edge -6.7, t -0.2) | -10.4% (edge +5.9, t 1.2) | -6.7% (edge +3.6, t 0.6) | 44% | -16.4% |
| ETF: vol index under 25 | signal close | 845 | -13.1% (edge -0.6, t 1.7) | -15.8% (edge +1.4, t 3.5) | -11.2% (edge -0.4, t 3.0) | 42% | -17.2% |
| ETF: vol index 25+ | signal close | 97 | -11.3% (edge +3.0, t -0.6) | +0.1% (edge +18.8, t 1.2) | +2.0% (edge +13.9, t 1.0) | 58% | -18.7% |
| ETF: QQQ only | signal close | 103 | -28.2% (edge -15.5, t -3.4) | -21.5% (edge -4.4, t -0.9) | -18.8% (edge -8.1, t -2.1) | 33% | -17.1% |
| ETF: all | confirm (RSI back through the line) | 741 | -17.0% (edge -4.4, t -0.8) | -16.2% (edge +1.0, t 1.1) | -10.8% (edge +0.1, t 0.9) | 42% | -17.2% |
| ETF: 50 over 200 | confirm (RSI back through the line) | 618 | -16.3% (edge -3.5, t -0.5) | -15.4% (edge +1.9, t 1.4) | -10.4% (edge +0.6, t 1.2) | 43% | -17.4% |
| ETF: 50 under 200 | confirm (RSI back through the line) | 123 | -20.5% (edge -8.9, t -0.7) | -19.9% (edge -3.7, t -1.0) | -12.8% (edge -2.6, t -0.9) | 39% | -16.2% |
| ETF: vol index under 25 | confirm (RSI back through the line) | 651 | -15.4% (edge -2.9, t -0.5) | -15.9% (edge +1.1, t 1.1) | -10.5% (edge +0.2, t 0.9) | 42% | -17.0% |
| ETF: vol index 25+ | confirm (RSI back through the line) | 90 | -28.8% (edge -15.3, t -2.4) | -18.0% (edge +0.1, t -0.8) | -12.3% (edge -0.9, t -0.9) | 42% | -18.1% |
| ETF: QQQ only | confirm (RSI back through the line) | 72 | -35.7% (edge -22.9, t -3.8) | -28.7% (edge -11.5, t -2.0) | -22.8% (edge -12.0, t -2.6) | 28% | -17.2% |
| MEGA: all | signal close | 938 | -15.8% (edge -1.3, t 1.1) | -22.5% (edge +0.5, t 2.2) | -17.0% (edge -1.0, t 1.7) | 35% | -23.0% |
| MEGA: 50 over 200 | signal close | 727 | -16.4% (edge -1.6, t 0.7) | -21.9% (edge +1.3, t 2.0) | -16.6% (edge -0.4, t 1.4) | 36% | -23.2% |
| MEGA: 50 under 200 | signal close | 211 | -13.5% (edge -0.0, t 0.2) | -24.5% (edge -2.2, t -0.1) | -18.3% (edge -2.9, t -0.3) | 31% | -22.3% |
| MEGA: all | confirm (RSI back through the line) | 712 | -14.9% (edge -0.4, t 0.7) | -20.8% (edge +2.2, t 1.6) | -15.2% (edge +0.8, t 1.2) | 37% | -23.0% |
| MEGA: 50 over 200 | confirm (RSI back through the line) | 555 | -15.4% (edge -0.7, t 0.9) | -19.9% (edge +3.2, t 1.7) | -15.1% (edge +0.9, t 1.2) | 37% | -23.1% |
| MEGA: 50 under 200 | confirm (RSI back through the line) | 157 | -13.0% (edge +0.6, t 0.1) | -23.7% (edge -1.3, t -0.5) | -15.4% (edge +0.2, t -0.0) | 34% | -22.4% |

### Path (the stock/ETF itself, 10 days after entry)

| Group | Entry | Trades | Avg move your way | Worst move against you: median / 75th pct / 90th pct | +3% your way before −3% against | Median days to +3% |
|---|---|---|---|---|---|---|
| ETF | signal close | 942 | -0.39% | -1.9% / -3.4% / -5.1% | 27% | 5 |
| ETF | confirm (RSI back through the line) | 741 | -0.57% | -2.1% / -3.5% / -6.0% | 28% | 4 |
| ETF | next open (stock only) | 942 | -0.35% | — | — | — |
| MEGA | signal close | 938 | -1.29% | -4.3% / -8.0% / -13.9% | 39% | 3 |
| MEGA | confirm (RSI back through the line) | 712 | -1.15% | -4.2% / -7.9% / -13.6% | 42% | 3 |
| MEGA | next open (stock only) | 938 | -1.19% | — | — | — |

## RSI 80 → PUTS

### Option estimate (average return per trade, and vs random)

| Group / split | Entry | Trades | Hold 10 days | +50% target else day 10 | +50% target / −50% stop | Win rate (b) | Random (b) |
|---|---|---|---|---|---|---|---|
| ETF: all | signal close | 119 | -7.7% (edge +5.8, t -0.1) | -2.3% (edge +16.1, t 1.6) | +0.9% (edge +12.5, t 1.3) | 55% | -18.4% |
| ETF: 50 over 200 | signal close | 112 | -14.5% (edge -0.8, t -0.9) | -5.6% (edge +12.9, t 0.9) | -2.2% (edge +9.5, t 0.6) | 52% | -18.5% |
| ETF: 50 under 200 | signal close | 7 | +101.6% (edge +112.7, t 1.7) | +50.0% (edge +66.7, t 33.8) | +50.0% (edge +60.4, t 43.1) | 100% | -16.7% |
| ETF: vol index under 25 | signal close | 110 | -15.0% (edge -1.8, t -1.0) | -5.2% (edge +12.9, t 1.2) | -2.2% (edge +9.2, t 0.7) | 52% | -18.1% |
| ETF: vol index 25+ | signal close | 9 | +82.4% (edge +99.2, t 2.1) | +33.7% (edge +55.1, t 1.9) | +38.9% (edge +52.6, t 2.8) | 89% | -21.4% |
| ETF: QQQ only | signal close | 17 | +24.8% (edge +38.9, t 1.4) | +1.3% (edge +19.9, t 1.4) | +7.3% (edge +19.1, t 1.6) | 59% | -18.6% |
| ETF: all | confirm (RSI back through the line) | 112 | -23.7% (edge -10.5, t -1.8) | -17.8% (edge +0.3, t -0.4) | -14.4% (edge -3.0, t -0.8) | 46% | -18.1% |
| ETF: 50 over 200 | confirm (RSI back through the line) | 106 | -28.4% (edge -15.0, t -2.3) | -18.1% (edge +0.1, t -0.3) | -15.3% (edge -3.8, t -0.7) | 46% | -18.2% |
| ETF: 50 under 200 | confirm (RSI back through the line) | 6 | +58.8% (edge +69.9, t 0.5) | -12.5% (edge +4.6, t -0.2) | +0.0% (edge +10.6, t 0.0) | 50% | -17.1% |
| ETF: vol index under 25 | confirm (RSI back through the line) | 103 | -26.8% (edge -13.9, t -2.1) | -22.0% (edge -4.2, t -0.9) | -16.9% (edge -5.6, t -1.2) | 43% | -17.8% |
| ETF: vol index 25+ | confirm (RSI back through the line) | 9 | +11.8% (edge +28.6, t 0.8) | +30.0% (edge +51.4, t 1.8) | +13.2% (edge +26.9, t 1.4) | 89% | -21.4% |
| ETF: QQQ only | confirm (RSI back through the line) | 16 | +5.7% (edge +19.4, t 0.8) | +1.1% (edge +19.3, t 1.3) | +0.7% (edge +12.3, t 1.0) | 62% | -18.3% |
| MEGA: all | signal close | 202 | -6.7% (edge +8.0, t 1.1) | -16.1% (edge +7.1, t 2.0) | -13.5% (edge +2.6, t 0.6) | 40% | -23.1% |
| MEGA: 50 over 200 | signal close | 176 | -4.7% (edge +10.2, t 1.1) | -13.9% (edge +9.3, t 2.0) | -11.3% (edge +4.9, t 1.0) | 42% | -23.2% |
| MEGA: 50 under 200 | signal close | 26 | -20.8% (edge -7.0, t -0.2) | -30.7% (edge -8.1, t -0.6) | -28.9% (edge -13.1, t -1.7) | 27% | -22.6% |
| MEGA: all | confirm (RSI back through the line) | 181 | -10.6% (edge +4.0, t 0.7) | -20.7% (edge +2.4, t 0.8) | -18.0% (edge -1.9, t -0.1) | 33% | -23.1% |
| MEGA: 50 over 200 | confirm (RSI back through the line) | 162 | -10.3% (edge +4.3, t 0.3) | -18.9% (edge +4.3, t 0.7) | -16.4% (edge -0.3, t 0.1) | 35% | -23.1% |
| MEGA: 50 under 200 | confirm (RSI back through the line) | 19 | -13.0% (edge +1.5, t 0.2) | -36.3% (edge -13.1, t -0.9) | -32.0% (edge -15.8, t -1.9) | 21% | -23.2% |

### Path (the stock/ETF itself, 10 days after entry)

| Group | Entry | Trades | Avg move your way | Worst move against you: median / 75th pct / 90th pct | +3% your way before −3% against | Median days to +3% |
|---|---|---|---|---|---|---|
| ETF | signal close | 119 | -0.09% | -1.8% / -2.9% / -4.0% | 39% | 4 |
| ETF | confirm (RSI back through the line) | 112 | -0.98% | -2.4% / -3.7% / -5.2% | 24% | 4 |
| ETF | next open (stock only) | 119 | -0.12% | — | — | — |
| MEGA | signal close | 202 | -1.66% | -4.3% / -9.6% / -17.1% | 42% | 3 |
| MEGA | confirm (RSI back through the line) | 181 | -2.46% | -4.6% / -10.5% / -17.9% | 43% | 2 |
| MEGA | next open (stock only) | 202 | -1.30% | — | — | — |

## QQQ RSI 30 signals (every one)

| Date | VXN | Trend | 10-day move | Worst against | Option: hold 10d | +50% else day 10 | +50%/−50% |
|---|---|---|---|---|---|---|---|
| 2000-04-14 | 71 | 50 over 200 | +19.0% | -3.0% | +161% | +50% | +50% |
| 2000-10-11 | 58 | 50 under 200 | +1.1% | -3.4% | +0% | +50% | +50% |
| 2001-02-27 | 73 | 50 under 200 | -9.3% | -14.7% | -73% | -73% | -50% |
| 2001-03-16 | 76 | 50 under 200 | -5.0% | -7.8% | -58% | -58% | -50% |
| 2001-04-03 | 75 | 50 under 200 | +31.4% | -3.1% | +266% | +50% | +50% |
| 2001-09-07 | 65 | 50 under 200 | -15.5% | -19.3% | -91% | -91% | -50% |
| 2002-04-26 | 42 | 50 under 200 | -4.8% | -8.4% | -55% | -55% | -50% |
| 2002-07-02 | 60 | 50 under 200 | +7.1% | -1.8% | +42% | +50% | +50% |
| 2004-08-06 | 27 | 50 under 200 | +3.9% | -1.1% | +43% | +43% | +43% |
| 2005-01-24 | 20 | 50 over 200 | +3.1% | +0.2% | +55% | +50% | +50% |
| 2005-04-15 | 22 | 50 over 200 | +0.7% | -1.1% | -24% | -24% | -24% |
| 2006-05-16 | 17 | 50 over 200 | -2.6% | -4.1% | -62% | -62% | -50% |
| 2006-06-12 | 26 | 50 over 200 | +2.3% | -0.6% | +7% | +7% | +7% |
| 2008-01-08 | 31 | 50 over 200 | -6.2% | -11.3% | -81% | -81% | -50% |
| 2008-01-25 | 34 | 50 over 200 | -0.9% | -4.2% | -47% | -47% | -50% |
| 2008-03-10 | 31 | 50 under 200 | +8.7% | -0.5% | +149% | +50% | +50% |
| 2008-09-09 | 29 | 50 under 200 | -4.4% | -6.9% | -61% | -61% | -50% |
| 2008-09-29 | 50 | 50 under 200 | -7.1% | -22.3% | -63% | -63% | -50% |
| 2008-10-15 | 73 | 50 under 200 | +3.9% | -8.2% | -5% | -5% | -5% |
| 2010-05-07 | 42 | 50 over 200 | -1.3% | -4.2% | -38% | +50% | +50% |
| 2011-08-08 | 45 | 50 over 200 | -0.8% | -1.3% | -39% | +50% | +50% |
| 2012-05-17 | 26 | 50 over 200 | -1.9% | -2.0% | -50% | -50% | -50% |
| 2012-11-08 | 20 | 50 over 200 | +2.8% | -2.9% | +37% | +37% | -50% |
| 2014-10-15 | 27 | 50 over 200 | +8.1% | -2.1% | +159% | +50% | +50% |
| 2015-08-21 | 30 | 50 over 200 | -0.2% | -17.2% | -34% | -34% | -34% |
| 2016-01-07 | 27 | 50 over 200 | -1.0% | -7.3% | -46% | -46% | -50% |
| 2016-06-27 | 24 | 50 over 200 | +9.1% | +1.1% | +223% | +50% | +50% |
| 2016-11-04 | 23 | 50 over 200 | +3.2% | +0.3% | +33% | +50% | +50% |
| 2018-10-10 | 28 | 50 over 200 | -3.7% | -3.9% | -67% | -67% | -50% |
| 2018-10-24 | 30 | 50 over 200 | +6.2% | -3.2% | +84% | +50% | +50% |
| 2018-12-21 | 34 | 50 under 200 | +8.4% | -2.5% | +121% | +50% | +50% |
| 2019-06-03 | 24 | 50 over 200 | +8.0% | +0.7% | +189% | +50% | +50% |
| 2019-08-05 | 28 | 50 over 200 | +4.3% | -0.5% | +46% | +50% | +50% |
| 2020-02-27 | 41 | 50 over 200 | -13.8% | -14.0% | -79% | +50% | +50% |
| 2020-03-12 | 68 | 50 over 200 | +8.5% | -6.8% | +32% | +32% | -50% |
| 2021-10-04 | 28 | 50 over 200 | +5.7% | +0.2% | +83% | +50% | +50% |
| 2022-01-21 | 34 | 50 over 200 | +1.8% | -5.0% | -10% | -10% | -10% |
| 2022-09-26 | 37 | 50 under 200 | -2.9% | -3.9% | -55% | -55% | -50% |
| 2024-04-19 | 23 | 50 over 200 | +5.0% | -0.2% | +96% | +50% | +50% |
| 2025-03-10 | 29 | 50 over 200 | +3.9% | -1.3% | +33% | +33% | +33% |
| 2025-04-04 | 38 | 50 over 200 | +2.5% | -4.8% | +4% | +50% | +50% |
| 2026-03-30 | 33 | 50 over 200 | +12.6% | +1.1% | +229% | +50% | +50% |

Limits: option prices are Black-Scholes estimates (no bid/ask spread, earlier calibration says too pessimistic on decay). Real fills on QQQ/SPY options are tight; on smaller ETFs and in panics, spreads widen. Mega tech = known winners.
