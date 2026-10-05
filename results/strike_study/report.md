# Strike-distance study — how far out of the money should you buy?

2626 positions since 2024, all accounts. Stock price at entry: exact minute for 24%, that day's VWAP for the rest. Delta from implied vol backed out of YOUR fill price (available for 96%). Avg return capped at +500% per trade; t clustered by day.

## 1. By delta (all expiries)

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 360 | 23% | -21% (t -4.2) | -40% | $-5,049 |
| 0.10-0.20 | 681 | 28% | -17% (t -5.4) | -31% | $-13,075 |
| 0.20-0.30 | 631 | 37% | -6% (t -2.0) | -13% | $-17,556 |
| 0.30-0.40 | 451 | 49% | +0% (t -0.5) | -1% | $-621 |
| 0.40-0.50 | 246 | 49% | +4% (t 1.0) | -1% | $8,273 |
| 0.50+ (in the money) | 153 | 69% | +30% (t 4.8) | +24% | $26,358 |

## 2. By distance from the stock price

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| in the money | 266 | 69% | +37% (t 6.4) | +27% | $46,605 |
| 0-0.5% OTM | 420 | 47% | +3% (t 1.2) | -2% | $5,478 |
| 0.5-1% | 391 | 41% | -5% (t -0.9) | -9% | $-920 |
| 1-2% | 508 | 33% | -12% (t -3.7) | -19% | $-6,341 |
| 2-4% | 511 | 32% | -13% (t -3.4) | -26% | $-14,567 |
| 4%+ OTM | 530 | 29% | -16% (t -5.9) | -28% | $-13,020 |

## 3. Delta within each expiry group (does it hold at every expiry?)


**0DTE**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 97 | 15% | -38% (t -4.6) | -47% | $-1,297 |
| 0.10-0.20 | 182 | 26% | -26% (t -4.2) | -39% | $-4,930 |
| 0.20-0.30 | 166 | 33% | -13% (t -2.4) | -19% | $-4,440 |
| 0.30-0.40 | 118 | 47% | -14% (t -2.6) | -4% | $-4,263 |
| 0.40-0.50 | 70 | 47% | -2% (t -0.0) | -1% | $2,990 |
| 0.50+ (in the money) | 59 | 54% | +18% (t 2.2) | +9% | $2,650 |

**1-3 days**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 155 | 25% | -14% (t -2.3) | -47% | $-1,791 |
| 0.10-0.20 | 279 | 27% | -16% (t -2.8) | -32% | $-7,439 |
| 0.20-0.30 | 275 | 39% | -2% (t -0.4) | -10% | $-7,938 |
| 0.30-0.40 | 178 | 47% | +2% (t 0.4) | -2% | $-5,089 |
| 0.40-0.50 | 101 | 54% | +9% (t 1.8) | +3% | $4,398 |
| 0.50+ (in the money) | 58 | 78% | +40% (t 5.1) | +41% | $13,516 |

**4-14 days**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 87 | 28% | -17% (t -2.2) | -31% | $-1,676 |
| 0.10-0.20 | 193 | 33% | -10% (t -2.7) | -20% | $-2,358 |
| 0.20-0.30 | 167 | 37% | -6% (t -1.3) | -13% | $-4,991 |
| 0.30-0.40 | 132 | 54% | +9% (t 1.8) | +3% | $7,560 |
| 0.40-0.50 | 64 | 45% | +6% (t 0.4) | -5% | $2,201 |
| 0.50+ (in the money) | 34 | 82% | +36% (t 3.8) | +32% | $11,826 |

**15+ days**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 21 | 24% | -16% (t -1.5) | -26% | $-285 |
| 0.10-0.20 | 27 | 33% | -8% (t -1.6) | -13% | $1,652 |
| 0.20-0.30 | 23 | 48% | -7% (t -0.8) | +0% | $-187 |
| 0.30-0.40 | 23 | 48% | +2% (t -0.4) | -5% | $1,171 |
| 0.40-0.50 | 11 | 27% | -8% (t -1.1) | -16% | $-1,316 |
| 0.50+ (in the money) | 2 | 0% | -45% (t nan) | -45% | $-1,634 |

## 4. Delta by period (does it hold before, during and after the best run?)


**before** — median delta bought: 0.20, share at delta >= 0.30: 28%

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 254 | 19% | -30% (t -4.1) | -53% | $-5,619 |
| 0.10-0.20 | 367 | 26% | -18% (t -3.7) | -41% | $-6,976 |
| 0.20-0.30 | 296 | 35% | -4% (t -0.6) | -30% | $-9,809 |
| 0.30-0.40 | 196 | 46% | +2% (t -0.1) | -7% | $1,736 |
| 0.40-0.50 | 105 | 47% | +7% (t 0.6) | -5% | $2,670 |
| 0.50+ (in the money) | 68 | 81% | +48% (t 5.6) | +44% | $20,146 |

**best run** — median delta bought: 0.27, share at delta >= 0.30: 42%

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 49 | 43% | +25% (t 0.1) | -10% | $781 |
| 0.10-0.20 | 139 | 34% | -14% (t -2.5) | -27% | $-3,808 |
| 0.20-0.30 | 152 | 45% | -6% (t -1.8) | -8% | $-4,477 |
| 0.30-0.40 | 142 | 49% | -3% (t -0.6) | -1% | $-2,388 |
| 0.40-0.50 | 77 | 51% | +4% (t 1.1) | +1% | $4,518 |
| 0.50+ (in the money) | 47 | 70% | +24% (t 1.7) | +36% | $5,275 |

**after** — median delta bought: 0.24, share at delta >= 0.30: 32%

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 57 | 23% | -21% (t -3.6) | -20% | $-211 |
| 0.10-0.20 | 175 | 29% | -16% (t -6.3) | -12% | $-2,291 |
| 0.20-0.30 | 183 | 33% | -9% (t -3.5) | -7% | $-3,270 |
| 0.30-0.40 | 113 | 54% | +0% (t -0.7) | +1% | $31 |
| 0.40-0.50 | 64 | 50% | +1% (t 0.0) | +0% | $1,085 |
| 0.50+ (in the money) | 38 | 45% | +3% (t 0.4) | -2% | $937 |

## 5. Walk-forward delta floor

Picked on Jan 2024 - Oct 2025 only: **buy delta >= 0.40**. Scored on Nov 2025 - Sep 2026:

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| Nov 2025+, everything | 1236 | 41% | -5% (t -4.5) | -6% | $-3,818 |
| Nov 2025+, delta >= 0.40 | 226 | 54% | +7% (t 1.9) | +3% | $11,815 |
| Nov 2025+, delta < 0.40 | 1010 | 39% | -8% (t -5.8) | -9% | $-15,633 |

## Notes

- Exact-minute prices make delta precise; VWAP-based rows can be off when the stock moved a lot that day.
- Positions with no delta: fill at or below intrinsic value, or an unrealistic implied vol.
- This measures what WAS bought; it doesn't prove a deeper strike would have won on the same idea, but it shows where your results come from.
