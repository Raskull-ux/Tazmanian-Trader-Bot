"""Post a prepared Discord message set: every .md file in POST_DIR, in name order, one message each.
WHERE = vip | private. @everyone pings only when the text contains it and the bot has the Mention Everyone permission."""
import os, glob, time, requests
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CH = {"vip": "1412516610845184123", "private": "1562327911866830949"}[os.environ.get("WHERE", "private")]
files = sorted(glob.glob(os.path.join(os.environ["POST_DIR"], "*.md")))
assert files, "no message files"
for f in files:
    text = open(f, encoding="utf-8").read().strip()
    assert len(text) <= 2000, f"{f} is over 2000 characters"
    r = requests.post(f"https://discord.com/api/v10/channels/{CH}/messages", headers={"Authorization": f"Bot {TOKEN}"},
                      json={"content": text, "allowed_mentions": {"parse": ["everyone"]}}, timeout=20)
    print(f"::notice::{os.path.basename(f)} -> {r.status_code} {r.text[:200] if r.status_code >= 300 else ''}")
    r.raise_for_status(); time.sleep(1.5)
