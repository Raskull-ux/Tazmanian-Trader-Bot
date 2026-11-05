# Handoff for a new Claude Code session (written Nov 4, 2026)

Taz trades options (mostly puts) on QQQ, AAPL, TSLA, HOOD, CVNA, NVDA, META. Small account, paid Discord (VIP + free).

## Working rules
- Direct, no fluff. No em dashes in anything user-facing. Never calculate his P&L.
- Test HIS definitions. Split every test 2016-21 (fit) / 2022-26 (judge). Report vs a baseline. Never trust a filter picked after looking without the held-out check.
- Chart settings: RSI 14 exponential (ewm span 14, adjust False, min_periods 14), ATR 14 Wilder (ewm alpha 1/14), 8 EMA, SMAs 10/20/50/200, MACD 12/26/9, intraday with extended hours.
- Data: yfinance works inside GitHub Actions (not locally in sandboxes). Alpaca free keys are repo secrets (APCA_API_KEY_ID / APCA_API_SECRET_KEY). Discord bot token secret DISCORD_BOT_TOKEN. The repo is PUBLIC: never commit Discord messages, personal info or secrets.
- Universe: universe/expanded_universe.csv (860 names; group == "your 75" are his names).

## What already holds up (2 ATR down before 2 ATR up in 10 days, normal ~45%)
- Staircase off a top (3+ lower highs, green higher high under the top, RSI<50): 55.7% on his 75 names.
- 4h cliff diver (big red 4h candle, body 0.5+ ATR, closes under the 4h 50 AND 200 at once, 50/200 within 0.5 ATR): 52-53%; with a heavy red volume day or a gap down under the daily 10 SMA: ~57% in both halves.
- Stacking: 6 clues live 50.8%, 7+ 52.3%.
- His own trades (results/entries_study/trades_features.csv, 324 puts on his 75 names, Apr 2024-Apr 2026): his puts WON MORE when the trend had already broken (monthly red 39% vs 27%, weekly lower highs 38% vs 27%, 10-day-chart 10 EMA under 10 SMA 39% vs 27%, recent 4h cliff 38% vs 28%) and LOST MORE shorting strength (3h RSI 90 in last 10 days 23% vs 34%, MACD plateau 14% vs 32%, near a 20-day high 27% vs 36%).
- AAPL only: gap down under the 50-day, green close under the 50 with a wick over it, next day gaps up into the 50: 8 of 9 closed red; dump days topped in the first 5 minutes at +0.1% to +1.1% over the open. The day it ran: low = 9:30 print, +2.4% over the open, 10 SMA below price.
- No edge alone: MA crosses (400 tested), 3h RSI 90, RSI backtest, volume, anchored VWAP, intraday relative strength, day-2 open behavior.

## Systems
- trade-bot/ (Cloudflare Worker + Durable Object): Taz types trades in his private Discord channel. Deploys on push via .github/workflows/deploy_trade_bot.yml. QQQ daily 8 EMA/8 SMA intraday tag alert lives in maTag() in src/index.js.
- watchlist.py + .github/workflows/watchlist.yml: evening list + 9:10 AM pre-market check, private channel.
- Research scripts in the repo root write results to results/<name>/.
