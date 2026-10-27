"""Read-only: today's messages from the private and VIP channels, printed as run annotations (nothing saved to the repo)."""
import os, requests, datetime as dt
T = os.environ["DISCORD_BOT_TOKEN"]; H = {"Authorization": f"Bot {T}"}
DAY = os.environ.get("DAY") or dt.datetime.now(dt.timezone(dt.timedelta(hours=-4))).strftime("%Y-%m-%d")
out = []
for name, ch in (("PRIVATE", "1562327911866830949"), ("VIP", "1412516610845184123")):
    r = requests.get(f"https://discord.com/api/v10/channels/{ch}/messages", headers=H, params={"limit": 100}, timeout=20)
    if r.status_code != 200: out.append(f"{name} error {r.status_code}"); continue
    for m in reversed(r.json()):
        t = dt.datetime.fromisoformat(m["timestamp"]).astimezone(dt.timezone(dt.timedelta(hours=-4)))
        if t.strftime("%Y-%m-%d") != DAY: continue
        txt = (m.get("content") or "").replace("\n", " / ")
        if not txt and m.get("embeds"): txt = "[embed] " + " / ".join((e.get("title") or "") + " " + (e.get("description") or "") for e in m["embeds"]).replace("\n", " / ")
        out.append(f"{name} {t:%H:%M} {m['author'].get('username')}: {txt[:300]}")
chunk = []
for line in out or ["no messages"]:
    chunk.append(line)
    if len(chunk) == 25: print("::notice title=discord::" + " %0A".join(chunk)); chunk = []
if chunk: print("::notice title=discord::" + " %0A".join(chunk))
