# Finding the edge: filters chosen on 2016-21, judged on 2022-26

## stairHH | outcome 2 ATR / 20 days
Setup alone: train 48.6% (n 2816), test 49.1% (n 3215)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| QQQ under its 8 EMA + volume 1.3x+ | 303 | 64.4% | 255 | **46.7%** | -2.4 pts |
| volume 1.3x+ + 3+ ATR under the top | 306 | 62.7% | 218 | **50.5%** | +1.4 pts |
| RSI < 40 + volume 1.3x+ | 243 | 62.6% | 189 | **50.8%** | +1.7 pts |
| QQQ down over 5 days + volume 1.3x+ | 383 | 62.1% | 301 | **49.2%** | +0.1 pts |
| volume 1.3x+ + gapped up | 378 | 60.8% | 277 | **49.8%** | +0.8 pts |

Model (trained 2016-21): test AUC 0.481 | top 20% of model scores in 2022-26: 46.7% (n 643) vs 49.1%

## stairHH | outcome 1.5 ATR / 5 days
Setup alone: train 49.9% (n 1968), test 51.1% (n 2131)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| volume 1.3x+ + gapped up | 291 | 63.9% | 195 | **52.3%** | +1.2 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 252 | 63.5% | 181 | **46.4%** | -4.7 pts |
| volume 1.3x+ + 3+ ATR under the top | 252 | 61.9% | 147 | **55.1%** | +4.0 pts |
| QQQ down over 5 days + volume 1.3x+ | 311 | 61.4% | 210 | **50.5%** | -0.7 pts |
| RSI < 40 + QQQ down over 5 days | 408 | 60.5% | 461 | **54.4%** | +3.3 pts |

Model (trained 2016-21): test AUC 0.479 | top 20% of model scores in 2022-26: 48.7% (n 427) vs 51.1%

## longstair | outcome 2 ATR / 20 days
Setup alone: train 48.8% (n 525), test 49.7% (n 620)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| stock under 50 + QQQ down over 5 days | 177 | 51.4% | 205 | **53.7%** | +4.0 pts |
| high volatility (ATR% top third) + near the 200 (<3 ATR) | 179 | 50.8% | 249 | **51.4%** | +1.7 pts |
| weaker than QQQ (5d) + sector weaker than SPY (5d) | 268 | 50.7% | 349 | **48.7%** | -1.0 pts |
| 10 EMA under 10 SMA + sector weaker than SPY (5d) | 270 | 50.4% | 352 | **49.7%** | +0.0 pts |
| sector weaker than SPY (5d) | 272 | 50.4% | 355 | **49.3%** | -0.4 pts |

Model (trained 2016-21): test AUC 0.504 | top 20% of model scores in 2022-26: 56.5% (n 124) vs 49.7%

## longstair | outcome 1.5 ATR / 5 days
Setup alone: train 49.1% (n 344), test 50.2% (n 412)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| QQQ down over 5 days + near the 200 (<3 ATR) | 153 | 51.6% | 184 | **51.6%** | +1.4 pts |
| stock under 50 + near the 200 (<3 ATR) | 159 | 51.6% | 189 | **54.5%** | +4.3 pts |
| stock under 50 | 184 | 50.5% | 223 | **54.3%** | +4.0 pts |
| stock under 50 + 10 EMA under 10 SMA | 184 | 50.5% | 220 | **54.5%** | +4.3 pts |
| stock under 8 EMA + stock under 50 | 181 | 50.3% | 222 | **54.1%** | +3.8 pts |

## macdtop | outcome 2 ATR / 20 days
Setup alone: train 45.5% (n 9720), test 49.9% (n 8107)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| RSI < 40 + gapped up | 277 | 51.3% | 220 | **48.6%** | -1.3 pts |
| volume 1.3x+ + gapped up | 995 | 50.9% | 615 | **48.6%** | -1.3 pts |
| low volatility (ATR% bottom third) + volume 1.3x+ | 856 | 50.1% | 388 | **48.2%** | -1.7 pts |
| stock under 8 EMA + far over the 200 (8+ ATR) | 1423 | 49.9% | 816 | **48.0%** | -1.9 pts |
| weaker than QQQ (5d) + far over the 200 (8+ ATR) | 2024 | 49.5% | 1127 | **49.5%** | -0.4 pts |

Model (trained 2016-21): test AUC 0.523 | top 20% of model scores in 2022-26: 51.8% (n 1622) vs 49.9%

## macdtop | outcome 1.5 ATR / 5 days
Setup alone: train 49.2% (n 6733), test 50.5% (n 5640)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| RSI < 40 + low volatility (ATR% bottom third) | 163 | 57.7% | 78 | **56.4%** | +5.9 pts |
| RSI < 40 + gapped up | 216 | 56.9% | 168 | **51.2%** | +0.6 pts |
| stock under 8 EMA + far over the 200 (8+ ATR) | 1055 | 54.3% | 578 | **45.8%** | -4.7 pts |
| volume 1.3x+ + gapped up | 741 | 54.0% | 446 | **48.7%** | -1.9 pts |
| RSI < 40 + QQQ red that day | 388 | 53.6% | 276 | **52.5%** | +2.0 pts |

Model (trained 2016-21): test AUC 0.495 | top 20% of model scores in 2022-26: 48.2% (n 1128) vs 50.5%

