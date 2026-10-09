# Taz's chart rules — tested

295 names, daily bars 2016 to Sep 2026. 'Puts move' = how much the stock fell vs SPY (positive = good for puts). Control = random days in the same stock. Edge = setup minus control.

## Calibration: your QQQ dates vs the triple-break rule (B fires within 2 trading days?)

- 2021-09-17: fired on Sep 20, Sep 21
- 2022-01-04: fired on Jan 05, Jan 06
- 2023-03-09: fired on Mar 10
- 2023-10-18: fired on Oct 19, Oct 20
- 2024-04-04: fired on Apr 04
- 2024-04-15: fired on Apr 15, Apr 16
- 2024-08-30: fired on Sep 03
- 2025-02-21: fired on Feb 24, Feb 25

## A. Count from the bottom

### Which bar the rally topped out on (bars 1-25 after the bottom)

| Timeframe | Bottoms | Top on bar 9-11 | Bar 12-13 | Expected if random (3 of 25 bars) | Median top bar |
|---|---|---|---|---|---|
| daily | 20149 | 9% | 6% | 12% | 16 |
| weekly | 6258 | 8% | 6% | 12% | 17 |

### Daily: puts from the close of bar k after the bottom

| Group | Count | 5 days: puts move vs SPY vs control → edge | 10 days | 20 days | Dropped 5%+ in 20 days |
|---|---|---|---|---|---|
| bars 6-8 | 60447 | -0.43% vs -0.24% → **-0.19** (t -0.9) | -0.79% vs -0.45% → **-0.34** (t -1.2) | -1.42% vs -1.02% → **-0.40** (t -1.1) | 56% vs 56% |
| **bars 9-11** | 60439 | -0.46% vs -0.28% → **-0.17** (t -0.9) | -0.73% vs -0.55% → **-0.19** (t -1.2) | -1.31% vs -1.12% → **-0.20** (t -1.2) | 55% vs 56% |
| bars 12-14 | 60333 | -0.31% vs -0.31% → **+0.00** (t 0.3) | -0.61% vs -0.56% → **-0.06** (t -0.5) | -1.21% vs -1.08% → **-0.13** (t -1.6) | 56% vs 56% |
| bars 15-20 | 120439 | -0.29% vs -0.27% → **-0.01** (t 1.3) | -0.55% vs -0.53% → **-0.02** (t 1.3) | -1.25% vs -1.08% → **-0.16** (t -0.9) | 56% vs 56% |

### Weekly: after week 11 closes red

| Case | Bottoms | Share of weeks 13-16 red | Normal red-week share | Puts week 12 → 16 |
|---|---|---|---|---|
| Week 11 red | 2717 | 47% | 47% | -2.45% |
| Week 11 green | 3541 | 46% | 46% | -1.52% |

## 2016-2021

### B. Triple MA break

| Group | Count | 5 days: puts move vs SPY vs control → edge | 10 days | 20 days | Dropped 5%+ in 20 days |
|---|---|---|---|---|---|
| All breaks (entry at break) | 22983 | -0.16% vs -0.05% → **-0.11** (t -0.8) | -0.29% vs -0.07% → **-0.21** (t -0.4) | -0.52% vs -0.14% → **-0.37** (t -0.4) | 42% vs 42% |
| All failed retests of the 10 (entry at retest) | 13307 | -0.20% vs -0.03% → **-0.17** (t -0.6) | -0.28% vs -0.10% → **-0.18** (t -0.1) | -0.67% vs -0.22% → **-0.45** (t -0.9) | 41% vs 42% |
| Break, NO golden cross in last 30 days | 21568 | -0.19% vs -0.04% → **-0.15** (t -0.9) | -0.32% vs -0.07% → **-0.25** (t -0.8) | -0.57% vs -0.14% → **-0.43** (t -0.7) | 41% vs 42% |
| Break INTO a golden cross (expect bounce) | 1415 | +0.25% vs -0.22% → **+0.48** (t 1.4) | +0.25% vs -0.14% → **+0.38** (t 1.4) | +0.22% vs -0.29% → **+0.51** (t 1.5) | 45% vs 43% |
| Next day closes lower (entry at that close) | 10367 | -0.19% vs +0.01% → **-0.19** (t -0.1) | -0.22% vs -0.01% → **-0.22** (t -0.4) | -0.60% vs -0.09% → **-0.51** (t -1.2) | 43% vs 43% |
| Next day bounces (entry at that close) | 12616 | -0.12% vs -0.08% → **-0.04** (t -0.5) | -0.32% vs -0.11% → **-0.21** (t -1.2) | -0.53% vs -0.31% → **-0.22** (t -0.6) | 40% vs 41% |
| Break, 50 SMA under the 200 | 7600 | -0.26% vs +0.18% → **-0.43** (t -1.1) | -0.25% vs +0.40% → **-0.65** (t -1.5) | -0.50% vs +0.78% → **-1.28** (t -2.1) | 44% vs 46% |
| Break, 50 SMA 0-5% above the 200 | 5359 | +0.18% vs +0.03% → **+0.15** (t 1.7) | +0.19% vs +0.06% → **+0.13** (t 2.3) | +0.27% vs +0.16% → **+0.12** (t 1.7) | 34% vs 32% |
| Break, 50 SMA 5-10% above the 200 | 4425 | -0.06% vs -0.08% → **+0.01** (t -0.7) | -0.08% vs -0.17% → **+0.08** (t 0.7) | -0.20% vs -0.32% → **+0.12** (t 0.9) | 38% vs 39% |
| Break, 50 SMA 10-20% above the 200 | 3906 | -0.34% vs -0.29% → **-0.05** (t 0.0) | -0.57% vs -0.51% → **-0.05** (t 0.1) | -0.91% vs -1.00% → **+0.09** (t 0.8) | 42% vs 44% |
| Break, 50 SMA 20%+ above the 200 | 1693 | -0.64% vs -0.68% → **+0.04** (t -1.6) | -1.83% vs -1.35% → **-0.48** (t -2.4) | -3.00% vs -2.81% → **-0.20** (t -1.2) | 62% vs 59% |
| Break, 10/20/50 bunched within 0-1% of price | 4480 | +0.06% vs +0.13% → **-0.07** (t -0.3) | +0.07% vs +0.19% → **-0.12** (t -0.3) | +0.26% vs +0.38% → **-0.12** (t -0.6) | 22% vs 24% |
| Break, 10/20/50 bunched within 1-2% of price | 5159 | -0.09% vs +0.00% → **-0.09** (t -1.2) | -0.12% vs +0.01% → **-0.13** (t -0.9) | -0.20% vs +0.05% → **-0.25** (t -1.6) | 36% vs 38% |
| Break, 10/20/50 bunched within 2-4% of price | 6716 | +0.03% vs -0.10% → **+0.12** (t 2.1) | -0.08% vs -0.12% → **+0.04** (t 0.8) | -0.42% vs -0.24% → **-0.18** (t -0.6) | 45% vs 44% |
| Break, 10/20/50 bunched within 4-+% of price | 6614 | -0.53% vs -0.16% → **-0.37** (t -0.6) | -0.83% vs -0.26% → **-0.57** (t -0.5) | -1.35% vs -0.55% → **-0.79** (t -0.4) | 56% vs 55% |

### C. Rally → quiet consolidation → volume dump

| Group | Count | 5 days: puts move vs SPY vs control → edge | 10 days | 20 days | Dropped 5%+ in 20 days |
|---|---|---|---|---|---|
| All volume dumps | 2897 | -0.25% vs -0.28% → **+0.03** (t 0.7) | -0.24% vs -0.39% → **+0.16** (t 1.2) | -0.91% vs -1.04% → **+0.13** (t 0.3) | 47% vs 48% |
| Volume 1.7-2x | 1281 | -0.53% vs -0.21% → **-0.32** (t -1.2) | -0.58% vs -0.36% → **-0.22** (t -1.0) | -1.37% vs -0.89% → **-0.48** (t -1.4) | 46% vs 47% |
| Volume 2-3x | 1197 | -0.14% vs -0.29% → **+0.14** (t 0.2) | -0.26% vs -0.41% → **+0.15** (t 0.3) | -0.85% vs -1.27% → **+0.41** (t 0.5) | 48% vs 48% |
| Volume 3x+ | 403 | +0.02% vs -0.54% → **+0.56** (t 1.5) | +0.54% vs -0.68% → **+1.22** (t 2.0) | -0.38% vs -1.14% → **+0.76** (t 0.8) | 47% vs 49% |
| Consolidation 3-5 days | 1014 | -0.26% vs -0.19% → **-0.07** (t -0.5) | -0.31% vs -0.31% → **-0.01** (t -0.4) | -0.93% vs -0.65% → **-0.28** (t -1.4) | 46% vs 49% |
| Consolidation 6-8 days | 944 | -0.22% vs -0.26% → **+0.04** (t 0.3) | -0.07% vs -0.36% → **+0.30** (t 0.1) | -0.52% vs -1.32% → **+0.80** (t 0.7) | 49% vs 48% |
| Consolidation 9-11 days | 561 | -0.12% vs -0.49% → **+0.36** (t 1.2) | -0.41% vs -0.74% → **+0.34** (t 1.2) | -1.14% vs -1.58% → **+0.43** (t 1.1) | 49% vs 48% |
| Consolidation 12-15 days | 378 | -0.50% vs -0.25% → **-0.24** (t 0.1) | -0.23% vs -0.19% → **-0.03** (t 0.9) | -1.51% vs -0.56% → **-0.94** (t -0.5) | 43% vs 45% |

## 2022-2026

### B. Triple MA break

| Group | Count | 5 days: puts move vs SPY vs control → edge | 10 days | 20 days | Dropped 5%+ in 20 days |
|---|---|---|---|---|---|
| All breaks (entry at break) | 26822 | -0.10% vs -0.08% → **-0.02** (t -1.4) | -0.24% vs -0.20% → **-0.04** (t -0.9) | -0.60% vs -0.41% → **-0.19** (t -1.2) | 52% vs 49% |
| All failed retests of the 10 (entry at retest) | 15128 | -0.14% vs -0.12% → **-0.02** (t -0.4) | -0.28% vs -0.19% → **-0.08** (t -1.4) | -0.62% vs -0.44% → **-0.18** (t 0.8) | 51% vs 50% |
| Break, NO golden cross in last 30 days | 24963 | -0.12% vs -0.10% → **-0.02** (t -1.5) | -0.24% vs -0.22% → **-0.02** (t -1.2) | -0.59% vs -0.45% → **-0.15** (t -1.3) | 53% vs 49% |
| Break INTO a golden cross (expect bounce) | 1859 | +0.07% vs +0.12% → **-0.04** (t -0.2) | -0.16% vs +0.13% → **-0.29** (t 0.2) | -0.73% vs +0.05% → **-0.78** (t -1.2) | 45% vs 48% |
| Next day closes lower (entry at that close) | 13259 | -0.19% vs -0.08% → **-0.10** (t -0.3) | -0.29% vs -0.16% → **-0.13** (t -0.3) | -0.75% vs -0.35% → **-0.40** (t -0.6) | 52% vs 50% |
| Next day bounces (entry at that close) | 13563 | -0.14% vs -0.11% → **-0.03** (t -0.7) | -0.30% vs -0.18% → **-0.12** (t -0.5) | -0.69% vs -0.42% → **-0.27** (t -0.8) | 49% vs 48% |
| Break, 50 SMA under the 200 | 11597 | -0.09% vs +0.18% → **-0.28** (t -2.9) | -0.17% vs +0.32% → **-0.49** (t -3.1) | -0.35% vs +0.68% → **-1.03** (t -4.2) | 56% vs 54% |
| Break, 50 SMA 0-5% above the 200 | 5137 | +0.08% vs +0.06% → **+0.02** (t -0.4) | +0.05% vs +0.10% → **-0.05** (t -0.8) | -0.02% vs +0.17% → **-0.19** (t -0.5) | 39% vs 36% |
| Break, 50 SMA 5-10% above the 200 | 3949 | -0.09% vs -0.10% → **+0.02** (t -1.2) | -0.12% vs -0.17% → **+0.05** (t 0.1) | -0.51% vs -0.37% → **-0.14** (t 0.0) | 45% vs 42% |
| Break, 50 SMA 10-20% above the 200 | 3749 | -0.10% vs -0.33% → **+0.22** (t 1.5) | -0.47% vs -0.62% → **+0.15** (t 1.0) | -0.80% vs -1.33% → **+0.53** (t 1.7) | 53% vs 49% |
| Break, 50 SMA 20%+ above the 200 | 2390 | -0.59% vs -1.27% → **+0.68** (t 2.8) | -1.03% vs -2.73% → **+1.70** (t 3.5) | -2.92% vs -5.58% → **+2.66** (t 3.2) | 72% vs 64% |
| Break, 10/20/50 bunched within 0-1% of price | 3673 | +0.05% vs +0.10% → **-0.05** (t -0.2) | +0.22% vs +0.19% → **+0.03** (t 1.2) | +0.39% vs +0.51% → **-0.11** (t 0.3) | 28% vs 25% |
| Break, 10/20/50 bunched within 1-2% of price | 4898 | +0.15% vs +0.06% → **+0.09** (t 0.3) | +0.22% vs +0.07% → **+0.15** (t 0.2) | +0.26% vs +0.11% → **+0.15** (t 0.4) | 44% vs 40% |
| Break, 10/20/50 bunched within 2-4% of price | 7383 | -0.03% vs -0.05% → **+0.02** (t 0.4) | -0.07% vs -0.11% → **+0.04** (t 0.7) | -0.27% vs -0.25% → **-0.03** (t 0.4) | 52% vs 48% |
| Break, 10/20/50 bunched within 4-+% of price | 10861 | -0.33% vs -0.24% → **-0.09** (t -1.1) | -0.73% vs -0.51% → **-0.21** (t -0.8) | -1.55% vs -1.08% → **-0.47** (t -0.8) | 64% vs 62% |

### C. Rally → quiet consolidation → volume dump

| Group | Count | 5 days: puts move vs SPY vs control → edge | 10 days | 20 days | Dropped 5%+ in 20 days |
|---|---|---|---|---|---|
| All volume dumps | 2601 | -0.71% vs -0.25% → **-0.46** (t -2.0) | -0.87% vs -0.70% → **-0.17** (t -0.6) | -1.68% vs -1.65% → **-0.03** (t -1.1) | 56% vs 55% |
| Volume 1.7-2x | 1201 | -0.72% vs -0.27% → **-0.44** (t -1.9) | -0.89% vs -0.56% → **-0.33** (t -1.3) | -1.95% vs -1.45% → **-0.50** (t -1.6) | 54% vs 55% |
| Volume 2-3x | 1069 | -0.78% vs -0.22% → **-0.57** (t -1.3) | -0.95% vs -0.85% → **-0.09** (t 0.3) | -1.80% vs -1.86% → **+0.07** (t -0.2) | 57% vs 56% |
| Volume 3x+ | 331 | -0.49% vs -0.31% → **-0.18** (t -0.7) | -0.55% vs -0.72% → **+0.18** (t -0.4) | -0.34% vs -1.73% → **+1.39** (t 0.8) | 58% vs 54% |
| Consolidation 3-5 days | 887 | -1.37% vs -0.33% → **-1.04** (t -3.0) | -1.70% vs -0.91% → **-0.79** (t -1.6) | -2.17% vs -1.79% → **-0.38** (t -1.1) | 56% vs 56% |
| Consolidation 6-8 days | 904 | -0.15% vs -0.08% → **-0.07** (t -0.3) | -0.36% vs -0.44% → **+0.08** (t 0.1) | -1.30% vs -1.38% → **+0.08** (t -0.4) | 57% vs 56% |
| Consolidation 9-11 days | 538 | -0.67% vs -0.34% → **-0.33** (t -0.6) | -0.67% vs -0.70% → **+0.03** (t 0.3) | -1.70% vs -1.86% → **+0.16** (t 0.7) | 55% vs 54% |
| Consolidation 12-15 days | 272 | -0.56% vs -0.43% → **-0.13** (t -0.3) | -0.22% vs -0.86% → **+0.65** (t 1.2) | -1.34% vs -1.72% → **+0.38** (t -0.1) | 53% vs 53% |

## PASS CHECK (set before running): 10-day edge > 0 with t >= 2 in BOTH periods

| Setup | 2016-2021 | 2022-2026 | Verdict |
|---|---|---|---|
| A daily bars 9-11 | -0.35, t -1.2, n 26561 | -0.06, t -0.2, n 33878 | fail |
| B break, no golden cross | -0.25, t -0.8, n 21568 | -0.02, t -1.2, n 24963 | fail |
| B failed retest | -0.18, t -0.1, n 13307 | -0.08, t -1.4, n 15128 | fail |
| C volume dump | +0.16, t 1.2, n 2897 | -0.17, t -0.6, n 2601 | fail |

Limits: today's stock list (survivorship bias against puts in older years), stock moves not option P&L.
