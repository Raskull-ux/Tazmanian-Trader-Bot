# 10-day chart RSI: does it mark the top area? (ALL signals vs QUICK ones)

How it's scored (direction, not size): for each signal, did the stock ROLL OVER 20%+ from its later high (the high of the next 60 sessions, then the 60 sessions after it), or did it RIP 25%+ off its later low (the mirror image)? Random data does both equally often, however volatile the stock is, so only a real top tilts it. Same for 'top held 6 months' vs 'bottom held 6 months'. The signal's tilt is compared with the tilt on OVERBOUGHT days (daily RSI 70+) of the same stock, same period, same size of moves. t clustered by year.

## 1. PASS CHECK (set before running)
40+ signals; the tilt beats overbought days by 5+ points in every period with 5+ signals (at least 2 periods); t >= 3.0. Periods: 2005-15 / 2016-21 / 2022-26. QUICK = RSI was 20+ points lower within the last 3 completed 10-day candles.

| Stream | 10-day RSI | Signals | Measure | Signal: down / up | Overbought days: down / up | Tilt edge by period | t | Verdict |
|---|---|---|---|---|---|---|---|---|
| ALL | 80 | 881 | rolled over 20%+ vs ripped 25%+ | 40% / 44% | 36% / 46% | +3 pts / +5 pts / +10 pts | 4.0 | fail |
| ALL | 80 | 856 | top held 6 mo vs bottom held 6 mo | 25% / 55% | 22% / 58% | +2 pts / +10 pts / +9 pts | 1.4 | fail |
| ALL | 80 | 881 | rolled over 30%+ vs ripped 43%+ (info only) | 20% / 20% | 19% / 22% | +1 pts / +0 pts / +8 pts | 1.4 | fail |
| ALL | 85 | 350 | rolled over 20%+ vs ripped 25%+ | 43% / 52% | 39% / 51% | +6 pts / +0 pts / +2 pts | 1.8 | fail |
| ALL | 85 | 340 | top held 6 mo vs bottom held 6 mo | 24% / 55% | 23% / 62% | +9 pts / +12 pts / +3 pts | 2.1 | fail |
| ALL | 85 | 350 | rolled over 30%+ vs ripped 43%+ (info only) | 26% / 28% | 23% / 30% | +3 pts / +6 pts / +6 pts | 2.2 | fail |
| ALL | 90 | 100 | rolled over 20%+ vs ripped 25%+ | 47% / 50% | 40% / 51% | +19 pts / +1 pts / +10 pts | 2.0 | fail |
| ALL | 90 | 97 | top held 6 mo vs bottom held 6 mo | 26% / 64% | 21% / 74% | +16 pts / +13 pts / +17 pts | 2.3 | fail |
| ALL | 90 | 100 | rolled over 30%+ vs ripped 43%+ (info only) | 37% / 39% | 29% / 38% | +4 pts / +1 pts / +16 pts | 1.1 | fail |
| QUICK (1-3 candles) | 80 | 42 | rolled over 20%+ vs ripped 25%+ | 86% / 88% | 89% / 88% | — / -2 pts / +6 pts | -1.8 | fail |
| QUICK (1-3 candles) | 80 | 38 | top held 6 mo vs bottom held 6 mo | 55% / 39% | 49% / 49% | — / +10 pts / +36 pts | 0.4 | fail |
| QUICK (1-3 candles) | 80 | 42 | rolled over 30%+ vs ripped 43%+ (info only) | 81% / 69% | 78% / 70% | — / +3 pts / +17 pts | -0.9 | fail |
| QUICK (1-3 candles) | 85 | 24 | rolled over 20%+ vs ripped 25%+ | 92% / 96% | 91% / 92% | — / -1 pts / -3 pts | -1.0 | fail |
| QUICK (1-3 candles) | 85 | 22 | top held 6 mo vs bottom held 6 mo | 64% / 41% | 54% / 53% | — / +30 pts / — | 1.3 | fail |
| QUICK (1-3 candles) | 85 | 24 | rolled over 30%+ vs ripped 43%+ (info only) | 88% / 88% | 86% / 78% | — / +0 pts / -6 pts | -1.4 | fail |
| QUICK (1-3 candles) | 90 | 6 | rolled over 20%+ vs ripped 25%+ | 83% / 100% | 94% / 98% | — / -1 pts / — | nan | fail |
| QUICK (1-3 candles) | 90 | 6 | top held 6 mo vs bottom held 6 mo | 67% / 67% | 51% / 45% | — / +3 pts / — | nan | fail |
| QUICK (1-3 candles) | 90 | 6 | rolled over 30%+ vs ripped 43%+ (info only) | 83% / 100% | 86% / 87% | — / -1 pts / — | nan | fail |

## 2. Breakdown: names you can actually trade, and how fast RSI got there
INFO ONLY, no pass verdict: these are many slices of the same signals, so some will look strong by luck. Use them to see WHERE an edge sits once section 1 passes. Cost = estimated near-the-money weekly at the signal (rough Black-Scholes, not real quotes).

| Stream | 10-day RSI | Group | Signals | Rolled over 20% / ripped 25% (overbought days) | t | Top held / bottom held (overbought days) | t |
|---|---|---|---|---|---|---|---|
| ALL | 80 | under $200 weekly | 571 | 29% / 35% (27% / 36%) | 2.0 | 22% / 59% (20% / 61%) | 1.9 |
| ALL | 80 | $200-500 weekly | 173 | 54% / 55% (46% / 56%) | 1.6 | 29% / 46% (23% / 54%) | 0.7 |
| ALL | 80 | over $500 weekly | 138 | 64% / 69% (60% / 73%) | 0.4 | 37% / 50% (29% / 55%) | 0.6 |
| ALL | 85 | under $200 weekly | 222 | 35% / 43% (32% / 39%) | -0.3 | 24% / 60% (23% / 64%) | 0.6 |
| ALL | 85 | $200-500 weekly | 76 | 55% / 64% (49% / 69%) | 1.6 | 21% / 51% (22% / 62%) | 0.7 |
| ALL | 85 | over $500 weekly | 53 | 60% / 74% (56% / 78%) | 2.3 | 30% / 40% (25% / 63%) | 3.0 |
| ALL | 90 | under $200 weekly | 54 | 30% / 31% (27% / 32%) | 1.5 | 17% / 69% (19% / 78%) | 1.4 |
| ALL | 90 | $200-500 weekly | 26 | 58% / 54% (47% / 58%) | 1.9 | 36% / 60% (23% / 70%) | 1.6 |
| ALL | 90 | over $500 weekly | 20 | 80% / 95% (69% / 94%) | 0.1 | 39% / 56% (24% / 70%) | 1.5 |
| QUICK (1-3 candles) | 80 | under $200 weekly | 16 | 100% / 100% (98% / 94%) | -2.5 | 50% / 44% (59% / 49%) | -0.2 |
| QUICK (1-3 candles) | 80 | $200-500 weekly | 11 | 64% / 82% (77% / 84%) | -1.9 | 60% / 40% (40% / 54%) | nan |
| QUICK (1-3 candles) | 80 | over $500 weekly | 15 | 87% / 80% (87% / 85%) | nan | 58% / 33% (38% / 51%) | nan |
| QUICK (1-3 candles) | 85 | under $200 weekly | 7 | 100% / 100% (98% / 93%) | nan | 71% / 29% (69% / 41%) | nan |
| QUICK (1-3 candles) | 85 | $200-500 weekly | 7 | 86% / 100% (92% / 99%) | nan | 71% / 43% (59% / 57%) | nan |
| QUICK (1-3 candles) | 85 | over $500 weekly | 10 | 90% / 90% (86% / 86%) | nan | 50% / 50% (38% / 59%) | nan |

## 3. The typical path after a signal (medians)

| Stream | 10-day RSI | Signals | How deep the run-up was (gain over the last 3 candles) | Kept running to (within 60 sessions) | Days to that high | Fall from that high | 60 sessions later | 120 sessions later |
|---|---|---|---|---|---|---|---|---|
| ALL | 80 | 882 | +13% | +9.3% (overbought days +12.5%) | 40 | -16.1% (overbought days -15.6%) | +1.9% | +5.0% |
| ALL | 85 | 351 | +16% | +9.8% (overbought days +14.8%) | 37 | -17.4% (overbought days -16.8%) | +1.0% | +4.6% |
| ALL | 90 | 100 | +17% | +10.7% (overbought days +14.7%) | 38 | -18.2% (overbought days -15.8%) | +0.6% | +2.4% |
| QUICK (1-3 candles) | 80 | 42 | +119% | +44.5% (overbought days +68.1%) | 26 | -52.9% (overbought days -45.6%) | -3.5% | -3.0% |
| QUICK (1-3 candles) | 85 | 24 | +152% | +54.3% (overbought days +78.0%) | 28 | -60.0% (overbought days -47.8%) | +2.7% | -0.6% |
| QUICK (1-3 candles) | 90 | 6 | +219% | +23.0% (overbought days +79.1%) | 4 | -66.6% (overbought days -60.6%) | -33.8% | -2.9% |

## 4. Every QUICK 10-day RSI 80+ signal (first quick touch of 80 per run-up)

| Name | Signal | 10-day RSI | Jumped (RSI pts in <=3 candles) | Gain over those candles | Weekly cost (est.) | Kept running to | Days | Then fell from there | 60 sessions later | Top held 6 months |
|---|---|---|---|---|---|---|---|---|---|---|
| AMGN | 2005-08-02 | 80 | 28 | +36% | $250 | +5.2% | 34 | -15.9% | -9.0% | yes |
| REGN | 2012-01-30 | 81 | 23 | +62% | $281 | +44.0% | 57 | -16.2% | +43.0% | no |
| TSLA | 2013-05-10 | 86 | 21 | +87% | $411 | +89.9% | 60 | -9.2% | +85.2% | no |
| FCEL | 2014-03-05 | 83 | 27 | +119% | $17 | +51.4% | 4 | -60.8% | -25.2% | yes |
| DHR | 2016-07-05 | 90 | 25 | +67% | $769 | +2.8% | 40 | -8.2% | -3.3% | no |
| RIOT | 2017-10-03 | 81 | 30 | +128% | $54 | +540.4% | 54 | -84.2% | +277.4% | yes |
| TEAM | 2017-10-20 | 82 | 23 | +48% | $224 | +11.4% | 60 | -14.6% | +10.8% | no |
| VRT | 2019-12-11 | 86 | 26 | +7% | $9 | +24.5% | 41 | -65.5% | +0.5% | no |
| AXSM | 2019-12-16 | 88 | 25 | +216% | $894 | +37.8% | 9 | -67.8% | -23.3% | yes |
| FUBO | 2020-05-11 | 80 | 30 | +113% | $161 | +4.9% | 1 | -57.2% | -46.4% | no |
| DKNG | 2020-05-12 | 81 | 28 | +115% | $95 | +70.3% | 14 | -38.5% | +27.9% | no |
| NVAX | 2020-05-18 | 82 | 23 | +216% | $740 | +232.5% | 55 | -57.5% | +118.4% | no |
| FSLY | 2020-07-09 | 87 | 21 | +161% | $512 | +14.7% | 19 | -43.5% | -7.2% | no |
| MSTR | 2020-11-30 | 87 | 24 | +108% | $1,749 | +283.6% | 48 | -59.1% | +118.9% | yes |
| MRNA | 2020-11-30 | 86 | 21 | +107% | $837 | +23.9% | 47 | -38.0% | +1.4% | no |
| RIOT | 2020-12-04 | 80 | 25 | +206% | $117 | +695.0% | 49 | -74.0% | +342.9% | yes |
| MARA | 2020-12-22 | 82 | 28 | +485% | $176 | +253.7% | 37 | -62.9% | +186.3% | no |
| BIDU | 2021-01-08 | 81 | 24 | +73% | $1,080 | +47.7% | 29 | -50.9% | -7.6% | yes |
| GME | 2021-01-14 | 84 | 23 | +214% | $451 | +1110.2% | 9 | -92.0% | +253.3% | yes |
| BB | 2021-01-25 | 82 | 25 | +119% | $137 | +59.6% | 2 | -72.1% | -52.0% | yes |
| NVAX | 2021-02-05 | 81 | 20 | +141% | $3,135 | +14.3% | 2 | -55.6% | -37.7% | yes |
| RKLB | 2021-09-09 | 87 | 28 | +105% | $169 | +0.7% | 1 | -42.5% | -37.3% | yes |
| CIFR | 2021-09-10 | 80 | 32 | +33% | $51 | +16.6% | 5 | -68.0% | -52.0% | yes |
| ANET | 2021-11-03 | 80 | 22 | +50% | $1,990 | +15.7% | 36 | -27.2% | -3.2% | yes |
| IONQ | 2021-11-05 | 82 | 35 | +85% | $104 | +86.3% | 9 | -74.5% | -40.4% | yes |
| RBLX | 2021-11-19 | 81 | 28 | +81% | $1,127 | +5.1% | 1 | -62.5% | -60.0% | yes |
| AAOI | 2023-07-11 | 82 | 39 | +330% | $83 | +66.8% | 32 | -59.0% | -8.6% | no |
| SMCI | 2024-02-06 | 85 | 20 | +124% | $4,641 | +80.3% | 22 | -45.4% | +11.9% | yes |
| MSTR | 2024-03-04 | 83 | 29 | +196% | $9,203 | +49.9% | 17 | -49.5% | +21.3% | no |
| MU | 2024-04-03 | 81 | 21 | +57% | $441 | +23.1% | 53 | -46.6% | +2.7% | yes |
| LUMN | 2024-08-07 | 82 | 51 | +497% | $101 | +17.3% | 52 | -33.9% | -3.6% | no |
| IONQ | 2024-11-15 | 81 | 30 | +205% | $239 | +87.9% | 34 | -67.3% | +28.6% | yes |
| LMND | 2024-11-25 | 80 | 28 | +174% | $391 | +3.3% | 3 | -49.0% | -37.3% | no |
| AAOI | 2024-11-29 | 81 | 22 | +142% | $400 | +8.0% | 3 | -62.9% | -47.0% | yes |
| IREN | 2025-09-24 | 87 | 20 | +166% | $276 | +63.1% | 30 | -56.6% | -24.1% | yes |
| CIFR | 2025-10-08 | 81 | 20 | +152% | $112 | +45.0% | 20 | -48.7% | +3.2% | no |
| NOK | 2025-10-28 | 81 | 28 | +66% | $34 | +-1.7% | 1 | -23.3% | -11.1% | no |
| LUMN | 2025-11-03 | 81 | 20 | +99% | $64 | +-3.2% | 1 | -36.4% | -25.4% | yes |
| DE | 2026-02-19 | 81 | 24 | +36% | $1,686 | +1.2% | 2 | -17.7% | -14.9% | — |
| AAOI | 2026-03-02 | 85 | 22 | +167% | $1,141 | +127.9% | 51 | -67.5% | +75.4% | — |
| FSLY | 2026-03-10 | 80 | 33 | +174% | $259 | +53.1% | 20 | -54.9% | -12.4% | — |
| DRAM | 2026-04-02 | 86 | 46 | +832% | $1,239 | +193.0% | 54 | -45.4% | +166.0% | — |

Limits: today's most-traded names (survivorship: names that collapsed and delisted are missing, which hides some rollovers, so the real rollover rates are probably a bit higher). Daily bars for the after-signal path. Contract cost is an estimate, not real quotes. 10-day candles are on one fixed calendar; your chart's candles may start on different days, which can move the exact RSI reading a few points. Rare signals = small samples: a strong-looking result can still be luck, which is what the pass rule is for. Patterns on the 10-day chart are NOT in this run.
