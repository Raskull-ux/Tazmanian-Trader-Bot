# Clue board backtest

Every day, rank names like the board (most broken clues, then fewest strength warnings) and take the top 10 with 1+ broken clue. Outcome: 2 ATR down before 2 ATR up within 10 trading days from that day's close (a same-day tie counts as a loss). Win rates near 30% are normal for this 10-day race.

## His 75 names (all clues incl. 4h cliff and 3h RSI 90)

75 names, 165,137 name-days. Clues used: monthly_red, weekly_3lh, tenday_cross, cliff_4h, rsi3h_90, macd_plateau, near_20d_high.

| Group | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| Every name-day (baseline) | 78,492 | 29.6% | +0.0 pts | 86,645 | 31.7% | +0.0 pts |
| Board top 10 (1+ broken clue) | 12,340 | 29.3% | -0.4 pts | 11,800 | 29.6% | -2.1 pts |
| Board top 10, no strength warning | 11,255 | 29.1% | -0.6 pts | 11,197 | 29.2% | -2.5 pts |
| Board top 3 | 3,871 | 29.1% | -0.6 pts | 3,570 | 29.5% | -2.2 pts |
| 2+ broken clues, no strength warning | 8,069 | 27.6% | -2.0 pts | 10,573 | 28.0% | -3.7 pts |
| Strength warning, no broken clue (the 'don't short' names) | 27,398 | 30.3% | +0.7 pts | 26,031 | 32.6% | +0.9 pts |

**Verdict:** board top 10 vs every name-day: -0.4 pts (2016-21), -2.1 pts (2022-26). Ranking by broken clues did NOT pick clearly better puts in both halves (bar: +1 point in each).

## All 860 names (daily clues only)

849 names, 2,039,291 name-days. Clues used: monthly_red, weekly_3lh, tenday_cross, macd_plateau, near_20d_high.

| Group | 2016-21 n | 2016-21 win | vs baseline | 2022-26 n | 2022-26 win | vs baseline |
|---|---|---|---|---|---|---|
| Every name-day (baseline) | 1,056,393 | 28.8% | +0.0 pts | 982,898 | 30.7% | +0.0 pts |
| Board top 10 (1+ broken clue) | 15,110 | 26.9% | -1.9 pts | 12,050 | 27.6% | -3.1 pts |
| Board top 10, no strength warning | 15,047 | 26.9% | -1.9 pts | 12,031 | 27.6% | -3.2 pts |
| Board top 3 | 4,533 | 26.4% | -2.4 pts | 3,615 | 27.1% | -3.6 pts |
| 2+ broken clues, no strength warning | 96,104 | 27.2% | -1.6 pts | 101,610 | 26.9% | -3.8 pts |
| Strength warning, no broken clue (the 'don't short' names) | 328,454 | 29.3% | +0.5 pts | 268,395 | 31.9% | +1.1 pts |

**Verdict:** board top 10 vs every name-day: -1.9 pts (2016-21), -3.1 pts (2022-26). Ranking by broken clues did NOT pick clearly better puts in both halves (bar: +1 point in each).

