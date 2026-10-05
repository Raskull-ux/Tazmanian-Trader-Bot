# Strike-distance study — how far out of the money should you buy?

2626 positions since 2024, all accounts. Stock price at entry: exact minute for 24%, that day's OPEN for the rest (no after-entry information). Delta from implied vol backed out of YOUR fill price (available for 94%). Avg return capped at +500% per trade; t clustered by day.

## 1. By delta (all expiries)

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 357 | 26% | -16% (t -2.9) | -35% | $-3,642 |
| 0.10-0.20 | 731 | 35% | -7% (t -2.9) | -20% | $-2,036 |
| 0.20-0.30 | 585 | 39% | -7% (t -2.3) | -12% | $-5,682 |
| 0.30-0.40 | 449 | 48% | +4% (t 0.8) | -2% | $13,223 |
| 0.40-0.50 | 255 | 54% | +7% (t 1.7) | +3% | $9,081 |
| 0.50+ (in the money) | 94 | 45% | +10% (t 1.2) | -3% | $8,688 |

## 2. By distance from the stock price

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| in the money | 249 | 39% | -4% (t -0.4) | -5% | $6,291 |
| 0-0.5% OTM | 373 | 45% | +1% (t 0.6) | -4% | $3,378 |
| 0.5-1% | 392 | 42% | -0% (t -0.2) | -9% | $806 |
| 1-2% | 519 | 41% | -6% (t -2.5) | -13% | $5,758 |
| 2-4% | 549 | 38% | -6% (t -3.5) | -15% | $1,292 |
| 4%+ OTM | 544 | 33% | -9% (t -2.9) | -21% | $-290 |

## 3. Delta within each expiry group (does it hold at every expiry?)


**0DTE**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 93 | 24% | -25% (t -2.2) | -36% | $-1,056 |
| 0.10-0.20 | 195 | 32% | -14% (t -2.4) | -26% | $-1,320 |
| 0.20-0.30 | 161 | 42% | -4% (t -0.6) | -10% | $-1,540 |
| 0.30-0.40 | 91 | 45% | -1% (t 0.0) | -8% | $1,106 |
| 0.40-0.50 | 62 | 58% | +11% (t 1.3) | +11% | $4,861 |
| 0.50+ (in the money) | 49 | 41% | +3% (t 0.2) | -4% | $2,788 |

**1-3 days**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 155 | 27% | -11% (t -1.9) | -40% | $-1,078 |
| 0.10-0.20 | 302 | 34% | -2% (t -0.6) | -21% | $-1,899 |
| 0.20-0.30 | 247 | 38% | -10% (t -1.7) | -13% | $-3,913 |
| 0.30-0.40 | 206 | 48% | +5% (t 1.2) | -2% | $6,338 |
| 0.40-0.50 | 94 | 55% | +7% (t 1.5) | +5% | $-1,210 |
| 0.50+ (in the money) | 31 | 48% | +16% (t 1.4) | +0% | $3,129 |

**4-14 days**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 88 | 28% | -14% (t -1.6) | -31% | $-1,223 |
| 0.10-0.20 | 207 | 38% | -7% (t -2.1) | -15% | $-763 |
| 0.20-0.30 | 158 | 36% | -6% (t -0.9) | -14% | $-424 |
| 0.30-0.40 | 125 | 53% | +9% (t 1.6) | +2% | $4,856 |
| 0.40-0.50 | 87 | 53% | +8% (t 1.2) | +3% | $7,190 |
| 0.50+ (in the money) | 13 | 54% | +29% (t 1.1) | +12% | $4,389 |

**15+ days**

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 21 | 24% | -16% (t -1.5) | -26% | $-285 |
| 0.10-0.20 | 27 | 37% | -6% (t -1.3) | -8% | $1,946 |
| 0.20-0.30 | 19 | 53% | -4% (t -0.5) | +0% | $195 |
| 0.30-0.40 | 27 | 41% | -3% (t -1.1) | -8% | $923 |
| 0.40-0.50 | 12 | 25% | -11% (t -1.4) | -17% | $-1,760 |
| 0.50+ (in the money) | 1 | 0% | -90% (t nan) | -90% | $-1,618 |

## 4. Delta by period (does it hold before, during and after the best run?)


**before** — median delta bought: 0.20, share at delta >= 0.30: 28%

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 250 | 21% | -26% (t -3.1) | -51% | $-4,491 |
| 0.10-0.20 | 385 | 32% | -7% (t -1.8) | -37% | $-488 |
| 0.20-0.30 | 279 | 35% | -7% (t -1.1) | -32% | $-3,125 |
| 0.30-0.40 | 214 | 46% | +6% (t 0.8) | -8% | $12,284 |
| 0.40-0.50 | 128 | 52% | +6% (t 1.0) | +4% | $903 |
| 0.50+ (in the money) | 29 | 59% | +23% (t 1.3) | +13% | $4,085 |

**best run** — median delta bought: 0.28, share at delta >= 0.30: 42%

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 50 | 46% | +29% (t 0.8) | -7% | $950 |
| 0.10-0.20 | 144 | 43% | -4% (t -1.3) | -12% | $-887 |
| 0.20-0.30 | 134 | 44% | -5% (t -1.4) | -8% | $-416 |
| 0.30-0.40 | 136 | 53% | +4% (t 0.8) | +7% | $587 |
| 0.40-0.50 | 92 | 58% | +12% (t 1.7) | +11% | $8,037 |
| 0.50+ (in the money) | 38 | 47% | +6% (t 0.3) | -1% | $4,105 |

**after** — median delta bought: 0.22, share at delta >= 0.30: 24%

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 57 | 33% | -12% (t -2.1) | -14% | $-101 |
| 0.10-0.20 | 202 | 35% | -8% (t -4.5) | -9% | $-661 |
| 0.20-0.30 | 172 | 41% | -8% (t -4.3) | -5% | $-2,141 |
| 0.30-0.40 | 99 | 46% | -0% (t -1.1) | -3% | $352 |
| 0.40-0.50 | 35 | 49% | -1% (t 0.0) | -0% | $141 |
| 0.50+ (in the money) | 27 | 26% | +0% (t 0.4) | -4% | $498 |

## 5. Walk-forward delta floor

Picked on Jan 2024 - Oct 2025 only: **buy delta >= 0.40**. Scored on Nov 2025 - Sep 2026:

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| Nov 2025+, everything | 1186 | 44% | -1% (t -2.9) | -5% | $10,464 |
| Nov 2025+, delta >= 0.40 | 192 | 49% | +7% (t 1.6) | +0% | $12,781 |
| Nov 2025+, delta < 0.40 | 994 | 43% | -3% (t -3.9) | -6% | $-2,317 |

## 6. Precision check: exact-minute fills only (the cleanest data)

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 131 | 26% | -18% (t -1.8) | -51% | $-2,620 |
| 0.10-0.20 | 204 | 27% | -16% (t -3.2) | -38% | $-1,905 |
| 0.20-0.30 | 155 | 33% | -15% (t -2.1) | -41% | $-4,042 |
| 0.30-0.40 | 91 | 43% | -4% (t -0.4) | -18% | $482 |
| 0.40-0.50 | 43 | 47% | -1% (t -0.1) | -11% | $579 |
| 0.50+ (in the money) | 4 | 25% | -9% (t -0.2) | -27% | $11 |

## 7. Date-only fills (stock price = day open)

| Bucket | Positions | Win rate | Avg return | Median | Net $ |
|---|---|---|---|---|---|
| delta <0.10 | 226 | 27% | -14% (t -2.7) | -30% | $-1,022 |
| 0.10-0.20 | 527 | 38% | -3% (t -1.2) | -12% | $-131 |
| 0.20-0.30 | 430 | 41% | -4% (t -1.1) | -8% | $-1,640 |
| 0.30-0.40 | 358 | 50% | +6% (t 1.7) | +0% | $12,741 |
| 0.40-0.50 | 212 | 55% | +9% (t 2.2) | +6% | $8,502 |
| 0.50+ (in the money) | 90 | 46% | +11% (t 1.3) | -2% | $8,677 |

## Notes

- Exact-minute prices make delta precise. Day-open rows are unbiased but noisier (the stock moves before you enter).
- Positions with no delta: fill at or below intrinsic value, or an unrealistic implied vol.
- This measures what WAS bought; it doesn't prove a deeper strike would have won on the same idea, but it shows where your results come from.
