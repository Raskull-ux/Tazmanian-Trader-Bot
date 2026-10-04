# Option Estimate Calibration

115,894 real contract-hours from Taz's Databento cache (2,895 contracts), strikes within 10% of spot, up to 30 days out.

## 1. Price level: real option price ÷ estimate

Above 1.00 = real options cost more than the estimate (IV proxy too low).

| Days to expiry | Puts: median ratio | Calls: median ratio | n |
|---|---|---|---|
| 0DTE | 0.52 | 0.38 | 12,537 |
| 1 | 0.76 | 0.69 | 15,487 |
| 2-3 | 0.81 | 0.80 | 25,618 |
| 4-7 | 0.85 | 0.86 | 31,990 |
| 8-30 | 0.85 | 0.82 | 30,262 |

## 2. Returns: real vs estimated % change (what the backtests use)

| Window | Days to expiry | n | Real avg | Estimated avg | Median error (real − est) | Correlation |
|---|---|---|---|---|---|---|
| next hour (puts) | 0DTE | 8,462 | -6.3% | -12.5% | +0.1 pts | 0.76 |
| next hour (puts) | 1 | 11,110 | -0.0% | -4.2% | +2.5 pts | 0.81 |
| next hour (puts) | 2-3 | 18,621 | +0.6% | -1.9% | +1.7 pts | 0.78 |
| next hour (puts) | 4-7 | 23,027 | +0.9% | -0.1% | +0.7 pts | 0.77 |
| next hour (puts) | 8-30 | 21,465 | +0.1% | -0.5% | +0.2 pts | 0.71 |
| rest of day (puts) | 0DTE | 1,735 | -36.2% | -48.5% | +1.1 pts | 0.84 |
| rest of day (puts) | 1 | 1,834 | -10.4% | -27.6% | +9.4 pts | 0.82 |
| rest of day (puts) | 2-3 | 3,166 | +0.8% | -12.9% | +8.0 pts | 0.85 |
| rest of day (puts) | 4-7 | 4,187 | +5.5% | -1.5% | +3.4 pts | 0.89 |
| rest of day (puts) | 8-30 | 4,409 | +0.4% | -3.4% | +1.4 pts | 0.84 |

## 3. When the estimate says a put gained 30%+, what did the real put do?

- Cases: 1,582
- Real put also gained 30%+: 88%
- Median real gain in those cases: +81%

How to read: if the median error is near 0 and correlation is high, the backtest's option numbers are trustworthy. A consistent negative error means the estimate is too optimistic and the backtests must be scaled down by about that much.
