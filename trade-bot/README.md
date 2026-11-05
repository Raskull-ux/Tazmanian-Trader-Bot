# Tazmanian trade bot

Type your trade once in your private Discord channel. The bot posts the clean alert, logs it, and checks your rules.
It never places orders. Robinhood has no official API, so this only posts and logs.

## Commands (just type them in the private channel, any word order, typos are fine)
| Type | What happens |
|---|---|
| `in aapl 345p 10/30 .39 x2` | Entry alert + logged. Same as `aapl 345p 10/30 .39 in`, `345 put aapl 10/30 @ .39`, `in .39 aapl oct30 345p 2 contracts`. Add `\| your read` for a note |
| `in aapl 345/340p 11/13 .79` | Spread, logged as one position (long 345P / short 340P, net debit). Also `bear put 345 340`, `345p 340p`, `345-340 p`, `credit` for credit spreads |
| `out 1.22` / `out aapl 1.22` / `out aapl 345 10/26 put 1.22` | Closes. The price is the money-looking number; strike and date only pick the position |
| `half .80` / `trim 50% .80` / `sold half at .8` | Sells half |
| `y` / a number / the missing piece | Answers the bot's question: confirm a guess, pick from a numbered list, or send `11/13`, `.45`, `c` |
| `fix price 1.22` / `fix strike 345` / `fix exp 11/13` / `fix qty 2` | Edits the last trade or sell, and its Discord post |
| `undo` / `delete 8` | Removes the last thing logged / trade #8 (and their posts) |
| `cleanup` | Lists the stuck positions from the old parser bug (#2, #3, #7, #8); `y` removes them |
| `plan qqq puts 727-733 rejection stop 733` | Setup post. After 4 PM it counts for the next trading day |
| `note 1h 10 SMA close target` | Adds your read to the latest trade |
| `open` / `recap` / `log` | Open trades / today / spreadsheet file |
| `paper` / `paper off` | Labels everything PAPER |
| `live` / `test` | Post to VIP, or show only in the private channel |
| `free in ...` | Sends that one alert to the free channel (needs FREE_CHANNEL_ID) |

Nothing is rejected outright. If a piece is missing the bot shows its best read with a ❓ and waits:
"Got AAPL 345P: no expiry, so I used the nearest Friday a week out: 11/13. Reply y to log it, or send the fix."
If several open trades match an exit it lists them numbered; reply `1`, `2`, ... Questions expire after 30 minutes.

## Tests
`npm test` runs the parser tests (every example above plus 30+ real sloppy messages) and an end-to-end test of the
bot on a real SQLite database with Discord mocked. The deploy workflow runs them and stops if any fail.

## Rule checks on every entry
0DTE, under a week to expiration, contract over $500, not in the plan, open after a big winner (9:30-10:00),
and 2 losses = locked (logged as a rule break, never posted).

## Results
All dollar and % results come only from the prices you type.

## Deploy
Push to `trade-bot/` or dispatch `deploy_trade_bot`. Needs repo secrets `CF_API_TOKEN` and `DISCORD_BOT_TOKEN`.
Channel and app IDs live in `wrangler.toml` (not secret).
