# Combined test — strike + fast exit

931 trades: 576 with exact fill times, 355 recovered (83 narrow-window). Each cell: average return / win rate (t clustered by day, n). Returns capped at +500% per trade.

## 1. Method check (fills with known times)

- Fills checked: 55
- 15-min result at the TRUE minute, average: -2.0%
- 15-min result averaged over candidate minutes: -4.7%
- Average gap (candidate-average minus true): -2.7 pts; correlation 0.64
- A gap near 0 means candidate-averaging gives the right answer on average, even when the exact minute is unknown.

## 2. Results

### All trades

| Delta at entry | What you did | Out at 15 min | 30 min | 60 min | At the close |
|---|---|---|---|---|---|
| under 0.30 | -11.8% / 32% win (t -3.1, n 562) | +0.6% / 37% win (t -0.7, n 549) | +1.4% / 37% win (t -0.1, n 556) | -1.5% / 35% win (t -0.9, n 559) | -16.2% / 26% win (t -3.2, n 555) |
| 0.30 and up | -3.3% / 46% win (t -1.0, n 350) | -2.7% / 39% win (t -1.4, n 350) | -4.1% / 39% win (t -1.5, n 351) | -6.4% / 38% win (t -1.0, n 355) | -2.4% / 35% win (t -0.2, n 355) |

### Precise only (exact times + narrow recovered windows)

| Delta at entry | What you did | Out at 15 min | 30 min | 60 min | At the close |
|---|---|---|---|---|---|
| under 0.30 | -14.2% / 29% win (t -2.9, n 467) | -1.0% / 34% win (t -0.6, n 447) | -0.1% / 36% win (t -0.0, n 454) | -2.6% / 34% win (t -0.7, n 457) | -13.4% / 26% win (t -2.2, n 453) |
| 0.30 and up | -8.8% / 41% win (t -1.5, n 190) | -3.7% / 36% win (t -1.5, n 181) | -6.0% / 35% win (t -1.8, n 182) | -8.5% / 35% win (t -1.5, n 186) | -7.1% / 33% win (t -1.1, n 186) |

### Recovered only (Nov 2025 - Apr 2026, all accounts)

| Delta at entry | What you did | Out at 15 min | 30 min | 60 min | At the close |
|---|---|---|---|---|---|
| under 0.30 | -1.1% / 47% win (t -0.3, n 126) | +8.0% / 44% win (t 1.0, n 133) | +9.1% / 40% win (t 0.7, n 134) | +9.3% / 41% win (t 0.7, n 134) | -13.9% / 28% win (t -0.6, n 134) |
| 0.30 and up | -3.0% / 49% win (t -0.3, n 210) | -4.2% / 39% win (t -1.8, n 216) | -5.3% / 40% win (t -1.6, n 216) | -7.3% / 38% win (t -0.7, n 218) | -3.0% / 35% win (t 0.2, n 219) |

### Best run only (Nov 2025 - Apr 2026)

| Delta at entry | What you did | Out at 15 min | 30 min | 60 min | At the close |
|---|---|---|---|---|---|
| under 0.30 | -5.7% / 41% win (t -1.9, n 218) | +3.5% / 41% win (t 0.1, n 223) | +5.3% / 40% win (t 0.0, n 224) | +4.3% / 38% win (t -0.3, n 224) | -17.6% / 26% win (t -2.5, n 224) |
| 0.30 and up | -3.4% / 48% win (t -1.0, n 263) | -1.8% / 42% win (t 0.0, n 268) | -3.7% / 40% win (t -0.6, n 268) | -6.9% / 37% win (t -0.6, n 270) | -4.1% / 35% win (t -0.1, n 270) |

## 3. PRIMARY TEST (set before running): delta >= 0.30 + exit at 15 minutes

- Older half (180 trades, Apr 2024 - Mar 2026): **-3.4%** per trade
- Newer half (180 trades, Mar 2026 - Apr 2026): **-1.9%** per trade
- **Verdict: FAIL** (pass = positive in both halves)
- Same test on precise trades only: older -5.6%, newer -1.8%
- Worst-case bound (every recovered trade at its WORST candidate minute): -18.0% per trade

Notes: option prices are trade prints, not bid/ask, so real fills would be slightly worse; the 15-minute exit uses the last trade at or before 15 minutes.
