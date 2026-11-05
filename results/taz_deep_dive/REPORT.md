# Taz's own trades: deep dive

576 of 576 trades rebuilt from the 5-minute bars with extended hours (522 puts, 54 calls), Apr 01 2024 to Apr 30 2026.
Every number is a percent or a count. Option returns are his real fills (exit / entry - 1). No dollar P&L anywhere.

**How to read this**
- **Win** = option return above 0. **2x+** = option return of +100% or more.
- **Fit period** = Apr 2024 to Mar 2025 (conditions were ranked here). **Judged period** = Apr 2025 to Apr 2026 (only used to check; nothing was picked here).
- Everything is measured from bars that had **already closed** at his entry minute, so it is what he could have seen. Rows marked **H:** use the rest of the day (hindsight) and rows marked **B:** are his own behavior after entry; both are shown for understanding but are kept out of the checklist.
- The main study is his **puts** (522 trades, 91% of everything). All the trend clues are bearish by definition, so the 54 calls get their own short section at the end.
- ATR = daily ATR 14 (Wilder) as of the prior close. Levels: daily candles are the regular session; 5m/15m/1h MAs include extended hours.

## Baseline (puts)

| Period | Puts | Win rate | 2x+ rate | Median option return |
|---|---|---|---|---|
| Fit (Apr 2024-Mar 2025) | 239 | 29% | 11% | -40% |
| Judged (Apr 2025-Apr 2026) | 283 | 33% | 5% | -31% |
| All | 522 | 31% | 8% | -38% |

## Plain-English summary

His puts won 29% of the time in the fit year and 33% in the judged year. Almost nothing about the 5-minute picture (RSI, TD count, MACD, VWAP, the moving averages, the gap, QQQ, how many levels were stacked) separated winners from losers in a way that held in both years: those flipped sign from one year to the next. What held is simple: **he wins when the bigger trend has already broken and he shorts the actual top of the day, and he loses when he shorts a stock that is still going up.**

**What held in both years (knowable at entry):**

1. **The bigger trend was already broken.** Monthly red (last month red and this month red so far), 3 weekly lower highs in a row, or a 4h cliff diver in the last 10 days. Puts with at least one of these won 39% (n 51) in the fit year and 42% (n 74) in the judged year, vs 27% (n 188) and 30% (n 209) with none. With 2 or more: 64% (n 11) and 67% (n 9) (very few trades). Only about 1 in 4 of his puts had any of them.
2. **The last closed 5m candle made a lower high.** Won 34% (n 114) / 38% (n 122) vs 25% (n 125) / 30% (n 161) without it.
3. Both together (at least one broken clue plus a 5m lower high): 42% (n 24) / 44% (n 32). Neither: 21% (n 98) / 26% (n 119).

**The biggest difference is timing, and it is hindsight** (you only know the day's high after the close, but it says what his winners look like):

- Entered within 0.25 ATR of the day's eventual high: won 49% (n 74) / 45% (n 102). Everything else: 21% (n 165) / 27% (n 181).
- Entered in the 15 minutes after the day's high printed: 52% (n 23) / 67% (n 42). Entered 60+ minutes BEFORE the day's high (shorting while it was still going up): 11% (n 73) / 17% (n 122).
- Days where the high printed in the first 30 minutes: 41% (n 88) / 51% (n 90). Days where it printed later: 23% (n 151) / 25% (n 193).

**How long he held (his behavior, held in both years):**

- Sold within the hour: 43% (n 21) / 59% (n 56). Held 2+ days: 12% (n 43) / 27% (n 26). Part of this is cause and effect running backwards (winners hit target fast, losers get held hoping), but it matches the old finding that his overnight holds bleed.

**What did NOT hold (do not use these as reasons to enter):** price above or below VWAP, the open, the prior close, the 5m/15m/1h 50 and 200, the daily 8 EMA/10/50/200; 5m and 15m RSI; TD counts; MACD turning; volume; gap size; what QQQ was doing; the daily grade (B or better won 13% in the fit year and 44% in the judged year); levels stacked (83% of all his entries already had 3+ levels within 0.25 ATR, so it does not separate anything). Being within 1 ATR of the 20-day high was fine in the fit year and bad in the judged year (33% (n 111) / 23% (n 141) vs 26% (n 128) / 44% (n 142) away from it).

**2x+ winners:** no condition separated 2x+ trades in both years. Every lean in the fit year (above the 5m 200, 15m RSI 60+, near the high so far) reversed in the judged year. 2x+ trades are too rare (27 and 13) to build a rule on.

**Exits:** on winners he left a median of about 0.2 ATR (roughly 0.4% of the stock) on the table to that day's low, and about half his winners were sold before the day's low printed. Same-day exits leave little on the table; the leak is the entry (shorting the climb) and holding for days.

### Winning profile

A put on a name whose bigger trend is already broken (month red, weekly lower highs, a recent 4h cliff dive). The day's high prints early, usually in the first 30 minutes. He enters within a quarter ATR of that high, right after it prints, on a 5m candle that made a lower high, and he is out the same session, often inside the hour.

### Losing profile

A put on a stock with its trend intact (no broken clue), often near its 20-day high. He shorts while it is still making new highs: the day's high comes an hour or more after his entry. The 5m candle at entry is still making higher highs. He then holds it overnight or for 2 to 3 days.

## Taz's A+ setup (only what held in both years)

| # | Check | Fit year win rate | Judged year win rate |
|---|---|---|---|
| 1 | **Trend already broken**: at least one of monthly red (last month red and this month red so far), 3 weekly lower highs in a row, a 4h cliff diver in the last 10 trading days. Two or more = A+. | 39% (n 51); 2+: 64% (n 11) | 42% (n 74); 2+: 67% (n 9) |
| 2 | **Trigger**: wait for a closed 5m candle that makes a lower high. No lower high, no entry. | 34% (n 114) | 38% (n 122) |
| 3 | **Short the top, not the climb**: the day's high has printed (it held when it printed in the first 30 minutes) and you are within 0.25 ATR of it. If it is still making new highs, wait. (Built from the hindsight table; the live version is check 2.) | 49% (n 74) | 45% (n 102) |
| 4 | **Get paid the same session.** Puts sold inside the hour won 43% (n 21) / 59% (n 56); 2+ day holds won 12% (n 43) / 27% (n 26). | | |
| | **All of 1 and 2 together** | 42% (n 24) | 44% (n 32) |
| | Baseline (every put) | 29% (n 239) | 33% (n 283) |

**Do not count as a reason:** RSI level, TD count, MACD turn, VWAP, which MA it is above, gap size, QQQ direction, daily grade, number of stacked levels. None of them held in both years.

**Honest limits:** 24 months, one trader, one account. The broken-trend clues are each on only 20 to 40 puts per year, so a 10-point gap could still be luck (z-scores 0.8 to 2.1). The direction matches the HANDOFF notes on his trades; results/broken_vs_strength tests the same clues market-wide. Forward-log every A+ trade before trusting it with size.

## The detail: conditions ranked on the fit year, checked on the judged year

Ranked on the fit period only (strength of the win-rate gap, z-score, at least 20 trades on each side), then checked on the judged period. **Held** = same direction in the judged period, gap of 5+ points, 15+ trades each side.

| Rank | Condition (knowable at entry) | Fit: win with / without (n) | Fit z | Judged: win with / without (n) | Judged z | Held? |
|---|---|---|---|---|---|---|
| 1 | Daily grade B or better (4+/6) | 13% / 33% (46/193) | -2.7 | 44% / 30% (62/221) | +2.0 | no |
| 2 | 10-day chart 10 EMA under 10 SMA | 37% / 23% (102/137) | +2.3 | 35% / 32% (153/130) | +0.6 | no |
| 3 | 10-day chart 10 EMA crossed under 10 SMA within 2 candles | 46% / 26% (35/204) | +2.3 | 31% / 33% (26/257) | -0.3 | no |
| 4 | Within 0.25 ATR of the high so far | 36% / 23% (113/126) | +2.3 | 30% / 37% (154/129) | -1.3 | no |
| 5 | Monthly red (last month and this month so far) | 48% / 27% (23/216) | +2.1 | 39% / 32% (36/247) | +0.8 | YES |
| 6 | First 15m candle closed back under the prior close | 22% / 35% (77/110) | -1.8 | 38% / 29% (60/96) | +1.2 | no |
| 7 | Above the daily 200 | 28% / 44% (214/25) | -1.7 | 33% / 32% (239/44) | +0.2 | no |
| 8 | First 15m candle closed under the daily 10 SMA | 21% / 33% (57/130) | -1.7 | 45% / 24% (65/91) | +2.7 | no |
| 9 | Above the daily 10 SMA | 33% / 22% (159/80) | +1.6 | 28% / 44% (194/89) | -2.6 | no |
| 10 | Last 5m candle made a lower high | 34% / 25% (114/125) | +1.6 | 38% / 30% (122/161) | +1.4 | YES |
| 11 | Above the daily 8 EMA | 33% / 23% (156/83) | +1.6 | 29% / 43% (201/82) | -2.2 | no |
| 12 | Price above the open | 34% / 25% (111/128) | +1.6 | 29% / 38% (140/143) | -1.6 | no |
| 13 | Above the 15m 200 | 33% / 24% (146/93) | +1.5 | 28% / 43% (187/96) | -2.4 | no |
| 14 | Above the 5m 50 | 33% / 25% (129/110) | +1.5 | 29% / 38% (154/129) | -1.6 | no |
| 15 | Above the 1h 50 | 33% / 24% (147/92) | +1.4 | 29% / 42% (185/98) | -2.2 | no |
| 16 | 15m RSI 60+ | 35% / 26% (83/156) | +1.4 | 30% / 35% (111/172) | -1.0 | no |
| 17 | Entered 15-60 minutes after the open | 41% / 28% (27/212) | +1.4 | 27% / 34% (30/253) | -0.8 | no |
| 18 | Price above the prior close | 33% / 25% (120/119) | +1.4 | 31% / 37% (168/115) | -1.0 | no |
| 19 | Below yesterday's low | 22% / 31% (51/188) | -1.4 | 35% / 33% (48/235) | +0.4 | no |
| 20 | Within 1 ATR of the 20-day high | 33% / 26% (111/128) | +1.3 | 23% / 44% (141/142) | -3.7 | no |

At a strict bar (fit z 1.5+) only 2 held: Monthly red (last month and this month so far), Last 5m candle made a lower high. To get the 3 to 5 the brief asks for, the bar was lowered to fit z 1.0+ (still ranked on the fit period only). The extra ones are weaker and rest on 20 to 40 trades each.

**The ones that held in both halves (used for the checklist):**

- **Monthly red (last month and this month so far)** helps: fit 48% vs 27%, judged 39% vs 32%.
- **Last 5m candle made a lower high** helps: fit 34% vs 25%, judged 38% vs 30%.
- **3 weekly lower highs** helps: fit 40% vs 28%, judged 48% vs 32%.
- **4h cliff diver in the last 10 days** helps: fit 40% vs 28%, judged 48% vs 32%.

**Stacking them** (how many of the held conditions lined up on the right side):

| Count lined up | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 of 4 | 98 | 21% | 11% | 119 | 26% | 3% | -48% |
| 1 of 4 | 109 | 32% | 11% | 123 | 35% | 4% | -37% |
| 2 of 4 | 28 | 39% | 11% | 40 | 50% | 10% | -9% |
| 3 of 4 | 4 | 75% | 25% | 1 | 0% | 0% | +7% |

### Same ranking for 2x+ winners

2x+ trades are rare (27 in the fit period, 13 in the judged period), so treat this as a lean.

| Condition | Fit: 2x+ with / without (n) | Fit z | Judged: 2x+ with / without (n) | Judged z |
|---|---|---|---|---|
| Above the 5m 200 | 16% / 6% (132/107) | +2.5 | 3% / 7% (176/107) | -1.2 |
| 15m RSI 60+ | 18% / 8% (83/156) | +2.4 | 4% / 5% (111/172) | -0.6 |
| Above the 1h 50 | 15% / 5% (147/92) | +2.3 | 4% / 6% (185/98) | -0.9 |
| Within 1 ATR of the 20-day high | 16% / 7% (111/128) | +2.2 | 2% / 7% (141/142) | -2.0 |
| Within 0.25 ATR of the high so far | 16% / 7% (113/126) | +2.1 | 3% / 7% (154/129) | -1.8 |
| 4h cliff diver in the last 10 days | 25% / 10% (20/219) | +2.0 | 4% / 5% (23/260) | -0.1 |
| Above the 15m 200 | 14% / 6% (146/93) | +1.9 | 4% / 6% (187/96) | -1.0 |
| Above the daily 8 EMA | 14% / 6% (156/83) | +1.9 | 3% / 7% (201/82) | -1.4 |
| Price above the open | 15% / 8% (111/128) | +1.8 | 3% / 6% (140/143) | -1.4 |
| Above the 5m 50 | 15% / 7% (129/110) | +1.8 | 4% / 5% (154/129) | -0.6 |

### Follow-up added after seeing the data (not used for the checklist)

The strongest thing in the whole study is hindsight: his winners were entered right at the day's high (see section 1). This checks a version he could see live: the high of the day so far printed in the last 15 minutes, price is still within 0.25 ATR of it, and the last 5m candle made a lower high. It was designed after looking at both halves, so it is a lead to forward-test, not a proven rule.

### Just topped, knowable at entry


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| high so far printed 5-15 min ago, within 0.25 ATR of it, last 5m candle a lower high | 6 | 67% | 33% | 8 | 38% | 0% | -7% |
| everything else | 233 | 28% | 11% | 275 | 33% | 5% | -38% |

## 1. Timing

### Minutes after the open at entry


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0-5 min | 37 | 30% | 14% | 93 | 37% | 5% | -41% |
| 5-15 min | 15 | 27% | 20% | 34 | 26% | 3% | -41% |
| 15-30 min | 13 | 38% | 23% | 18 | 17% | 6% | -57% |
| 30-60 min | 14 | 43% | 14% | 12 | 42% | 0% | -25% |
| 1-2 h | 38 | 16% | 3% | 23 | 26% | 4% | -45% |
| 2-4 h | 49 | 37% | 16% | 44 | 32% | 0% | -32% |
| last 2 h | 73 | 27% | 7% | 59 | 39% | 8% | -28% |

### Entry before or after the day's high (H)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| before the day's high (it went higher after) | 107 | 23% | 5% | 160 | 22% | 2% | -51% |
| after the day's high | 132 | 34% | 17% | 123 | 48% | 7% | -18% |

### Entry distance under the day's eventual high, in ATR (H)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| within 0.25 ATR | 74 | 49% | 23% | 102 | 45% | 7% | -8% |
| 0.25-0.5 | 76 | 25% | 9% | 102 | 33% | 4% | -38% |
| 0.5-1 | 72 | 17% | 4% | 63 | 16% | 0% | -51% |
| 1-2 | 17 | 18% | 0% | 13 | 23% | 15% | -54% |
| 2+ ATR | 0 | - | - | 3 | 33% | 0% | -70% |

### Minutes from the day's high to his entry (H)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 60+ min before the high | 71 | 11% | 3% | 121 | 17% | 2% | -57% |
| 15-60 before | 23 | 39% | 0% | 25 | 28% | 0% | -34% |
| 0-15 before | 13 | 62% | 23% | 14 | 50% | 14% | +14% |
| 0-15 after | 23 | 52% | 35% | 42 | 67% | 12% | +25% |
| 15-60 after | 20 | 35% | 15% | 14 | 50% | 0% | -10% |
| 60+ min after | 89 | 29% | 12% | 67 | 36% | 6% | -32% |

### Day trade vs overnight swing (B)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| day trade (sold same day) | 80 | 44% | 18% | 200 | 33% | 4% | -30% |
| overnight swing | 159 | 22% | 8% | 83 | 34% | 7% | -41% |

### Results by hold length (B)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under 15 min | 3 | 33% | 0% | 15 | 73% | 7% | +22% |
| 15-60 min | 18 | 44% | 11% | 41 | 54% | 5% | +3% |
| 1-3 h | 28 | 54% | 29% | 68 | 31% | 4% | -37% |
| 3 h to close | 31 | 35% | 13% | 76 | 16% | 1% | -48% |
| 1 night | 116 | 26% | 10% | 57 | 37% | 9% | -41% |
| 2-3 days | 34 | 15% | 3% | 23 | 30% | 4% | -38% |
| 4+ days | 9 | 0% | 0% | 3 | 0% | 0% | -67% |

## 2. Location

### Price vs the prior close (ATR)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 1+ ATR under | 7 | 14% | 0% | 7 | 57% | 14% | -42% |
| 0.25-1 under | 55 | 20% | 4% | 58 | 40% | 3% | -32% |
| at it (+/-0.25) | 87 | 34% | 16% | 101 | 28% | 5% | -46% |
| 0.25-1 over | 71 | 27% | 8% | 88 | 39% | 3% | -30% |
| 1+ ATR over | 19 | 47% | 26% | 29 | 17% | 7% | -34% |

### The gap


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| gap down 1%+ | 21 | 33% | 5% | 33 | 48% | 9% | -23% |
| gap down 0.3-1% | 36 | 25% | 14% | 67 | 28% | 3% | -39% |
| flat | 100 | 26% | 10% | 71 | 37% | 3% | -40% |
| gap up 0.3-1% | 49 | 35% | 10% | 51 | 29% | 6% | -37% |
| gap up 1%+ | 33 | 33% | 18% | 61 | 30% | 5% | -39% |

### Price vs the open


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0.5+ ATR under the open | 29 | 28% | 3% | 11 | 27% | 9% | -38% |
| 0-0.5 under | 84 | 24% | 8% | 88 | 36% | 5% | -44% |
| 0-0.5 over | 96 | 36% | 17% | 147 | 30% | 4% | -31% |
| 0.5+ over | 30 | 23% | 10% | 37 | 41% | 5% | -32% |

### Price vs VWAP


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0.5+ ATR under VWAP | 4 | 50% | 0% | 4 | 50% | 25% | -20% |
| 0-0.5 under | 87 | 25% | 9% | 77 | 32% | 4% | -41% |
| 0-0.5 over | 107 | 32% | 12% | 101 | 32% | 4% | -30% |
| 0.5+ over | 4 | 25% | 25% | 8 | 12% | 0% | -64% |

### Price vs the 5m 50


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 45 | 27% | 4% | 39 | 44% | 10% | -39% |
| at it (+/-0.25 ATR) | 154 | 30% | 13% | 198 | 34% | 4% | -38% |
| over (0.25+ ATR) | 40 | 30% | 12% | 46 | 22% | 2% | -47% |

### Price vs the 5m 200


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 60 | 23% | 2% | 48 | 40% | 6% | -37% |
| at it (+/-0.25 ATR) | 97 | 29% | 14% | 130 | 32% | 6% | -41% |
| over (0.25+ ATR) | 82 | 34% | 15% | 105 | 32% | 2% | -31% |

### Price vs the 15m 50


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 58 | 22% | 3% | 49 | 43% | 6% | -37% |
| at it (+/-0.25 ATR) | 108 | 31% | 13% | 138 | 29% | 5% | -45% |
| over (0.25+ ATR) | 73 | 33% | 15% | 96 | 34% | 3% | -30% |

### Price vs the 15m 200


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 65 | 26% | 5% | 63 | 43% | 6% | -29% |
| at it (+/-0.25 ATR) | 61 | 21% | 7% | 64 | 33% | 6% | -41% |
| over (0.25+ ATR) | 113 | 35% | 18% | 156 | 29% | 3% | -38% |

### Price vs the 1h 50


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 66 | 26% | 5% | 63 | 43% | 6% | -30% |
| at it (+/-0.25 ATR) | 64 | 23% | 8% | 64 | 31% | 5% | -42% |
| over (0.25+ ATR) | 109 | 35% | 17% | 156 | 30% | 4% | -37% |

### Price vs the 1h 200


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 66 | 24% | 6% | 74 | 41% | 5% | -33% |
| at it (+/-0.25 ATR) | 24 | 38% | 8% | 39 | 41% | 13% | -18% |
| over (0.25+ ATR) | 149 | 30% | 14% | 170 | 28% | 2% | -45% |

### Price vs the daily 8 EMA


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 64 | 25% | 6% | 71 | 45% | 8% | -30% |
| at it (+/-0.25 ATR) | 40 | 15% | 2% | 37 | 32% | 3% | -39% |
| over (0.25+ ATR) | 135 | 36% | 16% | 175 | 29% | 3% | -40% |

### Price vs the daily 10 SMA


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 64 | 23% | 8% | 76 | 43% | 8% | -32% |
| at it (+/-0.25 ATR) | 34 | 21% | 3% | 36 | 36% | 6% | -34% |
| over (0.25+ ATR) | 141 | 34% | 15% | 171 | 28% | 3% | -40% |

### Price vs the daily 50


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 53 | 25% | 6% | 82 | 38% | 4% | -29% |
| at it (+/-0.25 ATR) | 19 | 32% | 11% | 14 | 43% | 14% | -34% |
| over (0.25+ ATR) | 167 | 31% | 13% | 186 | 30% | 4% | -41% |

### Price vs the daily 200


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 20 | 35% | 5% | 40 | 32% | 5% | -31% |
| at it (+/-0.25 ATR) | 6 | 50% | 0% | 4 | 50% | 0% | +4% |
| over (0.25+ ATR) | 211 | 27% | 12% | 237 | 33% | 5% | -39% |

### Price vs the yesterday's high


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 131 | 26% | 8% | 129 | 40% | 7% | -37% |
| at it (+/-0.25 ATR) | 65 | 35% | 15% | 86 | 28% | 1% | -50% |
| over (0.25+ ATR) | 43 | 30% | 14% | 68 | 28% | 4% | -35% |

### Price vs the yesterday's low


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under (0.25+ ATR) | 20 | 20% | 0% | 26 | 46% | 8% | -39% |
| at it (+/-0.25 ATR) | 64 | 28% | 8% | 61 | 30% | 3% | -37% |
| over (0.25+ ATR) | 155 | 31% | 14% | 196 | 33% | 5% | -38% |

### Nearest unfilled gray box (daily, bodies only)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| inside a box | 111 | 32% | 8% | 134 | 43% | 6% | -28% |
| within 0.25 ATR | 38 | 29% | 11% | 50 | 28% | 4% | -51% |
| 0.25-1 ATR | 62 | 24% | 16% | 63 | 17% | 5% | -45% |
| 1+ ATR away | 28 | 32% | 14% | 36 | 33% | 0% | -29% |

### Nearest unfilled box ABOVE price (resistance a put would fade)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| box bottom within 0.25 ATR above | 52 | 38% | 8% | 75 | 35% | 5% | -32% |
| 0.25-1 ATR above | 68 | 25% | 10% | 95 | 31% | 7% | -38% |
| 1+ ATR above | 23 | 22% | 13% | 34 | 44% | 3% | -30% |

### Levels stacked within 0.25 ATR of his entry
Levels counted: prior close, open, VWAP, yesterday's high and low, 5m/15m/1h 50 and 200, daily 8 EMA/10/50/200, every unfilled box edge.

| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 | 8 | 0% | 0% | 6 | 33% | 0% | -75% |
| 1 | 15 | 33% | 13% | 11 | 27% | 0% | -40% |
| 2 | 26 | 42% | 23% | 30 | 30% | 0% | -38% |
| 3 | 18 | 11% | 0% | 25 | 24% | 0% | -41% |
| 4-5 | 37 | 32% | 8% | 67 | 36% | 10% | -25% |
| 6+ | 135 | 30% | 12% | 144 | 35% | 4% | -39% |

## 3. Momentum

### 5m RSI at entry


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under 30 | 34 | 26% | 3% | 34 | 38% | 12% | -42% |
| 30-40 | 40 | 25% | 12% | 47 | 40% | 2% | -41% |
| 40-50 | 42 | 36% | 12% | 49 | 29% | 6% | -40% |
| 50-60 | 43 | 21% | 9% | 53 | 36% | 2% | -39% |
| 60-70 | 48 | 31% | 15% | 42 | 36% | 2% | -26% |
| 70-80 | 20 | 40% | 15% | 40 | 25% | 8% | -30% |
| 80+ | 12 | 33% | 17% | 18 | 22% | 0% | -65% |

### 15m RSI at entry


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under 30 | 27 | 26% | 4% | 38 | 34% | 8% | -48% |
| 30-40 | 34 | 29% | 12% | 38 | 45% | 8% | -29% |
| 40-50 | 51 | 22% | 8% | 53 | 34% | 2% | -45% |
| 50-60 | 44 | 30% | 7% | 43 | 30% | 5% | -39% |
| 60-70 | 38 | 39% | 24% | 56 | 29% | 2% | -28% |
| 70-80 | 31 | 39% | 13% | 35 | 34% | 6% | -26% |
| 80+ | 14 | 14% | 14% | 20 | 25% | 5% | -65% |

### TD sell count on the 5m


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 (no sell count) | 136 | 29% | 10% | 139 | 36% | 6% | -38% |
| 1-3 | 67 | 30% | 15% | 84 | 27% | 2% | -38% |
| 4-6 | 27 | 26% | 7% | 41 | 39% | 5% | -40% |
| 7-9 | 9 | 33% | 11% | 19 | 26% | 0% | -30% |

### TD sell count on the 15m


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 (no sell count) | 122 | 26% | 8% | 138 | 33% | 4% | -44% |
| 1-3 | 62 | 34% | 13% | 74 | 30% | 4% | -31% |
| 4-6 | 40 | 32% | 15% | 51 | 41% | 8% | -24% |
| 7-9 | 15 | 27% | 20% | 20 | 25% | 0% | -68% |

### TD sell count on the 1h


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 (no sell count) | 114 | 30% | 10% | 139 | 40% | 5% | -34% |
| 1-3 | 77 | 29% | 10% | 76 | 24% | 5% | -41% |
| 4-6 | 38 | 29% | 16% | 45 | 27% | 4% | -37% |
| 7-9 | 10 | 30% | 20% | 23 | 35% | 0% | -40% |

### 5m MACD histogram


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| just turned down | 38 | 32% | 11% | 48 | 42% | 2% | -35% |
| falling 2+ bars | 99 | 32% | 13% | 104 | 31% | 7% | -36% |
| rising / flat | 102 | 25% | 10% | 131 | 32% | 4% | -39% |

### 15m MACD histogram


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| just turned down | 38 | 24% | 5% | 53 | 38% | 8% | -40% |
| falling 2+ bars | 82 | 27% | 12% | 88 | 31% | 3% | -37% |
| rising / flat | 119 | 33% | 13% | 142 | 33% | 4% | -38% |

### Last 3 closed 5m candles: how many red


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 red | 36 | 28% | 14% | 37 | 30% | 0% | -43% |
| 1 red | 80 | 26% | 11% | 97 | 29% | 3% | -41% |
| 2 red | 96 | 30% | 11% | 115 | 33% | 4% | -37% |
| 3 red | 27 | 37% | 7% | 34 | 50% | 15% | -6% |

### Last 5m candle upper wick (share of range)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| upper wick under 20% | 116 | 33% | 12% | 130 | 27% | 3% | -41% |
| 20-40% | 60 | 27% | 10% | 81 | 36% | 6% | -33% |
| 40%+ | 63 | 25% | 11% | 72 | 42% | 6% | -32% |

### Last 5m candle made a lower high


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| not a lower high | 125 | 25% | 11% | 161 | 30% | 4% | -44% |
| lower high | 114 | 34% | 11% | 122 | 38% | 6% | -32% |

### Last 5m volume vs its 20-bar average


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under 0.7x | 41 | 27% | 15% | 39 | 31% | 3% | -39% |
| 0.7-1.5x | 109 | 30% | 8% | 115 | 36% | 3% | -31% |
| 1.5-3x | 54 | 30% | 9% | 60 | 40% | 8% | -39% |
| 3x+ | 35 | 29% | 20% | 69 | 25% | 4% | -44% |

## 4. The day's shape

### First 15m candle closed over or back under the prior close (entries 9:45+)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| over | 110 | 35% | 13% | 96 | 29% | 5% | -36% |
| under | 77 | 22% | 6% | 60 | 38% | 3% | -34% |

### Gap-up days only: first 15m close vs the prior close (entries 9:45+)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| over | 58 | 38% | 16% | 59 | 25% | 7% | -36% |
| under | 3 | 33% | 0% | 0 | - | - | -72% |

### First 15m candle closed over or under the daily 10 SMA (entries 9:45+)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| over | 130 | 33% | 12% | 91 | 24% | 3% | -38% |
| under | 57 | 21% | 5% | 65 | 45% | 6% | -31% |

### Did the day's high print in the first 30 minutes? (H)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| high printed in the first 30 min | 88 | 41% | 18% | 90 | 51% | 10% | -7% |
| high printed later | 151 | 23% | 7% | 193 | 25% | 2% | -48% |

### What QQQ was doing at entry (vs its prior close)


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| QQQ down 0.5%+ | 69 | 23% | 7% | 55 | 31% | 2% | -43% |
| QQQ down 0-0.5% | 47 | 45% | 19% | 59 | 32% | 7% | -37% |
| QQQ up 0-0.5% | 56 | 16% | 9% | 67 | 31% | 4% | -41% |
| QQQ up 0.5%+ | 67 | 36% | 12% | 102 | 36% | 5% | -26% |

### QQQ vs its VWAP at entry


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| QQQ over VWAP | 107 | 32% | 13% | 111 | 33% | 4% | -33% |
| QQQ under VWAP | 95 | 26% | 8% | 79 | 29% | 5% | -38% |

## 5. The bigger picture

### Daily grade (the bot's put grade, as of the prior close)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| D (0-2) | 159 | 31% | 13% | 184 | 28% | 4% | -40% |
| C (3) | 34 | 41% | 9% | 37 | 41% | 8% | -37% |
| B (4) | 28 | 18% | 7% | 49 | 41% | 4% | -27% |
| A- (5) | 16 | 6% | 6% | 10 | 60% | 10% | -32% |
| A (6+) | 2 | 0% | 0% | 3 | 33% | 0% | -37% |

### Monthly red (last month red and this month so far)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 23 | 48% | 9% | 36 | 39% | 6% | -27% |
| no | 216 | 27% | 12% | 247 | 32% | 4% | -38% |

### 3 weekly lower highs


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 20 | 40% | 5% | 25 | 48% | 12% | -13% |
| no | 219 | 28% | 12% | 258 | 32% | 4% | -38% |

### 10-day chart: 10 EMA under 10 SMA


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 102 | 37% | 13% | 153 | 35% | 5% | -31% |
| no | 137 | 23% | 10% | 130 | 32% | 4% | -41% |

### 10-day chart: 10 EMA crossed under 10 SMA within 2 candles


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 35 | 46% | 14% | 26 | 31% | 15% | -31% |
| no | 204 | 26% | 11% | 257 | 33% | 4% | -38% |

### 4h cliff diver in the last 10 days


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 20 | 40% | 25% | 23 | 48% | 4% | -27% |
| no | 219 | 28% | 10% | 260 | 32% | 5% | -39% |

### 3h RSI 90 in the last 10 days


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 40 | 35% | 18% | 42 | 36% | 2% | -46% |
| no | 199 | 28% | 10% | 241 | 33% | 5% | -36% |

### Daily MACD plateau


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 8 | 0% | 0% | 6 | 50% | 17% | -47% |
| no | 231 | 30% | 12% | 277 | 33% | 4% | -38% |

### Within 1 ATR of the 20-day high


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| yes | 111 | 33% | 16% | 141 | 23% | 2% | -47% |
| no | 128 | 26% | 7% | 142 | 44% | 7% | -30% |

### Broken-trend clues stacked (monthly red, weekly lower highs, 10-day cross, 4h cliff)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 | 170 | 24% | 10% | 193 | 30% | 4% | -41% |
| 1 | 45 | 36% | 16% | 74 | 39% | 5% | -28% |
| 2 | 19 | 63% | 16% | 12 | 42% | 0% | +10% |
| 3+ | 5 | 20% | 0% | 4 | 50% | 50% | -67% |

### Strength clues stacked (3h RSI 90, MACD plateau, near the 20-day high)


| Group | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0 | 113 | 27% | 7% | 131 | 41% | 6% | -31% |
| 1 | 93 | 31% | 14% | 117 | 26% | 4% | -39% |
| 2+ | 33 | 33% | 18% | 35 | 26% | 0% | -53% |

## 6. Exits: his sell vs the day's eventual low

Stock move left after his sell, to the lowest print of the rest of that session (puts). In ATR and in % of the stock price (an option on a 1-week expiry moves several times the stock %).

| Group | Trades | Median left (ATR) | Median left (% of stock) | Sold within 0.25 ATR of the day's low | Sold before the day's low printed |
|---|---|---|---|---|---|
| Winners | 164 | 0.19 | 0.42% | 45% | 57% |
| 2x+ winners | 40 | 0.17 | 0.41% | 50% | 62% |
| Losers | 358 | 0.11 | 0.25% | 23% | 19% |
| All puts | 522 | 0.13 | 0.30% | 30% | 31% |

| Period | Winners: median left (ATR) | Winners sold before the low | Losers: median left (ATR) | Losers sold before the low |
|---|---|---|---|---|
| fit | 0.18 | 54% | 0.10 | 22% |
| judged | 0.19 | 60% | 0.12 | 16% |

### How much was left after his sell


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under 0.1 ATR (sold near the low) | 94 | 19% | 7% | 103 | 25% | 4% | -43% |
| 0.1-0.5 ATR | 90 | 28% | 13% | 134 | 34% | 4% | -40% |
| 0.5-1 ATR | 28 | 54% | 18% | 27 | 56% | 11% | +15% |
| 1+ ATR left | 7 | 29% | 14% | 7 | 57% | 0% | -23% |

## 7. Winning vs losing profile (puts, all 24 months)

Share of winners vs losers that had each trait (traits picked to describe, not to rank).

| Trait at entry | Winners | Losers | 2x+ winners |
|---|---|---|---|
| Entered in the first 15 minutes | 35% | 34% | 35% |
| Entered 1 hour+ after the open | 53% | 56% | 50% |
| Price above VWAP | 41% | 42% | 45% |
| Above the prior close | 56% | 55% | 55% |
| Gapped up 0.3%+ | 37% | 37% | 42% |
| Above the daily 8 EMA | 67% | 69% | 72% |
| 5m RSI 60+ | 34% | 35% | 40% |
| 15m RSI 60+ | 38% | 37% | 48% |
| 15m TD sell 7-9 | 5% | 7% | 8% |
| 3+ levels stacked | 82% | 82% | 80% |
| Within 0.25 ATR of the high so far | 53% | 50% | 55% |
| QQQ red at entry | 45% | 44% | 48% |
| Monthly red | 15% | 9% | 10% |
| 3 weekly lower highs | 12% | 7% | 10% |
| 10-day 10 EMA under 10 SMA | 55% | 46% | 52% |
| 4h cliff diver last 10 days | 12% | 7% | 15% |
| 3h RSI 90 last 10 days | 18% | 15% | 20% |
| Within 1 ATR of the 20-day high | 42% | 51% | 52% |
| Daily grade B or better | 20% | 21% | 15% |
| H: entered before the day's high | 37% | 58% | 22% |
| B: day trade | 62% | 50% | 52% |
| B: held under 1 hour | 26% | 10% | 12% |

Median values:

| Measure | Winners | Losers | 2x+ |
|---|---|---|---|
| Minutes after the open | 82 | 84 | 56 |
| 5m RSI | 51 | 52 | 51 |
| 15m RSI | 53 | 52 | 58 |
| Distance under the high so far (ATR) | 0.23 | 0.25 | 0.22 |
| Vs VWAP (ATR) | +0.04 | +0.02 | +0.09 |
| Vs prior close (ATR) | +0.05 | +0.06 | +0.08 |
| Levels stacked | 6 | 6 | 6 |
| H: under the day's high (ATR) | 0.26 | 0.42 | 0.21 |
| B: hold (hours) | 3.4 | 12.0 | 5.4 |
| B: stock move in his favor, entry to exit (ATR) | +0.38 | -0.16 | +0.82 |

## 8. Calls (small sample)

54 calls: fit 35 trades, win 26%; judged 19 trades, win 47%. Too few to rank conditions; timing and hold shown for completeness.

### Calls: minutes after the open


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| 0-15 min | 9 | 44% | 11% | 5 | 80% | 0% | +34% |
| 15-60 min | 5 | 0% | 0% | 2 | 50% | 0% | -35% |
| 1 h+ | 21 | 24% | 5% | 12 | 33% | 0% | -19% |

### Calls: hold length


| Bucket | Fit n | Fit win | Fit 2x+ | Judged n | Judged win | Judged 2x+ | Median return (all) |
|---|---|---|---|---|---|---|---|
| under 1 h | 13 | 38% | 0% | 16 | 50% | 0% | -9% |
| 1 h to close | 6 | 17% | 17% | 3 | 33% | 0% | -32% |
| overnight+ | 16 | 19% | 6% | 0 | - | - | -47% |
