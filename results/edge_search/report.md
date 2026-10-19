# Edge search, stage 1: what survives on stock moves

2718 variations scored (signal x hold x regime x group). Edge = move after the signal minus the normal move for the same name, 5-minute slot, hold, regime and period, in % of price. Discovery 2016-2022 picks the top 25; the untouched 2023-2026 holdout decides. Survivors go to stage 2 (real option prices).

## 1. SURVIVORS

| Signal | Names | Regime | Hold | Direction | Discovery 2016-22 | Holdout 2023-26 | Verdict |
|---|---|---|---|---|---|---|---|
| none | | | | | | | |

## 2. All 6 discovery candidates (top by t) and how they did in the holdout

| Signal | Names | Regime | Hold | Direction | Discovery 2016-22 | Holdout 2023-26 | Verdict |
|---|---|---|---|---|---|---|---|
| D TD9 buy | STOCK | downtrend | 3d | CALLS (up) | +1.54% (t 4.0, n 204) | -0.43% (t -1.6, n 111) | fail |
| I 1h RSI <=25 | ETF | VIX20+ | 1d | CALLS (up) | +0.30% (t 3.8, n 1166) | +0.05% (t 1.9, n 295) | fail |
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | CALLS (up) | +0.12% (t 3.5, n 2399) | +0.21% (t 1.2, n 652) | fail |
| D inside day | STOCK | downtrend | 5d | CALLS (up) | +0.54% (t 3.3, n 1063) | -0.15% (t -0.3, n 723) | fail |
| I gap down 2% | STOCK | VIX20+ | 1d | CALLS (up) | +0.42% (t 3.2, n 1260) | -0.04% (t 1.9, n 428) | fail |
| D 20d breakdown | STOCK | VIX20+ | 1d | CALLS (up) | +0.46% (t 3.1, n 654) | -0.30% (t 0.8, n 165) | fail |

## 3. Your setups, for reference (no regime filter)

| Signal | Names | Hold | Discovery 2016-22 | Holdout 2023-26 |
|---|---|---|---|---|
| D RSI14 <=30 | ETF | 1d | +0.20% (t 1.8, n 584) | -0.01% (t 1.1, n 316) |
| D RSI14 <=30 | ETF | 3d | +0.03% (t 1.9, n 584) | +0.05% (t 2.4, n 313) |
| D RSI14 <=30 | ETF | 5d | +0.12% (t 2.8, n 584) | +0.33% (t 3.2, n 313) |
| 3h RSI >=80 | ETF | 1d | -0.09% (t -2.9, n 1780) | -0.00% (t -0.9, n 1165) |
| 3h RSI >=80 | ETF | 3d | -0.22% (t -3.3, n 1780) | -0.06% (t -2.0, n 1162) |
| 3h RSI >=80 | ETF | 5d | -0.20% (t -2.9, n 1780) | -0.31% (t -3.2, n 1159) |
| D triple break down | ETF | 1d | +0.05% (t 1.7, n 665) | +0.04% (t 1.2, n 388) |
| D triple break down | ETF | 3d | +0.01% (t 1.2, n 665) | +0.10% (t 1.5, n 385) |
| D triple break down | ETF | 5d | +0.15% (t 1.4, n 665) | +0.15% (t 1.3, n 385) |
| D SMA10/20 cross down | ETF | 1d | -0.13% (t -0.8, n 454) | -0.08% (t 0.3, n 285) |
| D SMA10/20 cross down | ETF | 3d | -0.11% (t 0.4, n 454) | -0.05% (t 0.4, n 285) |
| D SMA10/20 cross down | ETF | 5d | -0.07% (t -0.4, n 454) | -0.16% (t 0.6, n 284) |
| I live daily RSI <30 | ETF | 15m | -0.02% (t -0.6, n 447) | +0.01% (t 0.2, n 249) |
| I live daily RSI <30 | ETF | 1d | +0.05% (t 1.7, n 447) | +0.00% (t 0.3, n 248) |
| I live daily RSI <30 | ETF | 1h | -0.01% (t -0.9, n 447) | -0.00% (t 0.3, n 249) |
| I live daily RSI <30 | ETF | 2h | +0.06% (t 0.6, n 447) | +0.07% (t 1.2, n 249) |
| I live daily RSI <30 | ETF | 30m | -0.03% (t -0.9, n 447) | +0.00% (t 0.2, n 249) |
| I live daily RSI <30 | ETF | close | +0.01% (t 0.7, n 447) | +0.03% (t 0.2, n 249) |
| D 10d RSI >=80 | STOCK | 1d | -0.14% (t -0.5, n 279) | -0.04% (t 0.1, n 154) |
| D 10d RSI >=80 | STOCK | 3d | -0.19% (t -0.8, n 279) | +0.18% (t -0.2, n 154) |
| D 10d RSI >=80 | STOCK | 5d | -0.02% (t -0.0, n 279) | -0.34% (t -0.3, n 154) |

Limits: today's names (survivorship); stock moves only (stage 2 prices survivors with real options); 5-minute bars, so entries are at bar closes; regimes use the prior close. Not financial advice.
