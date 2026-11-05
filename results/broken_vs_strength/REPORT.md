# Broken trend vs strength: puts on 860 names, 2016-2026

849 names, 2,039,291 name-days. Outcome: from the signal day's close, the stock falls **2 ATR before it rises 2 ATR** within 10 trading days (a same-day tie counts as a loss). Baseline = every day of every name in that period.
Fit period = 2016-2021, judged period = 2022-2026. Nothing below was tuned; the definitions were set before running.
4h and 3h clues need hourly bars: 80 names had them (Alpaca, extended hours). Days without hourly data count the 4h/3h clue as off. The first full run (4-hour limit) timed out while pulling hourly bars; this run caps the hourly pull at 45 minutes, so the 4h cliff and 3h RSI clues cover only the names above.

## Plain-English answer

Market-wide, the broken-trend clues do NOT make puts better, and shorting strength does NOT make them worse. It is the reverse, by a little:
- Monthly red, 3 weekly lower highs and the 10-day cross were 1 to 3 points WORSE than any random day for a put (2 ATR down before 2 ATR up in 10 days). Stacking them made it worse: 3+ broken clues won 26.1% in 2022-26 vs 30.7% baseline (your 75: 23.3% vs 31.6%). After a trend breaks, stocks tend to bounce before they fall another 2 ATR.
- The strength clues (3h RSI 90, MACD plateau, near the 20-day high) were slightly BETTER for puts, about +1 point; 2+ strength clues with no broken clue: +1.1 / +2.9 pts.
- The one clue that held for puts in both halves is the 4h cliff diver on your 75 names: 36.5% vs 29.4% (2016-21) and 36.9% vs 31.6% (2022-26); first day it fires: +5.5 and +14.9 pts (63 and 71 days). On all 860 it was +1.6 / +0.7, but only 80 names had hourly bars in this run.

What this means with your own trades (results/taz_deep_dive): your puts won more when the trend had broken, but the market as a whole does not. The clues are not the edge by themselves; your timing (shorting the actual top of the day, out the same session) is. Use the broken clues as a filter on your setups, and give the 4h cliff diver the most weight.

## All 860 names

| Clue | Side | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline | Held? |
|---|---|---|---|---|---|---|---|---|
| **Baseline (every day)** | | 1,056,393 | 28.8% | | 982,898 | 30.7% | | |
| Monthly red (last month and this month so far) | broken | 191,778 | 28.3% | -0.5 pts | 212,922 | 27.9% | -2.8 pts | no |
| 3 weekly lower highs | broken | 118,371 | 26.9% | -1.9 pts | 120,882 | 28.6% | -2.1 pts | yes |
| 10-day chart 10 EMA crossed under 10 SMA (within 2 candles) | broken | 137,597 | 27.5% | -1.3 pts | 127,552 | 29.1% | -1.6 pts | yes |
| 4h cliff diver in the last 10 days | broken | 5,270 | 30.4% | +1.6 pts | 6,073 | 31.4% | +0.7 pts | no |
| 3h RSI 90 in the last 10 days | strength | 10,978 | 29.6% | +0.8 pts | 9,180 | 32.0% | +1.2 pts | no |
| Daily MACD plateau | strength | 47,171 | 29.8% | +1.0 pts | 38,941 | 32.3% | +1.5 pts | no |
| Within 1 ATR of the 20-day high | strength | 349,209 | 29.0% | +0.2 pts | 282,140 | 31.9% | +1.2 pts | no |

**First day the clue turns on only** (removes the overlap of the same setup counted on many days in a row):

| Clue | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| Monthly red (last month and this month so far) | 12,290 | 30.0% | +1.2 pts | 11,598 | 30.6% | -0.1 pts |
| 3 weekly lower highs | 12,570 | 26.4% | -2.4 pts | 12,537 | 29.2% | -1.5 pts |
| 10-day chart 10 EMA crossed under 10 SMA (within 2 candles) | 7,228 | 29.1% | +0.3 pts | 6,649 | 31.0% | +0.3 pts |
| 4h cliff diver in the last 10 days | 414 | 32.9% | +4.0 pts | 483 | 39.1% | +8.4 pts |
| 3h RSI 90 in the last 10 days | 858 | 28.8% | -0.0 pts | 756 | 29.1% | -1.6 pts |
| Daily MACD plateau | 21,642 | 30.3% | +1.5 pts | 18,481 | 31.7% | +1.0 pts |
| Within 1 ATR of the 20-day high | 22,121 | 27.3% | -1.5 pts | 20,799 | 31.1% | +0.4 pts |

**Broken clues stacked** (how many of the 4 are on that day):

| Broken clues on | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| 0 | 722,740 | 29.3% | +0.4 pts | 638,616 | 31.7% | +0.9 pts |
| 1 | 232,800 | 28.1% | -0.7 pts | 238,191 | 29.8% | -0.9 pts |
| 2 | 82,393 | 27.1% | -1.7 pts | 89,074 | 27.3% | -3.4 pts |
| 3+ | 18,460 | 27.6% | -1.2 pts | 17,017 | 26.1% | -4.6 pts |

**Head to head:** broken only vs strength only vs both:

| Day type | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| 1+ broken, no strength clue | 286,094 | 28.0% | -0.8 pts | 305,740 | 28.6% | -2.1 pts |
| 2+ broken, no strength clue | 97,595 | 27.2% | -1.6 pts | 103,413 | 27.0% | -3.8 pts |
| 1+ strength, no broken clue | 331,571 | 29.3% | +0.5 pts | 270,695 | 31.9% | +1.1 pts |
| 2+ strength, no broken clue | 25,783 | 29.9% | +1.1 pts | 19,280 | 33.6% | +2.9 pts |
| both | 47,559 | 27.0% | -1.8 pts | 38,542 | 31.8% | +1.1 pts |
| neither | 391,169 | 29.2% | +0.4 pts | 367,921 | 31.5% | +0.8 pts |

## His 75 names

| Clue | Side | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline | Held? |
|---|---|---|---|---|---|---|---|---|
| **Baseline (every day)** | | 91,207 | 29.4% | | 87,774 | 31.6% | | |
| Monthly red (last month and this month so far) | broken | 15,549 | 29.8% | +0.4 pts | 19,541 | 29.1% | -2.5 pts | no |
| 3 weekly lower highs | broken | 9,385 | 27.3% | -2.1 pts | 10,640 | 27.7% | -3.8 pts | yes |
| 10-day chart 10 EMA crossed under 10 SMA (within 2 candles) | broken | 12,054 | 28.2% | -1.2 pts | 11,105 | 29.5% | -2.0 pts | yes |
| 4h cliff diver in the last 10 days | broken | 789 | 36.5% | +7.1 pts | 870 | 36.9% | +5.3 pts | yes |
| 3h RSI 90 in the last 10 days | strength | 2,276 | 28.3% | -1.1 pts | 1,831 | 34.4% | +2.8 pts | no |
| Daily MACD plateau | strength | 4,123 | 29.3% | -0.1 pts | 3,323 | 33.8% | +2.2 pts | no |
| Within 1 ATR of the 20-day high | strength | 31,397 | 29.4% | -0.1 pts | 24,413 | 32.5% | +0.9 pts | no |

**First day the clue turns on only** (removes the overlap of the same setup counted on many days in a row):

| Clue | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| Monthly red (last month and this month so far) | 1,049 | 30.9% | +1.4 pts | 1,069 | 33.0% | +1.4 pts |
| 3 weekly lower highs | 1,010 | 26.0% | -3.4 pts | 1,153 | 29.3% | -2.3 pts |
| 10-day chart 10 EMA crossed under 10 SMA (within 2 candles) | 634 | 27.8% | -1.7 pts | 577 | 30.8% | -0.7 pts |
| 4h cliff diver in the last 10 days | 63 | 34.9% | +5.5 pts | 71 | 46.5% | +14.9 pts |
| 3h RSI 90 in the last 10 days | 155 | 26.5% | -3.0 pts | 143 | 30.8% | -0.8 pts |
| Daily MACD plateau | 1,950 | 31.0% | +1.6 pts | 1,601 | 33.0% | +1.5 pts |
| Within 1 ATR of the 20-day high | 1,885 | 26.9% | -2.5 pts | 1,850 | 31.0% | -0.6 pts |

**Broken clues stacked** (how many of the 4 are on that day):

| Broken clues on | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| 0 | 63,340 | 29.6% | +0.2 pts | 56,471 | 32.6% | +1.1 pts |
| 1 | 19,426 | 29.2% | -0.2 pts | 21,844 | 30.6% | -1.0 pts |
| 2 | 6,974 | 28.2% | -1.3 pts | 8,067 | 28.4% | -3.1 pts |
| 3+ | 1,467 | 29.2% | -0.2 pts | 1,392 | 23.3% | -8.3 pts |

**Head to head:** broken only vs strength only vs both:

| Day type | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| 1+ broken, no strength clue | 23,500 | 29.2% | -0.2 pts | 27,761 | 29.4% | -2.2 pts |
| 2+ broken, no strength clue | 8,097 | 28.3% | -1.1 pts | 9,164 | 27.5% | -4.1 pts |
| 1+ strength, no broken clue | 30,247 | 29.4% | -0.1 pts | 23,871 | 32.6% | +1.0 pts |
| 2+ strength, no broken clue | 2,896 | 30.7% | +1.3 pts | 1,935 | 35.5% | +3.9 pts |
| both | 4,367 | 27.5% | -1.9 pts | 3,542 | 32.0% | +0.4 pts |
| neither | 33,093 | 29.9% | +0.4 pts | 32,600 | 32.7% | +1.1 pts |

## Notes

- The baseline here is about 30%, lower than the ~45% in older notes, because this race has 10 days, not 20; more days end with neither level hit (counted as not a win).
- Held = beats or trails the baseline in the same direction in both periods by at least 1 point.
- Name-days overlap (a clue that stays on for 10 days is counted 10 times, and their 10-day outcomes overlap), so the n is bigger than the number of independent bets. The 'first day only' table is the cleaner read.
- Run time 50 min.
