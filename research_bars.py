# Pull SIP stock bars (free Alpaca data) for research. Extended hours included.
# Env: SYMS (comma list), TFS (e.g. 15Min,30Min,1Hour), START (YYYY-MM-DD). Writes results/research/{SYM}_{TF}.csv.gz
import os, time, requests, pandas as pd
K=os.environ["ALPACA_API_KEY_ID"]; S=os.environ["ALPACA_API_SECRET_KEY"]
H={"APCA-API-KEY-ID":K,"APCA-API-SECRET-KEY":S}
syms=[s.strip().upper() for s in os.environ.get("SYMS","HOOD").split(",") if s.strip()]
tfs=os.environ.get("TFS","15Min,30Min,1Hour").split(",")
start=os.environ.get("START","2024-01-01")+"T00:00:00Z"
os.makedirs("results/research",exist_ok=True)
for sym in syms:
    for tf in tfs:
        rows=[]; tok=None
        while True:
            p={"timeframe":tf,"start":start,"feed":"sip","limit":10000,"adjustment":"split"}
            if tok: p["page_token"]=tok
            r=requests.get(f"https://data.alpaca.markets/v2/stocks/{sym}/bars",headers=H,params=p,timeout=60)
            if r.status_code==429: time.sleep(3); continue
            r.raise_for_status(); j=r.json(); rows+=j.get("bars") or []; tok=j.get("next_page_token")
            if not tok: break
        df=pd.DataFrame(rows)
        if df.empty: print("none",sym,tf); continue
        df=df.rename(columns={"t":"t","o":"o","h":"h","l":"l","c":"c","v":"v"})[["t","o","h","l","c","v"]]
        df.to_csv(f"results/research/{sym}_{tf}.csv.gz",index=False); print(sym,tf,len(df),df.t.iloc[0],df.t.iloc[-1])
