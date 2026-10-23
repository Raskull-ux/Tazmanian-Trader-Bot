# The bear spot: big drops off a top vs. matched charts that didn't drop

Top-area days (within 1 ATR of the 20-day high): 406,005. DUMP = 3 ATR down before 1.5 ATR up within 10 days.
Base rates: DUMP train 15.0% / test 16.7% | RIP train 16.5% / test 17.9%

## What was different the day before a dump (dumps vs top days that didn't dump)

| Measure | Dumps (median) | No dump (median) | Holds in 2016-21 AND 2022-26? |
|---|---|---|---|
| atr_pct | 2.21 | 2.39 | yes (effect 0.11 sd) |
| macd_hist | 0.17 | 0.19 | yes (effect 0.08 sd) |
| slope_s50 | 0.36 | 0.30 | yes (effect 0.06 sd) |
| r5 | 2.66 | 3.02 | yes (effect 0.06 sd) |
| qqq_macd_hist | 0.06 | 0.08 | yes (effect 0.06 sd) |
| slope_s200 | 0.18 | 0.14 | yes (effect 0.05 sd) |
| qqq_r5 | 1.11 | 1.37 | yes (effect 0.04 sd) |
| r20 | 6.33 | 6.95 | yes (effect 0.04 sd) |
| upwick | 0.21 | 0.22 | yes (effect 0.04 sd) |
| vs_s200 | 5.20 | 4.39 | yes (effect 0.04 sd) |
| macd | 0.73 | 0.68 | yes (effect 0.03 sd) |
| s50_vs_s200 | 2.32 | 1.60 | yes (effect 0.03 sd) |
| r60 | 9.52 | 8.64 | yes (effect 0.03 sd) |
| s10_vs_s20 | 0.71 | 0.68 | yes (effect 0.03 sd) |
| from_hi52 | 1.93 | 2.46 | yes (effect 0.02 sd) |

## Model trained on 2016-21, judged on 2022-26

AUC for DUMP: 0.533 (0.50 = no skill) | same score vs RIP: 0.527

| Model score bucket (2022-26) | Days | DUMP | RIP | Dump minus rip |
|---|---|---|---|---|
| bottom 50% | 123,675 | 15.2% | 16.8% | -1.6 pts |
| 50-80% | 74,205 | 17.8% | 18.7% | -0.9 pts |
| top 20-10% | 24,735 | 18.8% | 18.3% | +0.5 pts |
| top 10-5% | 12,367 | 16.8% | 19.7% | -2.9 pts |
| top 5-1% | 9,894 | 19.5% | 21.8% | -2.4 pts |
| top 1% | 2,474 | 21.8% | 23.1% | -1.3 pts |

## Readable version: top measures as one-line rules (cut picked on 2016-21, judged on 2022-26)

| Rule | 2016-21 days | DUMP 2016-21 | 2022-26 days | **DUMP 2022-26** | RIP 2022-26 |
|---|---|---|---|---|---|
| atr_pct <= 1.48 | 31,731 | 19.3% | 32,383 | **20.5%** | 16.9% |
| macd_hist <= 0.03 | 31,731 | 16.3% | 38,931 | **18.5%** | 18.5% |
| slope_s50 >= 0.72 | 31,731 | 18.5% | 38,868 | **18.0%** | 19.4% |
| r5 <= 0.81 | 31,731 | 17.1% | 42,298 | **19.4%** | 18.3% |
| qqq_macd_hist <= -0.07 | 31,772 | 15.6% | 65,441 | **18.5%** | 19.7% |
| slope_s200 >= 0.36 | 31,731 | 21.0% | 28,254 | **20.6%** | 20.6% |
| qqq_r5 <= -0.20 | 31,836 | 14.4% | 66,842 | **19.1%** | 18.3% |
| r20 <= 2.45 | 31,731 | 15.1% | 47,501 | **18.7%** | 17.4% |
