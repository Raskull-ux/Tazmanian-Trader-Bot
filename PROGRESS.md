# Progress (overnight run, Nov 4-5 2026)

Rules followed: free data only, no secrets or Discord messages in commits, no em dashes, push to main after every task.

| Task | Status | Result / where |
|---|---|---|
| 0 Taz deep dive | done | results/taz_deep_dive/REPORT.md. Broken-trend clues + 5m lower high held in both halves; A+ checklist at the end |
| 1 Broken vs strength, 860 names | running in Actions | results/broken_vs_strength/REPORT.md when the job finishes |
| 2 Gap-up 9:45 | done | results/gap_up_945/REPORT.md. First 15m back under prior close = red day 77%/74%, but from the 9:45 price it is a coin flip |
| 3 Forgiving trade bot | done, deployed | trade-bot/ (203 parser + 39 end-to-end tests) |
| 4 Clue board | done | clue_board.py + .github/workflows/clue_board.yml, weekdays 21:25 UTC, private channel, results/clue_board/ |
| 5 Gray box K1 fix | done | gray_box_bot.py saves k1/k2/ks in each list; grading uses the list's K1; log re-scored |
| 6 Filled box edges | done | results/gray_box/filled_edges.md. Filled edges no worse than open boxes; neither has an edge (all within 0.01 range of zero) |
| 7 30m gap-back rejection | done, NOT added to watchlist | results/gap_back/REPORT.md. Reached the 30m 200 first 35.9% vs 29.7% baseline (2022-24), 31.0% vs 30.0% (2025-26): did not hold in both halves |
| 8 Flipping the six | done | results/flip_six/REPORT.md. All 75 names: 60% vs 59% hit the prior close by noon (no edge). TSLA 2022-26 only: 76% vs 60% (n 33), a lean |
| 9 Clue board backtest | done | results/clue_board/BACKTEST.md. Board top 10 vs every name-day: your 75 -0.4 / -2.1 pts, 860 names -1.9 / -3.1 pts. The ranking does NOT pick better puts by itself (worse, if anything); the 'don't short' names were slightly better puts. Legend says so |
| 10 Clue board into the watchlist | done | watchlist.py reads results/clue_board/<date>.csv: 2+ broken clues moves a name up, any strength warning moves it down (inside the star tier), clue count shown on each name |
| 11 Track record | done | track_record.py + workflow: rebuilds results/track_record.csv weekdays 22:50 UTC; Sunday 22:07 UTC posts lists / triggered / hit / stopped / avg result (last 7 days and since start) |
| 12 Safe wording | done | Trade bot: entries/exits end with 'My position, not advice. Education and entertainment only.'; paper trades and the QQQ tag alert say Idea; plan posts say 'My plan, not a position yet'. Gray box, watchlist, clue board, nightly scan, morning brief ideas: labeled IDEAS with a one-line Idea footer |
| 13 Gray box 5m history | done | results/gray_box/full_5m.md. 43 names, 2024 to Oct 14 2026: avg +0.002 (2024) / +0.014 (2025-26) range per triggered trade, flat. Positive in both: PDD, AMC, META, ROKU, SMCI, MSFT, PLTR, AAPL (noise-level) |
| 14 3h 10 SMA retest, TOS anchors | done | results/three_hour/REPORT.md. Setup 43.7% / 42.9% vs every candle 41.6% / 44.0%: no edge; the anchor makes no difference |

## Choices made (no questions asked, per instructions)
- Task 5: the only list dated Oct 26 or earlier (Oct 23) actually has half-off levels at 0.5 range in the file, not 0.1. Implemented your rule as written (0.1). If you want it scored at 0.5, change K1_OLD_DEFAULT in gray_box_bot.py to 0.5. Also: grading always takes the newest saved list, and the Oct 23 list was re-graded every day Oct 26-30 because no newer lists were saved after the nightly schedule was removed.
- Task 4: "monthly red" = last month's candle red AND this month red so far (the same definition the trade study used). The 10-day candles are counted back from today so the latest one ends at today's close. The first push-run at 12:19 AM ET skipped because it compared to the calendar date; fixed to compare with the last closed session.
- Task 6 used the data_ext branch (Alpaca 5m bars already pulled, 75 names, 2016 to Oct 14 2026) instead of a new pull.
- Task 7 used the data_ext Alpaca 5m bars (extended hours) resampled to 30m instead of a new Alpaca pull (same source, ends Oct 14 2026). Gap down = open 0.3%+ under the prior close. 'Stalls at the 50' = pattern high within 0.1 daily ATR of the 30m 50 (or over it) but under the prior close, last candle closes back under the 50. Pass bar set before running: 5+ points over baseline in each half, 40+ signals.
- Task 8: 'six day' = yesterday closed on daily TD sell count 5 and today opens above yesterday's close (all 5 example days fit exactly). 'Pop' days that open below the prior close were left out because they already traded under it. Earnings = earnings date today or the trading day before (EDGAR file).
- Task 9: the 860-name run uses daily clues only (monthly, weekly, 10-day, MACD plateau, 20-day high). The 4h cliff and 3h RSI need hourly bars for 860 names since 2016, the slow Alpaca pull still running for Task 1. The 75-name run uses every clue. Top 10 = the board's own ranking each day (most broken clues, then fewest strength warnings, 1+ broken clue).
- Task 10: the boost/demote sits after the star (tested) tier and before the daily grade, so it reorders names but never outranks a starred setup. Note the Task 9 backtest: as a stand-alone screen the clues did not pick better puts, so this is a tiebreaker, not an edge. If the clue board has not run yet when the watchlist posts, names show 'clues n/a'.
- Task 11: watchlist and clue board lists are graded inside track_record.py from yfinance daily bars (watchlist uses watchlist.py's own grade_item rules). Clue board names are graded as a put on the next session (0.5 ATR down = hit, 0.5 ATR up = stopped, result = next close move in ATR). The gray box log only counts each list's next-day grade (the old Oct 23 list had been re-graded 5 days in a row).
- Task 12: post_discord.py was left as is: it posts message sets you wrote yourself in posts/. Scorecards, the morning market brief and the track record are reports, not alerts; they got 'Not advice. Education and entertainment only.' Plans are not positions yet, so they say so.
- Task 13: no new Alpaca pull was needed: the data_ext branch already holds Alpaca 5m bars with extended hours for all 43 chart_data names back to 2016 (through Oct 14 2026). Grading uses the regular session, like the live bot.
- Task 14: no earlier version of this test was in the repo, so the definitions were set before running: 3h candles anchored at 9:00 (6-9, 9-12, 12-15, 15-18, 18-20; pre-market 4-6 short) to line up with the 9-1 / 1-5 4H; far below = a close 2+ 3h ATR under the 3h 10 SMA in the last 10 candles; touch = high reaches the 10 SMA and the candle closes back under; win = 1 daily ATR down before 1 up in 5 trading days; pass bar = 3+ points over the every-candle baseline in both halves.

## What's next
- Task 1 (860-name broken vs strength) is still running in Actions (started 02:52 UTC, 4-hour limit at 06:52 UTC). If it times out, the fix is to cache the hourly pull per name and split the job; not started yet because a second run would share the same Alpaca rate limit and slow the first.
- Big picture from tonight: almost nothing mechanical held in both halves (gap-back, flip the six, 3h retest, gray box v2, filled edges, clue ranking). What held was in YOUR trades: shorting after the trend broke and at the actual top, out the same session. The edge is your selection; the bots are filters and record keepers, not signal generators.
- Worth your eyes: TSLA flip-the-six 2022-26 (76% vs 60% by noon, 33 days) and the Task 5 K1 question (Oct 23 list levels were built at 0.5).
