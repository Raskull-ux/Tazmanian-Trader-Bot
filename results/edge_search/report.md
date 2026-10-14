# Edge search, stage 1: what survives on stock moves

2712 variations scored (signal x hold x regime x group). Edge = move after the signal minus the normal move for the same name, 5-minute slot, hold, regime and period, in % of price. Discovery 2016-2022 picks the top 25; the untouched 2023-2026 holdout decides. Survivors go to stage 2 (real option prices).

## 1. SURVIVORS

| Signal | Names | Regime | Hold | Direction | Discovery 2016-22 | Holdout 2023-26 | Verdict |
|---|---|---|---|---|---|---|---|
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | CALLS (up) | +0.30% (t 4.2, n 802) | +0.50% (t 3.2, n 219) | **SURVIVES** |
| 3h RSI >=80 | ETF | all | 1d | PUTS (down) | -0.29% (t -3.6, n 302) | -0.15% (t -2.9, n 249) | **SURVIVES** |
| D RSI2 <=10 | ETF | VIX20+ | 1d | CALLS (up) | +0.54% (t 3.4, n 403) | +0.29% (t 2.7, n 125) | **SURVIVES** |
| I 1h RSI <=25 | STOCK | all | 2h | CALLS (up) | +0.14% (t 3.2, n 1689) | +0.21% (t 3.4, n 1033) | **SURVIVES** |

## 2. All 22 discovery candidates (top by t) and how they did in the holdout

| Signal | Names | Regime | Hold | Direction | Discovery 2016-22 | Holdout 2023-26 | Verdict |
|---|---|---|---|---|---|---|---|
| I 1h RSI <=25 | STOCK | VIX20+ | close | CALLS (up) | +0.49% (t 4.5, n 802) | +0.30% (t 2.4, n 219) | fail |
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | CALLS (up) | +0.30% (t 4.2, n 802) | +0.50% (t 3.2, n 219) | **SURVIVES** |
| I 5m RSI <=20 | STOCK | VIX20+ | 1h | CALLS (up) | +0.17% (t 4.1, n 1248) | +0.26% (t 2.1, n 367) | fail |
| D TD9 buy | STOCK | downtrend | 3d | CALLS (up) | +1.54% (t 4.0, n 204) | -0.45% (t -1.6, n 111) | fail |
| I 1h RSI <=25 | STOCK | VIX20+ | 1d | CALLS (up) | +0.61% (t 3.9, n 802) | +0.46% (t 1.6, n 219) | fail |
| I 15m RSI <=20 | STOCK | VIX20+ | 2h | CALLS (up) | +0.35% (t 3.8, n 980) | +0.48% (t 2.4, n 277) | fail |
| I 1h RSI <=25 | ETF | VIX20+ | 1d | CALLS (up) | +0.29% (t 3.7, n 371) | +0.03% (t 0.5, n 95) | fail |
| I 15m RSI <=20 | ETF | VIX20+ | 1d | CALLS (up) | +0.41% (t 3.7, n 485) | -0.40% (t -0.2, n 127) | fail |
| I 1h RSI <=25 | STOCK | all | close | CALLS (up) | +0.26% (t 3.6, n 1689) | +0.14% (t 1.8, n 1033) | fail |
| I 1h RSI <=25 | STOCK | all | 1d | CALLS (up) | +0.32% (t 3.6, n 1689) | +0.15% (t 2.1, n 1031) | fail |
| 3h RSI >=80 | ETF | all | 1d | PUTS (down) | -0.29% (t -3.6, n 302) | -0.15% (t -2.9, n 249) | **SURVIVES** |
| I 5m RSI <=20 | STOCK | VIX20+ | close | CALLS (up) | +0.26% (t 3.6, n 1248) | +0.11% (t 1.4, n 367) | fail |
| I 5m RSI <=20 | STOCK | VIX20+ | 30m | CALLS (up) | +0.10% (t 3.4, n 1248) | +0.17% (t 1.4, n 367) | fail |
| D RSI2 <=10 | ETF | VIX20+ | 1d | CALLS (up) | +0.54% (t 3.4, n 403) | +0.29% (t 2.7, n 125) | **SURVIVES** |
| 3h RSI <=20 | ETF | all | 1d | CALLS (up) | +0.69% (t 3.4, n 226) | -0.09% (t 1.2, n 103) | fail |
| D inside day | STOCK | downtrend | 5d | CALLS (up) | +0.54% (t 3.3, n 1063) | -0.15% (t -0.3, n 722) | fail |
| I live daily RSI <30 | ETF | all | 1d | CALLS (up) | +0.59% (t 3.2, n 275) | +0.10% (t 0.4, n 136) | fail |
| I 1h RSI <=25 | STOCK | all | 2h | CALLS (up) | +0.14% (t 3.2, n 1689) | +0.21% (t 3.4, n 1033) | **SURVIVES** |
| I gap down 2% | STOCK | VIX20+ | 1d | CALLS (up) | +0.42% (t 3.2, n 1260) | -0.04% (t 1.9, n 428) | fail |
| 3h RSI >=80 | ETF | uptrend | 1d | PUTS (down) | -0.26% (t -3.1, n 244) | -0.10% (t -2.4, n 236) | fail |
| D 20d breakdown | STOCK | VIX20+ | 1d | CALLS (up) | +0.46% (t 3.1, n 654) | -0.30% (t 0.8, n 165) | fail |
| I 5m RSI <=20 | STOCK | VIX20+ | 2h | CALLS (up) | +0.23% (t 3.1, n 1248) | +0.31% (t 1.9, n 367) | fail |

## 3. Your setups, for reference (no regime filter)

| Signal | Names | Hold | Discovery 2016-22 | Holdout 2023-26 |
|---|---|---|---|---|
| D RSI14 <=30 | ETF | 1d | +0.73% (t 2.9, n 168) | +0.34% (t 0.6, n 78) |
| D RSI14 <=30 | ETF | 3d | +0.20% (t 2.0, n 168) | +1.36% (t 2.5, n 78) |
| D RSI14 <=30 | ETF | 5d | +0.12% (t 2.2, n 168) | +2.09% (t 2.5, n 78) |
| 3h RSI >=80 | ETF | 1d | -0.29% (t -3.6, n 302) | -0.15% (t -2.9, n 249) |
| 3h RSI >=80 | ETF | 3d | -0.59% (t -3.0, n 302) | -0.03% (t -2.8, n 249) |
| 3h RSI >=80 | ETF | 5d | -0.56% (t -1.8, n 302) | -0.41% (t -3.2, n 249) |
| D triple break down | ETF | 1d | +0.05% (t 1.7, n 666) | +0.05% (t 1.3, n 385) |
| D triple break down | ETF | 3d | +0.01% (t 1.2, n 666) | +0.10% (t 1.5, n 385) |
| D triple break down | ETF | 5d | +0.15% (t 1.4, n 666) | +0.15% (t 1.4, n 384) |
| D SMA10/20 cross down | ETF | 1d | -0.13% (t -0.8, n 454) | -0.07% (t 0.6, n 284) |
| D SMA10/20 cross down | ETF | 3d | -0.11% (t 0.4, n 454) | -0.04% (t 0.7, n 283) |
| D SMA10/20 cross down | ETF | 5d | -0.07% (t -0.4, n 454) | -0.18% (t 0.3, n 283) |
| I live daily RSI <30 | ETF | 15m | +0.09% (t 1.4, n 275) | +0.11% (t 1.2, n 136) |
| I live daily RSI <30 | ETF | 1d | +0.59% (t 3.2, n 275) | +0.10% (t 0.4, n 136) |
| I live daily RSI <30 | ETF | 1h | +0.24% (t 1.8, n 275) | -0.00% (t 0.2, n 136) |
| I live daily RSI <30 | ETF | 2h | +0.25% (t 1.8, n 275) | +0.10% (t 0.5, n 136) |
| I live daily RSI <30 | ETF | 30m | +0.09% (t 0.8, n 275) | +0.09% (t 0.7, n 136) |
| I live daily RSI <30 | ETF | close | +0.26% (t 1.8, n 275) | -0.02% (t 0.5, n 136) |
| D 10d RSI >=80 | STOCK | 1d | -0.25% (t -1.2, n 188) | +0.16% (t 0.2, n 86) |
| D 10d RSI >=80 | STOCK | 3d | -0.06% (t -1.3, n 188) | -0.19% (t 0.4, n 86) |
| D 10d RSI >=80 | STOCK | 5d | -0.04% (t -1.0, n 188) | +0.38% (t 0.6, n 86) |

Limits: today's names (survivorship); stock moves only (stage 2 prices survivors with real options); 5-minute bars, so entries are at bar closes; regimes use the prior close. Not financial advice.
