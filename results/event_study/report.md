# Event Study — 2026-01-03 to 2026-10-04

300 names, 5-min SIP bars. Base event: rejection bar within 3 ATR of the high of day after a 2+ ATR run from the open. Option columns are Black-Scholes estimates (realized-vol IV proxy, 4% round-trip cost). Each cell: average return per trade (t-stat).

## Every event (baseline)

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| all events | 52428 | 8% hit, -9.6% (t -99.2) | 13% hit, -7.1% (t -100.0) | 8% hit, -5.6% (t -103.5) | +0.0% (t 0.9) |

## run_atr

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| run 2-4 ATR | 19176 | 8% hit, -8.8% (t -57.0) | 12% hit, -6.6% (t -59.2) | 7% hit, -5.3% (t -63.4) | +0.0% (t 1.0) |
| run 4-7 ATR | 17140 | 8% hit, -10.0% (t -56.9) | 13% hit, -7.3% (t -57.3) | 8% hit, -5.7% (t -59.2) | -0.0% (t -0.6) |
| run 7+ ATR | 16112 | 7% hit, -10.2% (t -58.1) | 14% hit, -7.6% (t -56.8) | 9% hit, -5.9% (t -56.8) | +0.0% (t 1.2) |

## consol

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| consolidation 0-2 bars | 21715 | 7% hit, -9.7% (t -65.6) | 12% hit, -7.2% (t -66.4) | 8% hit, -5.7% (t -69.5) | -0.0% (t -0.5) |
| 3-8 bars | 25651 | 8% hit, -9.7% (t -68.1) | 13% hit, -7.2% (t -68.5) | 8% hit, -5.6% (t -70.4) | +0.0% (t 1.8) |
| 9-20 bars | 5053 | 8% hit, -9.4% (t -30.1) | 13% hit, -6.8% (t -30.2) | 8% hit, -5.3% (t -31.0) | -0.0% (t -0.3) |
| 21+ bars | 9 | 0% hit, -12.1% (t -7.9) | 0% hit, -7.7% (t -10.4) | 0% hit, -6.0% (t -13.6) | +0.0% (t 0.4) |

## div_pts

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| no divergence (<0) | 17452 | 7% hit, -9.9% (t -58.1) | 13% hit, -7.4% (t -58.0) | 8% hit, -5.7% (t -59.2) | +0.0% (t 3.1) |
| divergence 0-5 | 14815 | 8% hit, -9.1% (t -50.3) | 13% hit, -6.8% (t -51.0) | 8% hit, -5.4% (t -53.9) | +0.0% (t 1.7) |
| divergence 5-10 | 10756 | 8% hit, -9.8% (t -46.1) | 12% hit, -7.2% (t -46.5) | 8% hit, -5.6% (t -47.9) | -0.0% (t -0.2) |
| divergence 10+ | 9405 | 8% hit, -9.9% (t -42.6) | 13% hit, -7.2% (t -43.6) | 8% hit, -5.6% (t -45.0) | -0.1% (t -3.3) |

## box_break

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| box break yes | 12647 | 9% hit, -9.9% (t -47.4) | 14% hit, -7.4% (t -47.3) | 9% hit, -5.7% (t -48.4) | +0.0% (t 1.9) |
| box break no | 39781 | 7% hit, -9.6% (t -87.2) | 12% hit, -7.1% (t -88.3) | 8% hit, -5.6% (t -91.8) | -0.0% (t -0.1) |

## ma_cross

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| 10/20 cross yes | 2841 | 7% hit, -8.9% (t -23.6) | 12% hit, -6.4% (t -24.1) | 8% hit, -5.2% (t -25.3) | -0.0% (t -1.0) |
| 10/20 cross no | 49587 | 8% hit, -9.7% (t -96.4) | 13% hit, -7.2% (t -97.2) | 8% hit, -5.6% (t -100.5) | +0.0% (t 1.1) |

## rsi_below_ma

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| RSI under its MA | 50914 | 8% hit, -9.7% (t -97.5) | 13% hit, -7.1% (t -98.1) | 8% hit, -5.6% (t -101.4) | +0.0% (t 0.6) |
| RSI over its MA | 1514 | 7% hit, -9.3% (t -18.4) | 9% hit, -7.1% (t -20.2) | 6% hit, -5.8% (t -21.7) | +0.1% (t 1.6) |

## ext50_atr

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| below 50 SMA | 5870 | 8% hit, -8.6% (t -34.7) | 11% hit, -6.4% (t -37.7) | 7% hit, -5.3% (t -40.7) | +0.0% (t 1.1) |
| 0-2 ATR above 50 | 19261 | 7% hit, -9.1% (t -58.4) | 11% hit, -6.8% (t -61.0) | 7% hit, -5.5% (t -65.8) | +0.0% (t 0.6) |
| 2-4 ATR above 50 | 17864 | 8% hit, -10.1% (t -58.3) | 14% hit, -7.6% (t -57.5) | 9% hit, -5.7% (t -57.4) | -0.0% (t -0.3) |
| 4+ ATR above 50 | 9433 | 9% hit, -10.5% (t -43.4) | 15% hit, -7.5% (t -41.8) | 10% hit, -5.8% (t -41.8) | +0.0% (t 0.8) |

## below200

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| under 5m 200 SMA | 11796 | 7% hit, -9.0% (t -47.3) | 11% hit, -6.8% (t -49.8) | 7% hit, -5.5% (t -54.2) | +0.0% (t 3.7) |
| over 5m 200 SMA | 40632 | 8% hit, -9.9% (t -87.3) | 13% hit, -7.3% (t -87.1) | 8% hit, -5.6% (t -88.9) | -0.0% (t -1.0) |

## room_atr

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| T1 room <2 ATR | 18189 | 9% hit, -9.4% (t -54.7) | 13% hit, -7.0% (t -57.1) | 8% hit, -5.6% (t -61.2) | -0.0% (t -1.6) |
| room 2-5 ATR | 19039 | 8% hit, -9.7% (t -59.5) | 12% hit, -7.0% (t -59.8) | 8% hit, -5.4% (t -60.6) | +0.0% (t 1.3) |
| room 5+ ATR | 14994 | 6% hit, -10.0% (t -57.6) | 13% hit, -7.5% (t -55.8) | 8% hit, -5.8% (t -56.9) | +0.0% (t 2.5) |

## above_d8

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| above daily 8 SMA | 33250 | 8% hit, -9.7% (t -78.2) | 13% hit, -7.1% (t -77.2) | 8% hit, -5.5% (t -79.2) | +0.0% (t 2.7) |
| below daily 8 SMA | 19178 | 7% hit, -9.6% (t -61.1) | 12% hit, -7.3% (t -64.0) | 7% hit, -5.8% (t -67.1) | -0.0% (t -2.0) |

## hour

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| 10:00 hour | 13282 | 11% hit, -9.3% (t -41.9) | 15% hit, -6.7% (t -44.0) | 9% hit, -5.3% (t -46.3) | -0.0% (t -1.7) |
| 11:00 hour | 16896 | 8% hit, -10.2% (t -60.6) | 11% hit, -7.2% (t -61.7) | 7% hit, -5.6% (t -64.2) | -0.0% (t -1.5) |
| 12:00 hour | 10842 | 6% hit, -10.1% (t -52.0) | 11% hit, -7.1% (t -50.1) | 7% hit, -5.6% (t -51.5) | +0.1% (t 4.2) |
| 13:00 hour | 5942 | 5% hit, -9.7% (t -37.4) | 11% hit, -7.3% (t -36.1) | 7% hit, -5.8% (t -37.4) | +0.0% (t 1.7) |
| 14:00 hour | 3733 | 4% hit, -9.1% (t -27.6) | 14% hit, -8.0% (t -26.2) | 10% hit, -6.1% (t -26.4) | +0.0% (t 1.2) |
| 15:00 hour | 1733 | 5% hit, -4.2% (t -8.8) | 22% hit, -8.0% (t -14.2) | 16% hit, -6.0% (t -13.8) | +0.1% (t 4.3) |

## Walk-forward rule (picked on events before 2026-07-04, scored after)

**Target: opt3_30_hold** — rule: below 50 SMA AND 9-20 bars AND under 5m 200 SMA

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| train, rule | 176 | 13% hit, -5.5% (t -3.2) | 18% hit, -4.4% (t -3.7) | 13% hit, -3.4% (t -3.5) | +0.3% (t 3.2) |
| TEST, rule | 97 | 3% hit, -13.7% (t -9.8) | 6% hit, -9.2% (t -8.6) | 1% hit, -8.2% (t -14.8) | -0.0% (t -0.3) |
| TEST, all events | 16764 | 6% hit, -9.9% (t -61.3) | 11% hit, -7.3% (t -59.2) | 7% hit, -5.7% (t -61.5) | +0.0% (t 4.1) |

**Target: opt1_50** — rule: 15:00 hour AND run 2-4 ATR AND divergence 0-5

| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | 7-day put +30%, hold | Stock move to 3:55 |
|---|---|---|---|---|---|
| train, rule | 93 | 2% hit, -1.8% (t -0.9) | 23% hit, -6.0% (t -2.6) | 18% hit, -3.6% (t -2.0) | +0.1% (t 1.2) |
| TEST, rule | 40 | 12% hit, -0.3% (t -0.1) | 15% hit, -15.8% (t -3.6) | 8% hit, -13.5% (t -4.3) | +0.1% (t 1.0) |
| TEST, all events | 16764 | 6% hit, -9.9% (t -61.3) | 11% hit, -7.3% (t -59.2) | 7% hit, -5.7% (t -61.5) | +0.0% (t 4.1) |

Only TEST rows count. Pass bar: TEST t ≥ 3 on the option column before going live.
