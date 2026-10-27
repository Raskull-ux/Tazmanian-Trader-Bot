"""Read-only: one day's messages from the private and VIP channels, printed as run annotations (nothing saved to the repo).
Pages back through history until it passes the requested day. ONLY_TAZ=1 keeps only Taz's own posts."""
import os, requests, datetime as dt
T = os.environ["DISCORD_BOT_TOKEN"]; H = {"Authorization": f"Bot {T}"}
ET = dt.timezone(dt.timedelta(hours=-4))
DAY = os.environ.get("DAY") or dt.datetime.now(ET).strftime("%Y-%m-%d")
CHS = os.environ.get("CHANNELS", "PRIVATE,VIP").split(",")
ONLY = os.environ.get("ONLY_TAZ") == "1"
IDS = {"PRIVATE": "1562327911866830949", "VIP": "1412516610845184123"}
out = []
for name in CHS:
    before = None; got = []
    for _ in range(30):
        p = {"limit": 100}
        if before: p["before"] = before
        r = requests.get(f"https://discord.com/api/v10/channels/{IDS[name]}/messages", headers=H, params=p, timeout=20)
        if r.status_code != 200: out.append(f"{name} error {r.status_code}"); break
        js = r.json()
        if not js: break
        got += js; before = js[-1]["id"]
        if dt.datetime.fromisoformat(js[-1]["timestamp"]).astimezone(ET).strftime("%Y-%m-%d") < DAY: break
    for m in reversed(got):
        t = dt.datetime.fromisoformat(m["timestamp"]).astimezone(ET)
        if t.strftime("%Y-%m-%d") != DAY: continue
        u = m["author"].get("username")
        if ONLY and u != "tazmaniantrader": continue
        txt = (m.get("content") or "").replace("\n", " / ")
        if not txt and m.get("embeds"): txt = "[embed] " + " / ".join((e.get("title") or "") + " " + (e.get("description") or "") for e in m["embeds"]).replace("\n", " / ")
        if not txt and m.get("attachments"): txt = "[image]"
        out.append(f"{name} {t:%H:%M} {u}: {txt[:260]}")
chunk = []
for line in out or ["no messages"]:
    chunk.append(line)
    if len(chunk) == 25: print("::notice title=discord::" + DAY + " | " + " %0A".join(chunk)); chunk = []
if chunk: print("::notice title=discord::" + DAY + " | " + " %0A".join(chunk))
