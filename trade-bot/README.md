# Tazmanian trade bot

Type your trade once in your private Discord channel. The bot posts the clean alert, logs it, and checks your rules.
It never places orders. Robinhood has no official API, so this only posts and logs.

## Commands (type after `/t`)
| Type | What happens |
|---|---|
| `in qqq 717p 10/23 .45 x2` | Entry alert + logged. Add `\| your read` to save a note |
| `half .90` | Sells half of the latest open trade |
| `out .70` | Closes the rest (`out qqq .70` if more than one is open) |
| `plan qqq puts 727-733 rejection stop 733` | Setup post. After 4 PM it counts for the next trading day |
| `note 1h 10 SMA close target` | Adds your read to the latest trade |
| `open` / `recap` / `log` | Open trades / today / spreadsheet file |
| `undo` | Removes the last thing logged, and deletes its post |
| `paper` / `paper off` | Labels everything PAPER |
| `live` / `test` | Post to VIP, or show only in the private channel |
| `free in ...` | Sends that one alert to the free channel (needs FREE_CHANNEL_ID) |

## Rule checks on every entry
0DTE, under a week to expiration, contract over $500, not in the plan, open after a big winner (9:30-10:00),
and 2 losses = locked (logged as a rule break, never posted).

## Results
All dollar and % results come only from the prices you type.

## Deploy
Push to `trade-bot/` or dispatch `deploy_trade_bot`. Needs repo secrets `CF_API_TOKEN` and `DISCORD_BOT_TOKEN`.
Channel and app IDs live in `wrangler.toml` (not secret).
