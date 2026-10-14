# Exit search, stage 1: signals traded with real exits (stock levels), calls and puts

112320 combinations scored (signal x direction x names x regime x 468 exit rules). Edge = the trade's result (% of the stock price, your direction) minus a paired random trade (same 5-minute slot, period and VIX state, same target and stop distances). Discovery 2016-2022 picks the top 25, the untouched 2023-2026 holdout decides.

## 1. SURVIVORS

| Signal | Trade | Names | Regime | Exit rule | Discovery: edge / avg / target hit (t, n) | Holdout: edge / avg / target hit (t, n) | Verdict |
|---|---|---|---|---|---|---|---|
| none | | | | | | | |

## 2. All 25 discovery candidates

| Signal | Trade | Names | Regime | Exit rule | Discovery | Holdout | Verdict |
|---|---|---|---|---|---|---|---|
| I 5m RSI <=20 | CALLS | STOCK | VIX20+ | all-in; target next any level; no stop; max same day | +0.27% / +0.18% / 60% (t 4.6, n 1211) | +0.06% / +0.20% / 67% (t 1.8, n 359) | fail |
| I 5m RSI <=20 | CALLS | STOCK | VIX20+ | all-in; target next hourly S/R; no stop; max same day | +0.34% / +0.23% / 49% (t 4.6, n 1210) | +0.04% / +0.17% / 56% (t 1.5, n 359) | fail |
| I 5m RSI >=80 | CALLS | STOCK | all | split; target 2nd gap; 30m close through 2nd level against; max 3 days | +0.42% / +0.37% / 16% (t 4.5, n 1144) | -0.08% / +0.04% / 17% (t -0.1, n 773) | fail |
| I 5m RSI >=80 | CALLS | STOCK | all | split; target 2nd gap; 1h close through 2nd level against; max 3 days | +0.46% / +0.42% / 17% (t 4.4, n 1144) | -0.14% / +0.02% / 17% (t -0.5, n 773) | fail |
| I 5m RSI >=80 | CALLS | STOCK | all | split; target 2nd SMA; 30m close through 2nd level against; max 3 days | +0.34% / +0.29% / 13% (t 4.4, n 960) | +0.31% / +0.31% / 12% (t 0.6, n 620) | fail |
| I 15m RSI >=80 | PUTS | ETF | all | all-in; target next daily S/R; no stop; max 3 days | +0.22% / +0.04% / 66% (t 4.4, n 1490) | -0.05% / -0.15% / 66% (t 0.5, n 870) | fail |
| I 1h RSI <=25 | CALLS | STOCK | VIX20+ | all-in; target 2nd SMA; no stop; max same day | +0.59% / +0.54% / 1% (t 4.4, n 677) | +0.19% / +0.60% / 1% (t -0.3, n 192) | fail |
| I 15m RSI >=80 | PUTS | ETF | all | all-in; target next any level; no stop; max 3 days | +0.20% / +0.02% / 71% (t 4.4, n 1490) | -0.08% / -0.14% / 71% (t 0.0, n 870) | fail |
| I 5m RSI <=20 | CALLS | STOCK | all | all-in; target next hourly S/R; no stop; max same day | +0.16% / +0.11% / 50% (t 4.3, n 3214) | +0.04% / +0.05% / 53% (t 1.4, n 2312) | fail |
| I 5m RSI <=20 | CALLS | STOCK | VIX20+ | all-in; target next any level; 1h close through day extreme; max same day | +0.15% / +0.11% / 49% (t 4.3, n 1211) | +0.15% / +0.22% / 58% (t 1.7, n 359) | fail |
| I 1h RSI <=25 | CALLS | STOCK | all | all-in; target 2nd SMA; no stop; max same day | +0.39% / +0.31% / 1% (t 4.3, n 1281) | +0.17% / +0.20% / 0% (t 2.0, n 779) | fail |
| I 1h RSI <=25 | CALLS | ETF | all | all-in; target next gap; no stop; max next day | +0.26% / +0.19% / 36% (t 4.3, n 668) | +0.18% / +0.15% / 32% (t 1.9, n 349) | fail |
| I 15m RSI >=80 | PUTS | ETF | all | all-in; target next hourly S/R; no stop; max 3 days | +0.27% / +0.04% / 61% (t 4.2, n 1490) | -0.10% / -0.18% / 59% (t 0.4, n 870) | fail |
| I 15m RSI <=20 | CALLS | ETF | VIX20+ | all-in; target 2nd gap; no stop; max next day | +0.76% / +0.58% / 19% (t 4.2, n 306) | -0.19% / +0.34% / 16% (t -0.2, n 77) | fail |
| I 15m RSI <=20 | CALLS | ETF | VIX20+ | all-in; target next volume profile; 30m close through signal bar; max next day | +0.26% / +0.23% / 22% (t 4.2, n 465) | +0.30% / +0.44% / 18% (t 1.3, n 127) | fail |
| I 1h RSI <=25 | CALLS | ETF | all | all-in; target 2nd volume profile; no stop; max next day | +0.25% / +0.17% / 9% (t 4.1, n 734) | +0.18% / +0.17% / 8% (t 2.0, n 396) | fail |
| I 5m RSI <=20 | CALLS | STOCK | all | all-in; target 2nd any level; no stop; max same day | +0.16% / +0.12% / 48% (t 4.1, n 3212) | +0.03% / +0.04% / 49% (t 1.1, n 2313) | fail |
| I 1h RSI <=25 | CALLS | STOCK | VIX20+ | all-in; target 2nd volume profile; no stop; max same day | +0.58% / +0.52% / 3% (t 4.1, n 761) | +0.15% / +0.56% / 2% (t -0.2, n 212) | fail |
| I 15m RSI <=20 | CALLS | ETF | VIX20+ | all-in; target next volume profile; 30m close through day extreme; max next day | +0.28% / +0.25% / 24% (t 4.1, n 465) | +0.33% / +0.45% / 19% (t 1.4, n 127) | fail |
| I 1h RSI <=25 | CALLS | STOCK | all | all-in; target 2nd volume profile; no stop; max same day | +0.34% / +0.26% / 2% (t 4.0, n 1608) | +0.13% / +0.19% / 1% (t 1.5, n 993) | fail |
| I 1h RSI <=25 | CALLS | ETF | all | all-in; target 2nd hourly S/R; no stop; max next day | +0.21% / +0.15% / 32% (t 4.0, n 735) | +0.18% / +0.14% / 33% (t 2.0, n 398) | fail |
| I live triple MA break up | CALLS | STOCK | all | all-in; target next any level; 15m close through day extreme; max 3 days | +0.15% / +0.08% / 78% (t 4.0, n 2362) | -0.02% / -0.01% / 77% (t -0.5, n 1623) | fail |
| I 1h RSI <=25 | CALLS | STOCK | VIX20+ | all-in; target 2nd hourly S/R; no stop; max same day | +0.51% / +0.46% / 14% (t 4.0, n 762) | +0.19% / +0.59% / 12% (t -0.1, n 213) | fail |
| I 1h RSI <=25 | CALLS | ETF | VIX20+ | all-in; target 2nd volume profile; no stop; max next day | +0.50% / +0.45% / 10% (t 4.0, n 346) | +0.39% / +0.44% / 8% (t 1.3, n 90) | fail |
| I 1h RSI <=25 | CALLS | STOCK | all | all-in; target next volume profile; no stop; max same day | +0.30% / +0.24% / 8% (t 4.0, n 1612) | +0.12% / +0.18% / 7% (t 1.5, n 996) | fail |

## 3. Best exit rule per signal and direction in DISCOVERY (info only, many tries)

| Signal | Trade | Names | Best exit rule | Discovery edge (t) | Holdout edge (t) |
|---|---|---|---|---|---|
| I 5m RSI >=80 | CALLS | STOCK | split; target 2nd gap; 30m close through 2nd level against; max 3 days | +0.42% (t 4.5) | -0.08% (t -0.1) |
| I 5m RSI <=20 | CALLS | STOCK | all-in; target next any level; no stop; max same day | +0.14% (t 4.4) | +0.02% (t 1.0) |
| I 15m RSI >=80 | PUTS | ETF | all-in; target next daily S/R; no stop; max 3 days | +0.22% (t 4.4) | -0.05% (t 0.5) |
| I 1h RSI <=25 | CALLS | STOCK | all-in; target 2nd SMA; no stop; max same day | +0.39% (t 4.3) | +0.17% (t 2.0) |
| I 1h RSI <=25 | CALLS | ETF | all-in; target next gap; no stop; max next day | +0.26% (t 4.3) | +0.18% (t 1.9) |
| I VWAP loss | CALLS | ETF | all-in; target 2nd SMA; 30m close through day extreme; max next day | +0.05% (t 4.1) | +0.00% (t 2.1) |
| I live triple MA break up | CALLS | STOCK | all-in; target next any level; 15m close through day extreme; max 3 days | +0.15% (t 4.0) | -0.02% (t -0.5) |
| I big 5m bar down | CALLS | ETF | all-in; target 2nd gap; 1h close through signal bar; max next day | +0.07% (t 4.0) | +0.00% (t -0.4) |
| I VWAP reclaim | CALLS | STOCK | split; target 2nd SMA; 15m close through 2nd level against; max same day | +0.05% (t 3.8) | +0.03% (t 1.7) |
| I prior-day low break | PUTS | STOCK | all-in; target 2nd hourly S/R; 15m close through signal bar; max 3 days | +0.08% (t 3.7) | +0.04% (t 1.4) |
| I 5m RSI <=20 | CALLS | ETF | all-in; target next daily S/R; 30m close through signal bar; max 3 days | +0.07% (t 3.7) | -0.04% (t -1.4) |
| I live triple MA break up | CALLS | ETF | all-in; target next daily S/R; 30m close through day extreme; max same day | +0.09% (t 3.7) | -0.00% (t 0.9) |
| I 1h RSI >=75 | PUTS | ETF | all-in; target next hourly S/R; no stop; max 3 days | +0.22% (t 3.7) | +0.00% (t 1.5) |
| I ORB down fails | PUTS | STOCK | split; target 2nd volume profile; 15m close through 2nd level against; max next day | +0.11% (t 3.6) | +0.01% (t 0.7) |
| I ORB up | CALLS | STOCK | all-in; target next hourly S/R; 15m close through signal bar; max same day | +0.03% (t 3.6) | +0.01% (t 1.5) |
| I gap up fills | PUTS | STOCK | all-in; target 2nd hourly S/R; 30m close through signal bar; max 3 days | +0.13% (t 3.6) | +0.08% (t 1.9) |
| I VWAP reclaim | CALLS | ETF | split; target 2nd SMA; 15m close through 2nd level against; max same day | +0.06% (t 3.5) | +0.02% (t 0.7) |
| I 15m RSI <=20 | CALLS | ETF | all-in; target next gap; no stop; max next day | +0.28% (t 3.5) | +0.01% (t 1.0) |
| I live daily RSI >70 | PUTS | ETF | all-in; target 2nd daily S/R; no stop; max 3 days | +0.24% (t 3.4) | +0.17% (t 1.7) |
| I gap down 1% | CALLS | STOCK | all-in; target 2nd hourly S/R; 15m close through day extreme; max same day | +0.09% (t 3.4) | +0.07% (t 1.3) |
| I gap up 1% | PUTS | STOCK | all-in; target 2nd gap; 30m close through day extreme; max 3 days | +0.21% (t 3.4) | -0.03% (t 0.7) |
| I ORB up | CALLS | ETF | split; target 2nd SMA; 30m close through 2nd level against; max same day | +0.02% (t 3.3) | +0.03% (t 0.3) |
| I gap up 1% | CALLS | ETF | all-in; target next volume profile; no stop; max same day | +0.35% (t 3.2) | -0.21% (t -0.4) |
| I prior-day high break fails | PUTS | ETF | all-in; target 2nd volume profile; 15m close through level; max same day | +0.07% (t 3.2) | -0.00% (t -0.5) |
| I ORB down | PUTS | STOCK | split; target next any level; 1h close through 2nd level against; max next day | +0.04% (t 3.2) | +0.03% (t 1.9) |
| I gap down fills | CALLS | STOCK | all-in; target 2nd volume profile; no stop; max 3 days | +0.34% (t 3.1) | -0.03% (t 1.1) |
| I VWAP loss | CALLS | STOCK | all-in; target 2nd volume profile; 15m close through level; max same day | +0.04% (t 3.0) | +0.01% (t 1.1) |
| I ORB up fails | CALLS | ETF | all-in; target 2nd SMA; 15m close through signal bar; max 3 days | +0.04% (t 3.0) | +0.07% (t 2.7) |
| I big 5m bar down | CALLS | STOCK | split; target next any level; 15m close through 2nd level against; max same day | +0.03% (t 3.0) | -0.01% (t -0.9) |
| I VWAP reclaim | PUTS | STOCK | all-in; target 2nd volume profile; 15m close through signal bar; max same day | +0.03% (t 3.0) | +0.01% (t 0.9) |
| I prior-day high break | CALLS | STOCK | all-in; target 2nd daily S/R; 15m close through signal bar; max same day | +0.06% (t 2.9) | +0.02% (t 0.8) |
| I gap up fills | CALLS | STOCK | all-in; target 2nd volume profile; 15m close through signal bar; max 3 days | +0.10% (t 2.9) | +0.03% (t 0.7) |
| I live triple MA break down | PUTS | ETF | all-in; target next SMA; 15m close through level; max same day | +0.10% (t 2.9) | -0.00% (t -0.4) |
| I big 5m bar up | PUTS | STOCK | all-in; target next hourly S/R; 15m close through signal bar; max next day | +0.03% (t 2.8) | -0.01% (t -0.7) |
| I big 5m bar up | CALLS | STOCK | all-in; target 2nd SMA; no stop; max 3 days | -0.01% (t 2.8) | +0.19% (t 2.1) |
| I 15m RSI <=20 | CALLS | STOCK | all-in; target 2nd SMA; no stop; max same day | +0.22% (t 2.8) | +0.21% (t 0.7) |
| I VWAP reclaim | PUTS | ETF | all-in; target 2nd volume profile; 15m close through signal bar; max next day | +0.02% (t 2.8) | +0.01% (t 0.8) |
| I live triple MA break down | PUTS | STOCK | split; target 2nd gap; 1h close through 2nd level against; max 3 days | +0.34% (t 2.8) | -0.18% (t -0.6) |
| I gap down 2% | CALLS | STOCK | all-in; target next volume profile; 15m close through day extreme; max same day | +0.18% (t 2.7) | +0.05% (t 0.8) |
| I 15m RSI >=80 | CALLS | STOCK | split; target 2nd hourly S/R; 15m close through 2nd level against; max next day | +0.12% (t 2.7) | +0.02% (t 0.4) |

Avg = the trade's raw result (% of stock price, your direction). Target hit = share of trades that reached the target before the stop or time. Limits: today's names; 5-minute bars (target and stop in the same bar = stop); stock moves, not option prices (stage 2 prices survivors). Not financial advice.
