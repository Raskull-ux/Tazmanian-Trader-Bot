"""One-off probe of free calendar sources (writes samples to results/morning/probe/)."""
import os, json, requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36", "Accept": "application/json, text/plain, */*"}
os.makedirs("results/morning/probe", exist_ok=True)
for name, url in {
    "nasdaq_econ_1023": "https://api.nasdaq.com/api/calendar/economicevents?date=2026-10-23",
    "nasdaq_econ_1026": "https://api.nasdaq.com/api/calendar/economicevents?date=2026-10-26",
    "ff_thisweek": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "ff_nextweek": "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
    "factbase": "https://media-cdn.factba.se/rss/json/trump/calendar-full.json",
}.items():
    try:
        r = requests.get(url, headers=UA, timeout=25)
        txt = r.text
        try:
            j = r.json()
            if isinstance(j, list): sample = {"type": "list", "len": len(j), "first": j[:3], "last": j[-3:]}
            else: sample = {"type": "dict", "keys": list(j.keys()), "body": json.dumps(j)[:4000]}
        except Exception:
            sample = {"type": "text", "head": txt[:1500]}
        out = {"status": r.status_code, **sample}
    except Exception as e:
        out = {"error": repr(e)}
    json.dump(out, open(f"results/morning/probe/{name}.json", "w"), indent=1, default=str)
