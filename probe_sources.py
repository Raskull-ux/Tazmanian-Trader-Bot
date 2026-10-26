"""One-off probe of free calendar sources (writes samples to results/morning/probe/)."""
import os, json, requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36", "Accept": "*/*"}
BLS_UA = {"User-Agent": "TazmanianTraderBot/1.0 (contact: taz-bot@users.noreply.github.com)", "Accept": "*/*"}
os.makedirs("results/morning/probe", exist_ok=True)
import glob
for f in glob.glob("results/morning/probe/*.json"): os.remove(f)
import re as _re2
try:
    t = requests.get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", headers=UA, timeout=25).text
    open("results/morning/probe/fomc_calendar.html", "w").write(t)
    hist = requests.get("https://www.federalreserve.gov/monetarypolicy/fomc_historical_year.htm", headers=UA, timeout=25).text
    open("results/morning/probe/fomc_hist_index.html", "w").write(hist[:400000])
    for y in range(2019, 2021):
        r = requests.get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm", headers=UA, timeout=25)
        open(f"results/morning/probe/fomc_{y}.html", "w").write(r.text)
except Exception as e:
    open("results/morning/probe/fomc_error.txt", "w").write(repr(e))
for name, url in {
    "bea_ics": "https://www.bea.gov/news/schedule/icalendar",
    "bls_ics": "https://www.bls.gov/schedule/news_release/bls.ics",
    "fed_oct": "https://www.federalreserve.gov/newsevents/2026-october.htm",
    "fed_nov": "https://www.federalreserve.gov/newsevents/2026-november.htm",
    "fed_json": "https://www.federalreserve.gov/json/calendar.json",
    "fomc_cal": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "treasury_upcoming": "https://www.treasurydirect.gov/TA_WS/securities/upcoming?format=json",
    "te_guest": "https://api.tradingeconomics.com/calendar/country/united%20states?c=guest:guest&f=json",
    "census_cal": "https://www.census.gov/economic-indicators/calendar-listview.html",
    "marketwatch_cal": "https://www.marketwatch.com/economy-politics/calendar",
    "nasdaq_econ_1023": "https://api.nasdaq.com/api/calendar/economicevents?date=2026-10-23",
    "nasdaq_econ_1026": "https://api.nasdaq.com/api/calendar/economicevents?date=2026-10-26",
    "ff_thisweek": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "ff_nextweek": "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
    "factbase": "https://media-cdn.factba.se/rss/json/trump/calendar-full.json",
}.items():
    try:
        r = requests.get(url, headers=BLS_UA if "bls.gov" in url else UA, timeout=25)
        txt = r.text
        try:
            j = r.json()
            if isinstance(j, list): sample = {"type": "list", "len": len(j), "first": j[:3], "last": j[-3:]}
            else: sample = {"type": "dict", "keys": list(j.keys()), "body": json.dumps(j)[:4000]}
        except Exception:
            import re
            body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", txt, flags=re.S)
            body = re.sub(r"<[^>]+>", " ", body); body = re.sub(r"\s+", " ", body)
            sample = {"type": "text", "len": len(txt), "head": txt[:800], "text_mid": body[:6000]}
        out = {"status": r.status_code, **sample}
    except Exception as e:
        out = {"error": repr(e)}
    json.dump(out, open(f"results/morning/probe/{name}.json", "w"), indent=1, default=str)
