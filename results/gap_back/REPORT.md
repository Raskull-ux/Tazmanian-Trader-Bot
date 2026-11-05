# 30m gap-back rejection: gap down, rally into the gap, stall at the 30m 50, red-green-green-red, target the 30m 200

75 names, 30m candles with extended hours, Jan 2022 to Oct 14 2026 (Alpaca 5m bars on the data_ext branch).
Win = reaches the 30m 200 SMA before trading back over the setup high (within 5 sessions). Baseline = every 30m touch of the 50 SMA from below that closed back under it, with the 200 below.

| Group | Period | Signals | Reached the 200 first | Median reward:risk (200 distance / stop distance) |
|---|---|---|---|---|
| setup | 2022-24 | 529 | 35.9% | 2.87 |
| setup | 2025-26 | 371 | 31.0% | 2.82 |
| baseline | 2022-24 | 25,216 | 29.7% | 3.14 |
| baseline | 2025-26 | 17,088 | 30.0% | 3.02 |

Same comparison inside reward:risk buckets (a far target is harder to reach, so compare like with like):

| Reward:risk | Period | Setup n | Setup win | Baseline n | Baseline win |
|---|---|---|---|---|---|
| under 1 | 2022-24 | 105 | 74% | 5,037 | 66% |
| under 1 | 2025-26 | 75 | 69% | 3,594 | 66% |
| 1-2 | 2022-24 | 96 | 47% | 4,016 | 38% |
| 1-2 | 2025-26 | 67 | 25% | 2,806 | 40% |
| 2-4 | 2022-24 | 130 | 28% | 5,535 | 26% |
| 2-4 | 2025-26 | 97 | 26% | 3,638 | 24% |
| 4+ | 2022-24 | 198 | 16% | 10,628 | 11% |
| 4+ | 2025-26 | 132 | 16% | 7,050 | 11% |

## Answer

Setup: 35.9% (2022-24) and 31.0% (2025-26) reached the 30m 200 first; baseline 29.7% and 30.0%.
**Did not hold in both halves** at the bar set before running (5+ points over the baseline in each half, 40+ signals). Not added to the watchlist alerts. Lean worth knowing: inside the same reward:risk bucket it beat the baseline in 3 of 4 buckets in both halves (all but 1-2 in 2025-26), so the pattern is not useless, but it is too thin to alert on.

By name (setup signals):

| Name | Signals | Win |
|---|---|---|
| AAPL | 10 | 20% |
| ABNB | 5 | 60% |
| AFRM | 11 | 36% |
| AMC | 3 | 0% |
| AMD | 23 | 13% |
| AMZN | 17 | 35% |
| ARKK | 16 | 56% |
| ARM | 7 | 29% |
| AVGO | 16 | 38% |
| BA | 8 | 0% |
| BABA | 19 | 11% |
| BAC | 9 | 11% |
| CANE | 5 | 0% |
| CMG | 7 | 43% |
| COIN | 19 | 58% |
| COST | 7 | 71% |
| CRM | 10 | 20% |
| CRWD | 7 | 14% |
| CRWV | 3 | 67% |
| CVNA | 9 | 22% |
| DIA | 16 | 69% |
| DIS | 16 | 50% |
| EBAY | 11 | 45% |
| GDX | 14 | 14% |
| GLD | 10 | 30% |
| GOOG | 10 | 40% |
| GOOGL | 9 | 56% |
| HOOD | 12 | 8% |
| IBM | 9 | 56% |
| INTC | 19 | 37% |
| IWM | 13 | 54% |
| JPM | 12 | 25% |
| KRE | 16 | 31% |
| LITE | 11 | 9% |
| LMT | 11 | 27% |
| LULU | 9 | 22% |
| MCD | 4 | 25% |
| META | 17 | 18% |
| MRNA | 10 | 50% |
| MSFT | 15 | 53% |
| MSTR | 17 | 53% |
| MU | 19 | 42% |
| NFLX | 10 | 50% |
| NKE | 13 | 38% |
| NVDA | 15 | 33% |
| ORCL | 11 | 27% |
| PANW | 12 | 25% |
| PDD | 17 | 6% |
| PFE | 7 | 43% |
| PLTR | 21 | 33% |
| QQQ | 13 | 38% |
| RDDT | 7 | 29% |
| RKLB | 7 | 0% |
| ROKU | 13 | 54% |
| SHOP | 11 | 45% |
| SLV | 14 | 7% |
| SMCI | 10 | 70% |
| SMH | 15 | 13% |
| SNAP | 14 | 50% |
| SNOW | 18 | 28% |
| SOFI | 14 | 36% |
| SPY | 13 | 54% |
| T | 10 | 30% |
| TLT | 19 | 26% |
| TSLA | 5 | 60% |
| UBER | 7 | 29% |
| ULTA | 9 | 22% |
| UNH | 4 | 50% |
| USO | 22 | 27% |
| WMT | 7 | 43% |
| XLE | 14 | 43% |
| XLF | 18 | 33% |
| XLK | 15 | 27% |
| XLV | 14 | 36% |
| XOM | 10 | 30% |
