"""
Tazmanian Trader — Universe Builder
===================================
Builds the list of stocks/ETFs the bot watches. Three groups:

  core    Every ticker Taz has actually traded (from the trade record) that is
          still listed, has options, and is liquid. These are always included
          and never cut by the ranking.
  broad   Every other US-listed stock/ETF with listed options, ranked by
          20-day average dollar volume. Top TARGET_SIZE are kept.
  gauge   Market-context ETFs (semis, transports, sectors, rates, vol).
          Recorded on every alert so the tape can be analyzed later.

Liquidity is measured with real consolidated (SIP) daily bars from Alpaca.
Alpaca's free plan allows SIP history as long as the request ends more than
15 minutes ago, so the request ends yesterday. If SIP is refused, the script
falls back to the IEX feed: IEX volume is only a small slice of total volume,
so absolute floors are disabled and ranking alone is used, and the report
says so in the first line.

Env:  ALPACA_API_KEY_ID, ALPACA_API_SECRET_KEY   (paper keys are fine)
Opt:  TARGET_SIZE (default 1000), MIN_PRICE (5), MIN_DOLLAR_VOL (25e6),
      MIN_SHARE_VOL (1e6), CORE_MIN_DOLLAR_VOL (10e6), TRADE_RECORD (xlsx path)

Output: universe/universe.csv, universe/universe_report.md
"""

from __future__ import annotations
import os, sys, time, glob
from datetime import date, timedelta
import requests
import pandas as pd

TRADING_API = "https://paper-api.alpaca.markets"
DATA_API = "https://data.alpaca.markets"

TARGET_SIZE = int(os.environ.get("TARGET_SIZE", 1000))
MIN_PRICE = float(os.environ.get("MIN_PRICE", 5))
MIN_DOLLAR_VOL = float(os.environ.get("MIN_DOLLAR_VOL", 25e6))
MIN_SHARE_VOL = float(os.environ.get("MIN_SHARE_VOL", 0))  # dollar volume is the liquidity test; a share floor wrongly drops high-priced names (DPZ, ULTA)
CORE_MIN_DOLLAR_VOL = float(os.environ.get("CORE_MIN_DOLLAR_VOL", 10e6))
LOOKBACK_DAYS = 20
LISTED_EXCHANGES = {"NYSE", "NASDAQ", "ARCA", "AMEX", "BATS"}

GAUGES = {
    "SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Small caps / breadth",
    "DIA": "Dow", "RSP": "Equal-weight S&P (breadth vs SPY)",
    "SMH": "Semis", "SOXX": "Semis", "IYT": "Transports",
    "XLK": "Tech", "XLF": "Financials", "KRE": "Regional banks",
    "XLE": "Energy", "XLY": "Consumer discretionary", "XLP": "Consumer staples",
    "XLV": "Health care", "XLI": "Industrials", "XLU": "Utilities",
    "TLT": "Long bonds", "HYG": "High-yield credit", "GLD": "Gold",
    "USO": "Oil", "UUP": "US dollar", "VIXY": "VIX futures (short-term)",
    "VIXM": "VIX futures (mid-term)",
}


def headers():
    k = (os.environ.get("ALPACA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        sys.exit("ALPACA_API_KEY / ALPACA_SECRET_KEY secrets are empty or missing in THIS repo "
                 "(Settings -> Secrets and variables -> Actions).")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


def key_diagnostic():
    """Safe facts only: never prints the key itself."""
    k = (os.environ.get("ALPACA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or "").strip()
    kind = {"PK": "PAPER", "AK": "LIVE"}.get(k[:2], "UNKNOWN prefix")
    return (f"key id: {len(k)} chars, type {kind}; secret: {len(s)} chars "
            "")


def get(url, params=None, tries=5):
    for i in range(tries):
        r = requests.get(url, headers=headers(), params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** i)
            continue
        return r
    r.raise_for_status()


# ---------------------------------------------------------------------------
def load_traded(path: str | None) -> pd.DataFrame:
    """Per-ticker counts from the Raw Fills tab. Empty frame if no file."""
    if not path:
        hits = sorted(glob.glob("Tazmanian_Trade_Record*.xlsx"))
        path = hits[-1] if hits else None
    if not path or not os.path.exists(path):
        print("No trade record found — core group will be empty.")
        return pd.DataFrame(columns=["symbol", "traded_buys", "traded_net", "last_traded"])
    raw = pd.read_excel(path, "Raw Fills (All Accounts)", header=3)
    raw["Side"] = raw["Side"].astype(str).str.upper()
    raw["cash"] = raw["Qty"] * raw["Price"] * 100 * raw["Side"].map({"BUY": -1, "SELL": 1})
    g = raw.groupby("Symbol").agg(
        traded_buys=("Side", lambda s: int((s == "BUY").sum())),
        traded_net=("cash", "sum"),
        last_traded=("Date", "max"),
    ).reset_index().rename(columns={"Symbol": "symbol"})
    g["symbol"] = g["symbol"].astype(str).str.upper().str.strip()
    print(f"Trade record {path}: {len(g)} traded tickers")
    return g


def load_assets() -> pd.DataFrame:
    print(key_diagnostic())
    params = {"status": "active", "asset_class": "us_equity"}
    r = None
    for base in ("https://paper-api.alpaca.markets", "https://api.alpaca.markets"):
        r = get(f"{base}/v2/assets", params)
        print(f"assets via {base}: HTTP {r.status_code}")
        if r.status_code == 200:
            break
    if r.status_code != 200:
        sys.exit("Alpaca rejected these keys on both paper and live (401 = wrong/expired key "
                 "or secret, or key and secret from different key pairs). Regenerate a PAPER "
                 "key pair in the Alpaca dashboard and paste BOTH into this repo's secrets.")
    a = pd.DataFrame(r.json())
    a["has_options"] = a["attributes"].apply(lambda x: "has_options" in (x or []))
    a = a[a["tradable"] & a["exchange"].isin(LISTED_EXCHANGES)]
    print(f"Active listed tradable assets: {len(a)}; with options: {int(a['has_options'].sum())}")
    return a[["symbol", "name", "exchange", "has_options"]]


def fetch_daily(symbols: list[str], feed: str) -> pd.DataFrame | None:
    """Daily bars for the last ~LOOKBACK_DAYS sessions. None if feed refused."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=LOOKBACK_DAYS * 2 + 10)
    rows = []
    for i in range(0, len(symbols), 200):
        chunk = symbols[i:i + 200]
        token = None
        while True:
            p = {"symbols": ",".join(chunk), "timeframe": "1Day",
                 "start": start.isoformat(), "end": end.isoformat(),
                 "feed": feed, "adjustment": "split", "limit": 10000}
            if token:
                p["page_token"] = token
            r = get(f"{DATA_API}/v2/stocks/bars", p)
            if r.status_code in (401, 403):
                print(f"Feed '{feed}' refused ({r.status_code}): {r.text[:200]}")
                return None
            r.raise_for_status()
            j = r.json()
            for sym, bars in (j.get("bars") or {}).items():
                for b in bars:
                    rows.append((sym, b["t"], b["c"], b["v"]))
            token = j.get("next_page_token")
            if not token:
                break
        print(f"  bars: {min(i + 200, len(symbols))}/{len(symbols)} symbols")
    return pd.DataFrame(rows, columns=["symbol", "t", "close", "volume"])


def liquidity(bars: pd.DataFrame) -> pd.DataFrame:
    bars = bars.sort_values("t")
    bars = bars.groupby("symbol").tail(LOOKBACK_DAYS)
    bars["dv"] = bars["close"] * bars["volume"]
    return bars.groupby("symbol").agg(
        days=("t", "size"), last_close=("close", "last"),
        avg_volume=("volume", "mean"), avg_dollar_vol=("dv", "mean"),
    ).reset_index()


# ---------------------------------------------------------------------------
def main():
    traded = load_traded(os.environ.get("TRADE_RECORD"))
    assets = load_assets()
    optionable = assets[assets["has_options"]]

    feed = "sip"
    bars = fetch_daily(optionable["symbol"].tolist(), "sip")
    if bars is None:
        feed = "iex"
        bars = fetch_daily(optionable["symbol"].tolist(), "iex")
    liq = liquidity(bars).merge(optionable, on="symbol", how="left")
    floors_on = feed == "sip"

    def passes(df, min_dv):
        ok = (df["last_close"] >= MIN_PRICE) & (df["days"] >= LOOKBACK_DAYS * 0.75)
        if floors_on:
            ok &= df["avg_dollar_vol"] >= min_dv
            if MIN_SHARE_VOL > 0:
                ok &= df["avg_volume"] >= MIN_SHARE_VOL
        return ok

    # --- core: Taz's traded tickers -------------------------------------
    core_rows, dropped = [], []
    active = set(assets["symbol"]); opt = set(optionable["symbol"])
    liq_i = liq.set_index("symbol")
    for _, t in traded.iterrows():
        s = t["symbol"]
        if s not in active:
            dropped.append((s, "no longer listed / renamed")); continue
        if s not in opt:
            dropped.append((s, "no listed options")); continue
        if s not in liq_i.index:
            dropped.append((s, "no recent bars")); continue
        row = liq_i.loc[[s]].reset_index()
        if not passes(row, CORE_MIN_DOLLAR_VOL).iloc[0]:
            dropped.append((s, f"below liquidity floor (${row['avg_dollar_vol'].iloc[0]/1e6:.1f}M/day, "
                               f"${row['last_close'].iloc[0]:.2f})")); continue
        core_rows.append(s)
    core = liq[liq["symbol"].isin(core_rows)].assign(group="core")

    # --- gauges ------------------------------------------------------------
    gauge = liq[liq["symbol"].isin(GAUGES) & ~liq["symbol"].isin(core["symbol"])].assign(group="gauge")
    missing_g = sorted(set(GAUGES) - set(liq["symbol"]))

    # --- broad: everything else, ranked -------------------------------------
    rest = liq[~liq["symbol"].isin(set(core["symbol"]) | set(gauge["symbol"]))]
    rest = rest[passes(rest, MIN_DOLLAR_VOL)].sort_values("avg_dollar_vol", ascending=False)
    n_broad = max(TARGET_SIZE - len(core) - len(gauge), 0)
    broad = rest.head(n_broad).assign(group="broad")

    uni = pd.concat([core, gauge, broad], ignore_index=True)
    uni = uni.merge(traded, on="symbol", how="left")
    uni["gauge_label"] = uni["symbol"].map(GAUGES)
    uni["rank_dollar_vol"] = uni["avg_dollar_vol"].rank(ascending=False).astype(int)
    uni = uni.sort_values(["group", "avg_dollar_vol"], ascending=[True, False])
    cols = ["symbol", "group", "name", "exchange", "last_close", "avg_volume",
            "avg_dollar_vol", "rank_dollar_vol", "traded_buys", "traded_net",
            "last_traded", "gauge_label"]
    os.makedirs("universe", exist_ok=True)
    uni[cols].to_csv("universe/universe.csv", index=False)

    # --- report -------------------------------------------------------------
    L = []
    L.append(f"# Universe — built {date.today()}  (feed: {feed.upper()})")
    if not floors_on:
        L.append("\n**WARNING: SIP refused, IEX used. IEX volume is a small slice of total "
                 "volume, so dollar-volume floors were OFF and names were ranked only.**")
    L.append(f"\nTotal: **{len(uni)}** = core {len(core)} + gauges {len(gauge)} + broad {len(broad)}")
    L.append(f"\nRules: options listed; price ≥ ${MIN_PRICE:g}; ≥{int(LOOKBACK_DAYS*0.75)} of last "
             f"{LOOKBACK_DAYS} sessions traded; broad ≥ ${MIN_DOLLAR_VOL/1e6:g}M/day; core ≥ ${CORE_MIN_DOLLAR_VOL/1e6:g}M/day.")
    if len(broad):
        L.append(f"\nSmallest broad name kept: {broad.iloc[-1]['symbol']} at "
                 f"${broad.iloc[-1]['avg_dollar_vol']/1e6:.1f}M/day. "
                 f"Eligible broad names not kept (beyond target): {max(len(rest)-n_broad,0)}.")
    L.append("\n## Core — your traded tickers kept (by your buy count)\n")
    c = core.merge(traded, on="symbol").sort_values("traded_buys", ascending=False)
    L.append("| Ticker | Your buys | Your net $ | Avg $ vol/day |\n|---|---|---|---|")
    for _, r in c.iterrows():
        L.append(f"| {r['symbol']} | {int(r['traded_buys'])} | {r['traded_net']:,.0f} | "
                 f"${r['avg_dollar_vol']/1e6:,.0f}M |")
    L.append(f"\n## Core — your traded tickers dropped ({len(dropped)})\n")
    for s, why in sorted(dropped):
        L.append(f"- {s}: {why}")
    L.append("\n## Gauges\n")
    for g_sym, label in GAUGES.items():
        if g_sym in set(uni["symbol"]):
            tag = " (also one of your traded tickers)" if g_sym in set(core["symbol"]) else ""
            L.append(f"- {g_sym} — {label}{tag}")
    if missing_g:
        L.append(f"- Missing (not returned by Alpaca): {', '.join(missing_g)}")
    L.append("\nNote: the VIX index itself and its futures term structure are not available "
             "from Alpaca stock data. VIXY/VIXM are ETF proxies only.")
    open("universe/universe_report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L[:6]))


if __name__ == "__main__":
    main()
