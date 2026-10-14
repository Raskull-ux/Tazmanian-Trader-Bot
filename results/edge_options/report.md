# Edge search, stage 2: do the survivors make money on real options?

Real Alpaca option trades, Feb 2024 to now. Expiry a week+ out, no 0DTE. Returns per contract after an assumed cost of max($0.02, 1%) per leg each way ('stress' doubles it). Random = same trade, same clock time, a random non-signal session. t clustered by entry date.

## 1. VERDICT per survivor (set before running: any contract choice with 30+ signal days, average > 0 and above random, t >= 2.5 on both)

| Survivor (signal, names, regime, hold) | Direction | Best contract | Signal days | Avg cost | Under $500 | Avg return | Median | Win rate | Random avg | t (avg) | t (edge) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3h RSI >=80 | ETF | all | 1d | P | debit spread ATM / ~1% out | 63 | $151 | 100% | -4.5% | -17.0% | 35% | -4.0% | -0.4 | 0.1 | no |
| D RSI2 <=10 | ETF | VIX20+ | 1d | C | single 0.5% OTM | 25 | $490 | 46% | +4.7% | -2.8% | 50% | +2.3% | 1.1 | 0.9 | too few |
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | C | debit spread ATM / ~1% out | 44 | $149 | 100% | -7.5% | -13.4% | 23% | -13.6% | -1.2 | 1.3 | no |
| I 1h RSI <=25 | STOCK | all | 2h | C | single ATM | 80 | $578 | 58% | +0.8% | +1.1% | 51% | -1.3% | 0.1 | 0.6 | no |

## 2. Every contract choice

| Survivor | Contract | Trades | Signal days | Avg cost | Under $500 | Avg return | Median | Win rate | Stress avg | Random avg | Edge | t (avg) | t (edge) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3h RSI >=80 | ETF | all | 1d | debit spread ATM / ~1% out | 80 | 63 | $151 | 100% | -4.5% | -17.0% | 35% | -16.1% | -4.0% | -0.5 | -0.4 | 0.1 |
| 3h RSI >=80 | ETF | all | 1d | single 0.5% OTM | 97 | 76 | $275 | 88% | -2.7% | -15.8% | 36% | -6.8% | +5.0% | -7.6 | -0.0 | -0.7 |
| 3h RSI >=80 | ETF | all | 1d | single ATM | 87 | 68 | $370 | 74% | -1.0% | -12.7% | 40% | -4.0% | +5.4% | -6.3 | -0.0 | -0.8 |
| D RSI2 <=10 | ETF | VIX20+ | 1d | debit spread ATM / ~1% out | 47 | 26 | $209 | 100% | -6.6% | -4.3% | 40% | -17.6% | -5.8% | -0.8 | -1.0 | -0.2 |
| D RSI2 <=10 | ETF | VIX20+ | 1d | single 0.5% OTM | 54 | 25 | $490 | 46% | +4.7% | -2.8% | 50% | +1.6% | +2.3% | +2.4 | 1.1 | 0.9 |
| D RSI2 <=10 | ETF | VIX20+ | 1d | single ATM | 57 | 28 | $553 | 46% | +7.0% | +3.0% | 54% | +4.2% | +0.5% | +6.5 | 0.9 | 0.8 |
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | debit spread ATM / ~1% out | 97 | 44 | $149 | 100% | -7.5% | -13.4% | 23% | -23.7% | -13.6% | +6.1 | -1.2 | 1.3 |
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | single 0.5% OTM | 105 | 44 | $465 | 70% | +0.9% | +1.2% | 51% | -1.6% | -0.2% | +1.1 | -0.3 | -0.2 |
| I 1h RSI <=25 | STOCK | VIX20+ | 2h | single ATM | 105 | 44 | $543 | 57% | +1.4% | +1.8% | 54% | -1.0% | +0.0% | +1.4 | 0.3 | 0.3 |
| I 1h RSI <=25 | STOCK | all | 2h | debit spread ATM / ~1% out | 93 | 74 | $145 | 99% | -14.3% | -11.7% | 25% | -28.4% | -10.8% | -3.5 | -5.4 | -1.4 |
| I 1h RSI <=25 | STOCK | all | 2h | single 0.5% OTM | 100 | 81 | $485 | 67% | +0.1% | -2.8% | 42% | -2.6% | -2.0% | +2.0 | -0.1 | 0.5 |
| I 1h RSI <=25 | STOCK | all | 2h | single ATM | 99 | 80 | $578 | 58% | +0.8% | +1.1% | 51% | -1.6% | -1.3% | +2.1 | 0.1 | 0.6 |

Limits: Feb 2024 onward only; trade prints, not bid/ask (cost line is an assumption); up to 120 signals per survivor. Not financial advice.
