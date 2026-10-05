# Recovered fill times — Nov 2025 to Apr 2026

Spent this run: $9.87 (cap $10).

## 1. Accuracy check on fills whose real time is known

- Fills checked: 169 (of 169)
- Recovered time within 5 min of the real time: 36%
- Within 15 min: 45% | within 30 min: 56%
- Median error: 21 min
- Real time inside the recovered window: 100%
- Among fills whose window was narrow (all candidate minutes within 15 min): 91% within 5 min, n=32

## 2. Recovered fills (no time on record)

| Account | Fills | Found | Narrow window (<=15 min) | Wide window |
|---|---|---|---|---|
| Bebo | 29 | 29 | 9 | 20 |
| Robinhood-main | 190 | 190 | 39 | 151 |
| Webull | 395 | 395 | 86 | 309 |

Not found: 0 ({})

Use rule (set before running): recovered times are used in the next tests only if the accuracy check shows a median error of 15 minutes or less; narrow-window fills first.
