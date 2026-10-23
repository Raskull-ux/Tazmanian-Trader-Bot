# Finding the edge: filters chosen on 2016-21, judged on 2022-26

## cross 10/20 | outcome 2 ATR / 20 days
Setup alone: train 43.7% (n 21731), test 47.6% (n 23683)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| MACD still above signal + gapped up | 1224 | 48.5% | 1340 | **46.0%** | -1.6 pts |
| MACD still above signal + low volatility (ATR% bottom third) | 870 | 47.1% | 667 | **50.2%** | +2.6 pts |
| MACD still above signal + QQQ red that day | 1081 | 47.0% | 1205 | **46.1%** | -1.5 pts |
| volume 1.3x+ + gapped up | 1976 | 46.4% | 1754 | **45.4%** | -2.2 pts |
| low volatility (ATR% bottom third) + gapped up | 4328 | 45.9% | 3220 | **47.4%** | -0.2 pts |

Model (trained 2016-21): test AUC 0.509 | top 20% of model scores in 2022-26: 46.9% (n 4737) vs 47.6%

## cross 10/20 | outcome 1.5 ATR / 5 days
Setup alone: train 45.9% (n 15071), test 47.6% (n 15829)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| volume 1.3x+ + gapped up | 1495 | 50.0% | 1233 | **45.1%** | -2.5 pts |
| QQQ red that day + gapped up | 3553 | 49.8% | 3651 | **45.9%** | -1.7 pts |
| gapped up + near the 200 (<3 ATR) | 3911 | 48.8% | 4650 | **44.9%** | -2.7 pts |
| RSI < 40 + gapped up | 2919 | 48.8% | 3165 | **45.8%** | -1.8 pts |
| QQQ down over 5 days + gapped up | 3499 | 48.6% | 3618 | **45.3%** | -2.3 pts |

Model (trained 2016-21): test AUC 0.513 | top 20% of model scores in 2022-26: 48.3% (n 3166) vs 47.6%

## cross 10/200 | outcome 2 ATR / 20 days
Setup alone: train 43.7% (n 4280), test 44.0% (n 5222)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| high volatility (ATR% top third) + volume 1.3x+ | 479 | 55.5% | 586 | **39.6%** | -4.5 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 760 | 53.2% | 818 | **41.6%** | -2.5 pts |
| volume 1.3x+ + gapped up | 423 | 52.7% | 476 | **41.6%** | -2.4 pts |
| volume 1.3x+ + small body (<30%) | 343 | 51.9% | 325 | **44.3%** | +0.3 pts |
| stock under 50 + volume 1.3x+ | 1097 | 51.0% | 1205 | **42.1%** | -2.0 pts |

Model (trained 2016-21): test AUC 0.505 | top 20% of model scores in 2022-26: 43.6% (n 1045) vs 44.0%

## cross 10/200 | outcome 1.5 ATR / 5 days
Setup alone: train 47.2% (n 2979), test 43.4% (n 3327)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| high volatility (ATR% top third) + volume 1.3x+ | 381 | 58.0% | 395 | **41.8%** | -1.6 pts |
| volume 1.3x+ + gapped up | 341 | 55.1% | 325 | **37.2%** | -6.1 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 640 | 53.8% | 584 | **42.6%** | -0.7 pts |
| RSI < 40 + volume 1.3x+ | 815 | 52.6% | 753 | **42.6%** | -0.7 pts |
| high volatility (ATR% top third) + weaker than QQQ (5d) | 889 | 52.5% | 1055 | **45.3%** | +1.9 pts |

Model (trained 2016-21): test AUC 0.538 | top 20% of model scores in 2022-26: 47.9% (n 666) vs 43.4%

## cross 20/200 | outcome 2 ATR / 20 days
Setup alone: train 42.1% (n 3213), test 46.4% (n 3714)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| high volatility (ATR% top third) + volume 1.3x+ | 369 | 51.5% | 323 | **35.3%** | -11.1 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 494 | 51.4% | 405 | **39.3%** | -7.2 pts |
| volume 1.3x+ + small body (<30%) | 226 | 51.3% | 186 | **38.7%** | -7.7 pts |
| sector weaker than SPY (5d) + volume 1.3x+ | 340 | 50.6% | 309 | **47.6%** | +1.2 pts |
| QQQ down over 5 days + volume 1.3x+ | 478 | 50.4% | 399 | **39.1%** | -7.3 pts |

Model (trained 2016-21): test AUC 0.501 | top 20% of model scores in 2022-26: 46.4% (n 743) vs 46.4%

## cross 20/200 | outcome 1.5 ATR / 5 days
Setup alone: train 44.9% (n 2225), test 45.3% (n 2360)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| high volatility (ATR% top third) + volume 1.3x+ | 308 | 53.9% | 222 | **38.7%** | -6.6 pts |
| volume 1.3x+ + gapped up | 226 | 53.1% | 186 | **38.2%** | -7.1 pts |
| high volatility (ATR% top third) + gapped up | 362 | 53.0% | 432 | **42.8%** | -2.5 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 423 | 52.0% | 286 | **43.4%** | -1.9 pts |
| QQQ down over 5 days + volume 1.3x+ | 401 | 51.6% | 280 | **43.9%** | -1.4 pts |

Model (trained 2016-21): test AUC 0.504 | top 20% of model scores in 2022-26: 41.9% (n 472) vs 45.3%

## cross 8/20 | outcome 2 ATR / 20 days
Setup alone: train 44.4% (n 22776), test 47.8% (n 25164)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| volume 1.3x+ + gapped up | 1941 | 49.5% | 1636 | **45.1%** | -2.7 pts |
| volume 1.3x+ + near the 200 (<3 ATR) | 3814 | 48.6% | 4446 | **46.3%** | -1.5 pts |
| low volatility (ATR% bottom third) + volume 1.3x+ | 2535 | 47.8% | 1570 | **45.9%** | -1.9 pts |
| volume 1.3x+ + far over the 200 (8+ ATR) | 371 | 47.7% | 145 | **44.8%** | -3.0 pts |
| QQQ red that day + volume 1.3x+ | 3871 | 47.7% | 3601 | **46.9%** | -0.9 pts |

Model (trained 2016-21): test AUC 0.523 | top 20% of model scores in 2022-26: 50.5% (n 5033) vs 47.8%

## cross 8/20 | outcome 1.5 ATR / 5 days
Setup alone: train 47.2% (n 16014), test 47.8% (n 17200)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| volume 1.3x+ + far over the 200 (8+ ATR) | 286 | 53.5% | 110 | **42.7%** | -5.1 pts |
| volume 1.3x+ + gapped up | 1451 | 52.9% | 1176 | **43.1%** | -4.7 pts |
| QQQ red that day + volume 1.3x+ | 2991 | 51.5% | 2594 | **49.1%** | +1.3 pts |
| volume 1.3x+ + near the 200 (<3 ATR) | 2816 | 51.2% | 3183 | **49.1%** | +1.3 pts |
| MACD still above signal + volume 1.3x+ | 377 | 51.2% | 476 | **50.8%** | +3.1 pts |

Model (trained 2016-21): test AUC 0.547 | top 20% of model scores in 2022-26: 54.2% (n 3440) vs 47.8%

## cross 8/200 | outcome 2 ATR / 20 days
Setup alone: train 44.5% (n 4719), test 44.2% (n 5766)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| RSI < 40 + MACD still above signal | 179 | 52.5% | 256 | **56.6%** | +12.5 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 1056 | 50.9% | 1090 | **43.4%** | -0.8 pts |
| MACD still above signal + low volatility (ATR% bottom third) | 197 | 50.8% | 203 | **48.3%** | +4.1 pts |
| high volatility (ATR% top third) + volume 1.3x+ | 643 | 50.7% | 780 | **41.7%** | -2.5 pts |
| RSI < 40 + volume 1.3x+ | 1482 | 50.1% | 1541 | **43.2%** | -1.0 pts |

Model (trained 2016-21): test AUC 0.512 | top 20% of model scores in 2022-26: 45.5% (n 1154) vs 44.2%

## cross 8/200 | outcome 1.5 ATR / 5 days
Setup alone: train 47.0% (n 3347), test 44.8% (n 3855)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| volume 1.3x+ + gapped up | 366 | 53.0% | 384 | **46.1%** | +1.3 pts |
| high volatility (ATR% top third) + small body (<30%) | 351 | 53.0% | 371 | **46.1%** | +1.3 pts |
| RSI < 40 + high volatility (ATR% top third) | 987 | 51.7% | 1189 | **44.2%** | -0.6 pts |
| high volatility (ATR% top third) + gapped up | 410 | 51.5% | 539 | **44.0%** | -0.8 pts |
| high volatility (ATR% top third) + volume 1.3x+ | 482 | 51.2% | 502 | **45.0%** | +0.2 pts |

Model (trained 2016-21): test AUC 0.516 | top 20% of model scores in 2022-26: 45.7% (n 771) vs 44.8%

## longstair | outcome 2 ATR / 20 days
Setup alone: train 48.8% (n 525), test 49.7% (n 620)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| low volatility (ATR% bottom third) + weaker than QQQ (5d) | 166 | 54.2% | 124 | **43.5%** | -6.1 pts |
| 10 EMA under 10 SMA + low volatility (ATR% bottom third) | 179 | 54.2% | 141 | **42.6%** | -7.1 pts |
| low volatility (ATR% bottom third) | 180 | 53.9% | 142 | **43.0%** | -6.7 pts |
| stock under 8 EMA + low volatility (ATR% bottom third) | 176 | 52.8% | 141 | **43.3%** | -6.4 pts |
| stock under 50 + QQQ down over 5 days | 177 | 51.4% | 205 | **53.7%** | +4.0 pts |

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
| RSI < 40 + low volatility (ATR% bottom third) | 289 | 50.9% | 151 | **58.3%** | +8.3 pts |
| volume 1.3x+ + gapped up | 995 | 50.9% | 615 | **48.6%** | -1.3 pts |
| low volatility (ATR% bottom third) + volume 1.3x+ | 1054 | 50.8% | 532 | **49.6%** | -0.3 pts |
| stock under 8 EMA + far over the 200 (8+ ATR) | 1423 | 49.9% | 816 | **48.0%** | -1.9 pts |

Model (trained 2016-21): test AUC 0.523 | top 20% of model scores in 2022-26: 51.8% (n 1622) vs 49.9%

## macdtop | outcome 1.5 ATR / 5 days
Setup alone: train 49.2% (n 6733), test 50.5% (n 5640)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| RSI < 40 + low volatility (ATR% bottom third) | 224 | 57.6% | 115 | **57.4%** | +6.8 pts |
| RSI < 40 + gapped up | 216 | 56.9% | 168 | **51.2%** | +0.6 pts |
| stock under 8 EMA + far over the 200 (8+ ATR) | 1055 | 54.3% | 578 | **45.8%** | -4.7 pts |
| volume 1.3x+ + gapped up | 741 | 54.0% | 446 | **48.7%** | -1.9 pts |
| RSI < 40 + QQQ red that day | 388 | 53.6% | 276 | **52.5%** | +2.0 pts |

Model (trained 2016-21): test AUC 0.495 | top 20% of model scores in 2022-26: 48.2% (n 1128) vs 50.5%

## pocket | outcome 2 ATR / 20 days
Setup alone: train 42.6% (n 14282), test 46.7% (n 17757)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| high volatility (ATR% top third) + volume 1.3x+ | 661 | 50.5% | 849 | **47.0%** | +0.3 pts |
| RSI < 40 + MACD still above signal | 355 | 47.9% | 467 | **46.9%** | +0.2 pts |
| MACD still above signal + light volume <0.8x | 581 | 46.3% | 621 | **44.4%** | -2.3 pts |
| MACD still above signal + high volatility (ATR% top third) | 413 | 46.2% | 622 | **42.9%** | -3.8 pts |
| MACD still above signal + small body (<30%) | 450 | 46.2% | 543 | **48.8%** | +2.1 pts |

Model (trained 2016-21): test AUC 0.512 | top 20% of model scores in 2022-26: 47.5% (n 3552) vs 46.7%

## pocket | outcome 1.5 ATR / 5 days
Setup alone: train 45.8% (n 9370), test 48.6% (n 11657)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| high volatility (ATR% top third) + volume 1.3x+ | 481 | 52.8% | 591 | **51.8%** | +3.2 pts |
| high volatility (ATR% top third) + small body (<30%) | 879 | 49.7% | 1376 | **47.8%** | -0.7 pts |
| RSI < 40 + MACD still above signal | 215 | 49.3% | 302 | **49.7%** | +1.1 pts |
| MACD still above signal + high volatility (ATR% top third) | 250 | 49.2% | 429 | **48.5%** | -0.1 pts |
| QQQ under its 8 EMA + volume 1.3x+ | 785 | 49.0% | 884 | **49.3%** | +0.8 pts |

Model (trained 2016-21): test AUC 0.505 | top 20% of model scores in 2022-26: 47.4% (n 2332) vs 48.6%

## pocket + 8EMA tag | outcome 2 ATR / 20 days
Setup alone: train 43.2% (n 4989), test 46.5% (n 6026)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| MACD still above signal + high volatility (ATR% top third) | 211 | 52.6% | 289 | **40.8%** | -5.7 pts |
| RSI < 40 + MACD still above signal | 159 | 49.1% | 184 | **47.8%** | +1.3 pts |
| MACD still above signal + small body (<30%) | 210 | 47.1% | 230 | **45.7%** | -0.8 pts |
| 10 EMA under 10 SMA + volume 1.3x+ | 295 | 46.8% | 369 | **45.8%** | -0.7 pts |
| MACD still above signal + weaker than QQQ (5d) | 489 | 46.4% | 484 | **46.1%** | -0.4 pts |

Model (trained 2016-21): test AUC 0.529 | top 20% of model scores in 2022-26: 50.1% (n 1206) vs 46.5%

## pocket + 8EMA tag | outcome 1.5 ATR / 5 days
Setup alone: train 46.1% (n 3265), test 48.3% (n 3988)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| 10 EMA under 10 SMA + volume 1.3x+ | 205 | 51.2% | 277 | **50.2%** | +1.9 pts |
| 10 EMA under 10 SMA + light volume <0.8x | 697 | 49.9% | 863 | **48.6%** | +0.2 pts |
| RSI < 40 + light volume <0.8x | 420 | 49.8% | 484 | **45.2%** | -3.1 pts |
| low volatility (ATR% bottom third) + light volume <0.8x | 476 | 49.2% | 379 | **45.1%** | -3.2 pts |
| QQQ down over 5 days + gapped up | 816 | 48.8% | 998 | **45.3%** | -3.0 pts |

Model (trained 2016-21): test AUC 0.520 | top 20% of model scores in 2022-26: 49.0% (n 798) vs 48.3%

## pre-cross | outcome 2 ATR / 20 days
Setup alone: train 44.0% (n 37041), test 48.5% (n 39108)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| volume 1.3x+ + small body (<30%) | 1719 | 48.0% | 1631 | **42.9%** | -5.7 pts |
| volume 1.3x+ + gapped up | 2454 | 47.6% | 1873 | **47.1%** | -1.4 pts |
| low volatility (ATR% bottom third) + volume 1.3x+ | 3868 | 47.4% | 2433 | **44.1%** | -4.4 pts |
| gapped up + small body (<30%) | 1726 | 47.1% | 1667 | **48.5%** | -0.0 pts |
| RSI < 40 + volume 1.3x+ | 4690 | 47.1% | 4683 | **46.2%** | -2.3 pts |

Model (trained 2016-21): test AUC 0.516 | top 20% of model scores in 2022-26: 52.8% (n 7822) vs 48.5%

## pre-cross | outcome 1.5 ATR / 5 days
Setup alone: train 46.9% (n 25949), test 49.3% (n 26828)

| Filter (picked on 2016-21) | Train n | Train | **Test n** | **Test (2022-26)** | Test lift |
|---|---|---|---|---|---|
| RSI < 40 + gapped up | 1967 | 53.0% | 1931 | **47.5%** | -1.7 pts |
| volume 1.3x+ + gapped up | 1849 | 51.9% | 1365 | **47.9%** | -1.4 pts |
| gapped up + small body (<30%) | 1136 | 50.5% | 1104 | **48.1%** | -1.2 pts |
| QQQ red that day + gapped up | 5761 | 49.7% | 4994 | **46.6%** | -2.7 pts |
| weaker than QQQ (5d) + far over the 200 (8+ ATR) | 2695 | 49.6% | 1472 | **49.4%** | +0.1 pts |

Model (trained 2016-21): test AUC 0.525 | top 20% of model scores in 2022-26: 54.7% (n 5366) vs 49.3%

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
| low volatility (ATR% bottom third) + volume 1.3x+ | 158 | 62.7% | 95 | **48.4%** | -2.7 pts |
| volume 1.3x+ + 3+ ATR under the top | 252 | 61.9% | 147 | **55.1%** | +4.0 pts |
| QQQ down over 5 days + volume 1.3x+ | 311 | 61.4% | 210 | **50.5%** | -0.7 pts |

Model (trained 2016-21): test AUC 0.479 | top 20% of model scores in 2022-26: 48.7% (n 427) vs 51.1%

