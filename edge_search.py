"""
EDGE SEARCH, STAGE 1: thousands of variations on stock moves, honest scoring.

Names: 11 ETFs + 24 liquid stocks with weekly options (two groups, pooled within each group).
Data: Alpaca 5-minute bars (regular hours, SIP, split+dividend adjusted) 2016 -> now, laid out as a day x 78-slot
grid; daily bars built from them; Alpaca 1-hour bars WITH extended hours for the 3-hour chart; Yahoo ^VIX.

SIGNALS (every one fires at a bar close using only what was known then):
  Intraday (first time per day): opening-range break up/down and failed breaks, prior-day high/low breaks and
    failed breaks, gaps 1% / 2% up/down (9:35), gap fills, VWAP reclaim/loss, 5-min RSI 20/80, 15-min RSI 20/80,
    1-hour RSI 25/75, live daily RSI crossing 30/70, big 5-min bars (3x normal), live triple MA break up/down.
  Daily (at the close, on the day it first happens): RSI(2) 10/90, RSI(5) 20/80, RSI(14) 30/70/80, 10-day-candle
    RSI 80/20, stretch from the 20 SMA (2.5 ATR), crosses 8/21 EMA, 10/20 SMA, 20/50 SMA, 10 EMA/10 SMA (both ways),
    streaks of 3 and 5 up/down closes, inside day, NR7, TD9 buy/sell, 20-day breakout/breakdown, volume spike
    (2x) on up/down days, fresh triple MA break up/down, 3-hour RSI 80/20 (extended hours).
HOLDS: intraday signals 15m / 30m / 1h / 2h / to the close / next day's close; daily signals 1 / 3 / 5 days.
REGIMES (known at the prior close): all days, VIX under 20, VIX 20+, uptrend (close over its 200 SMA), downtrend.
EDGE = the move after the signal MINUS the average move for the same name, same 5-minute slot, same hold, same
  regime, same period (so time of day, market drift and regime are all taken out). Direction is free: a negative
  edge means puts, positive means calls. t clustered by month.

HONEST SCORING (set before running):
  DISCOVERY 2016-2022: every variation scored. Candidates need 150+ events, 24+ months, |edge| above a size floor
    worth trading with options (15m 0.05%, 30m 0.07%, 1h 0.10%, 2h 0.12%, close 0.15%, 1d 0.25%, 3d 0.40%,
    5d 0.50%) and |t| >= 3. The top 25 by |t| go on.
  HOLDOUT 2023-2026 (never looked at before this): SURVIVOR = same direction, 60+ events, |t| >= 2.5,
    |edge| at least half the floor.
  Checked on random-walk test data first (see the noise line in the report).
Out: results/edge_search/report.md, all_tests.csv, survivors.csv, events_2024.csv.gz (for stage 2)
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/edge_search"
ETFS = "QQQ SPY IWM DIA XLK SMH XLF XLE XLV ARKK TLT".split()
STOCKS = ("AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX MU INTC BA JPM BAC XOM DIS UBER SHOP CRWD PLTR COIN "
          "SOFI HOOD").split()
SLOTS = 78
HOLD_SPLIT = pd.Timestamp("2023-01-01")
EV_START = pd.Timestamp("2024-02-01")
H_INTRA = ["15m", "30m", "1h", "2h", "close", "1d"]
H_DAILY = ["1d", "3d", "5d"]
FLOOR = {"15m": .05, "30m": .07, "1h": .10, "2h": .12, "close": .15, "1d": .25, "3d": .40, "5d": .50}
REGIMES = ["all", "VIX<20", "VIX20+", "uptrend", "downtrend"]
TOP_N, DISC_T, HOLD_T, DISC_N, DISC_M, HOLD_N = 25, 3.0, 2.5, 150, 24, 60
ALWAYS_SHOW = [("D RSI14 <=30", "ETF"), ("3h RSI >=80", "ETF"), ("D triple break down", "ETF"),
               ("D SMA10/20 cross down", "ETF"), ("I live daily RSI <30", "ETF"), ("D 10d RSI >=80", "STOCK")]


# ------------------------------------------------------------------ data
def keys():
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        raise SystemExit("Alpaca keys missing in this repo's secrets.")
    return {"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s}


HD = None


def fetch(sym, tf, start):
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": tf, "start": start, "end": end, "feed": "sip", "adjustment": "all", "limit": 10000}
        if token:
            p["page_token"] = token
        r = None
        for i in range(7):
            try:
                r = requests.get("https://data.alpaca.markets/v2/stocks/bars", headers=HD, params=p, timeout=90)
            except requests.RequestException:
                time.sleep(2 ** i); continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** i); continue
            break
        if r is None or r.status_code != 200:
            print(f"  {sym} {tf}: {None if r is None else r.status_code}"); break
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v"])
    if len(d):
        d["t"] = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    return d


def vix_series():
    try:
        import yfinance as yf
        v = yf.download("^VIX", start="2015-06-01", auto_adjust=False, progress=False, threads=False)
        if isinstance(v.columns, pd.MultiIndex):
            v.columns = v.columns.get_level_values(0)
        s = v["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        return s
    except Exception as ex:
        print(f"  VIX download failed ({ex}); VIX regimes skipped")
        return pd.Series(dtype=float)


# ------------------------------------------------------------------ grid
def build_grid(m5):
    t = m5.t
    mins = t.dt.hour * 60 + t.dt.minute - 570
    m5 = m5[(mins >= 0) & (mins < 390)].copy()
    m5["day"] = m5.t.dt.normalize(); m5["slot"] = ((m5.t.dt.hour * 60 + m5.t.dt.minute - 570) // 5).astype(int)
    cnt = m5.groupby("day").size()
    days = cnt[cnt >= 40].index.sort_values()
    m5 = m5[m5.day.isin(days)]
    di = days.get_indexer(m5.day)
    G = {}
    for k in ("o", "h", "l", "c", "v"):
        a = np.full((len(days), SLOTS), np.nan)
        a[di, m5.slot.values] = m5[k].values
        G[k] = a
    C = pd.DataFrame(G["c"]).ffill(axis=1).bfill(axis=1)
    miss = np.isnan(G["c"])
    G["c"] = C.values
    for k in ("o", "h", "l"):
        G[k] = np.where(miss, G["c"], G[k])
    G["v"] = np.where(miss, 0.0, G["v"])
    return days, G


def wilder(c, n):
    c = pd.Series(np.asarray(c, float))
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return up.values, dn.values


def rsi(c, n):
    up, dn = wilder(c, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 - 100 / (1 + up / dn)


def first_per_day(M):
    M = np.asarray(M, bool)
    E = np.zeros_like(M)
    has = M.any(1)
    E[has, M[has].argmax(1)] = True
    return E


def daily_only(x):
    E = np.zeros((len(x), SLOTS), bool)
    E[:, SLOTS - 1] = np.asarray(x, bool)
    return E


def cross_into(x, cond_now):
    """True on the day cond becomes true (false the day before)."""
    cond_now = np.asarray(cond_now, bool)
    prev = np.r_[False, cond_now[:-1]]
    return cond_now & ~prev


# ------------------------------------------------------------------ signals
def signals(days, G, h1):
    O, H, L, C, V = G["o"], G["h"], G["l"], G["c"], G["v"]
    D = len(days); s = np.arange(SLOTS)[None, :]
    o, h, l, c, v = O[:, 0], H.max(1), L.min(1), C[:, -1], V.sum(1)
    pc = np.r_[np.nan, c[:-1]]; ph = np.r_[np.nan, h[:-1]]; pl = np.r_[np.nan, l[:-1]]
    S = {}
    # ---------- intraday
    orh, orl = H[:, :6].max(1)[:, None], L[:, :6].min(1)[:, None]
    after = s >= 6
    up_b = first_per_day(after & (C > orh)); dn_b = first_per_day(after & (C < orl))
    S["I ORB up"] = up_b; S["I ORB down"] = dn_b
    bu = np.where(up_b.any(1), up_b.argmax(1), 999)[:, None]; bd = np.where(dn_b.any(1), dn_b.argmax(1), 999)[:, None]
    S["I ORB up fails"] = first_per_day((s > bu) & (s <= bu + 6) & (C < orh))
    S["I ORB down fails"] = first_per_day((s > bd) & (s <= bd + 6) & (C > orl))
    PDH, PDL = ph[:, None], pl[:, None]
    late = s >= 3
    pb = first_per_day(late & (C > PDH) & (O[:, :1] < PDH)); pd_ = first_per_day(late & (C < PDL) & (O[:, :1] > PDL))
    S["I prior-day high break"] = pb; S["I prior-day low break"] = pd_
    b1 = np.where(pb.any(1), pb.argmax(1), 999)[:, None]; b2 = np.where(pd_.any(1), pd_.argmax(1), 999)[:, None]
    S["I prior-day high break fails"] = first_per_day((s > b1) & (s <= b1 + 6) & (C < PDH))
    S["I prior-day low break fails"] = first_per_day((s > b2) & (s <= b2 + 6) & (C > PDL))
    gap = (o / pc - 1) * 100
    for g in (1, 2):
        S[f"I gap up {g}%"] = (s == 0) & (gap >= g)[:, None]
        S[f"I gap down {g}%"] = (s == 0) & (gap <= -g)[:, None]
    S["I gap up fills"] = first_per_day((gap >= 0.5)[:, None] & (L <= pc[:, None]))
    S["I gap down fills"] = first_per_day((gap <= -0.5)[:, None] & (H >= pc[:, None]))
    typ = (H + L + C) / 3
    with np.errstate(invalid="ignore", divide="ignore"):
        vw = np.cumsum(typ * V, 1) / np.cumsum(V, 1)
    vw = pd.DataFrame(vw).ffill(axis=1).values
    prevC = np.c_[np.full(D, np.nan), C[:, :-1]]; prevV = np.c_[np.full(D, np.nan), vw[:, :-1]]
    S["I VWAP reclaim"] = first_per_day(after & (C > vw) & (prevC <= prevV))
    S["I VWAP loss"] = first_per_day(after & (C < vw) & (prevC >= prevV))
    r5 = rsi(C.ravel(), 14).reshape(D, SLOTS)
    r5p = np.r_[np.nan, r5.ravel()[:-1]].reshape(D, SLOTS)
    S["I 5m RSI <=20"] = first_per_day(late & (r5 <= 20) & (r5p > 20))
    S["I 5m RSI >=80"] = first_per_day(late & (r5 >= 80) & (r5p < 80))
    for name, idx, lo, hi in (("15m", np.arange(2, SLOTS, 3), 20, 80),
                              ("1h", np.array([11, 23, 35, 47, 59, 71, 77]), 25, 75)):
        rr = rsi(C[:, idx].ravel(), 14).reshape(D, len(idx))
        rp = np.r_[np.nan, rr.ravel()[:-1]].reshape(D, len(idx))
        a = np.zeros((D, SLOTS), bool); b = np.zeros((D, SLOTS), bool)
        a[:, idx] = (rr <= lo) & (rp > lo); b[:, idx] = (rr >= hi) & (rp < hi)
        S[f"I {name} RSI <={lo}"] = first_per_day(a); S[f"I {name} RSI >={hi}"] = first_per_day(b)
    up14, dn14 = wilder(c, 14)
    rd = 100 - 100 / (1 + up14 / dn14)
    pu, pdn, prd = np.r_[np.nan, up14[:-1]], np.r_[np.nan, dn14[:-1]], np.r_[np.nan, rd[:-1]]
    ch = C - pc[:, None]
    with np.errstate(invalid="ignore", divide="ignore"):
        live = 100 - 100 / (1 + ((pu[:, None] * 13 + np.clip(ch, 0, None)) / 14) / ((pdn[:, None] * 13 + np.clip(-ch, 0, None)) / 14))
    S["I live daily RSI <30"] = first_per_day((live < 30) & (prd > 30)[:, None])
    S["I live daily RSI >70"] = first_per_day((live > 70) & (prd < 70)[:, None])
    r5m = np.abs(C / prevC - 1)
    avg = pd.Series(np.nanmean(r5m[:, 1:], 1)).rolling(20).mean().shift(1).values[:, None]
    big = (s >= 1) & (r5m > 3 * avg)
    S["I big 5m bar up"] = first_per_day(big & (C > prevC)); S["I big 5m bar down"] = first_per_day(big & (C < prevC))
    cs = pd.Series(c)
    sums = {n: cs.rolling(n - 1).sum().shift(1).values[:, None] for n in (10, 20, 50)}
    lsma = {n: (sums[n] + C) / n for n in sums}
    sm = {n: cs.rolling(n).mean().values for n in (10, 20, 50, 200)}
    under3 = (c < sm[10]) & (c < sm[20]) & (c < sm[50]); over3 = (c > sm[10]) & (c > sm[20]) & (c > sm[50])
    u2 = np.r_[False, False, under3[:-2]] | np.r_[False, under3[:-1]]
    o2 = np.r_[False, False, over3[:-2]] | np.r_[False, over3[:-1]]
    S["I live triple MA break down"] = first_per_day((C < lsma[10]) & (C < lsma[20]) & (C < lsma[50]) & ~u2[:, None])
    S["I live triple MA break up"] = first_per_day((C > lsma[10]) & (C > lsma[20]) & (C > lsma[50]) & ~o2[:, None])
    # ---------- daily (at the close)
    for n, lo, his in ((2, 10, (90,)), (5, 20, (80,)), (14, 30, (70, 80))):
        r = rsi(c, n)
        S[f"D RSI{n} <={lo}"] = daily_only(cross_into(None, r <= lo))
        for hi in his:
            S[f"D RSI{n} >={hi}"] = daily_only(cross_into(None, r >= hi))
    blk = np.arange(D) // 10
    Cb = pd.Series(c).groupby(blk).last()
    ub, db = wilder(Cb.values, 14)
    prev = blk - 1; ok = prev >= 13
    chb = c - np.where(ok, Cb.values[np.maximum(prev, 0)], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        l10 = np.where(ok, 100 - 100 / (1 + ((ub[np.maximum(prev, 0)] * 13 + np.clip(chb, 0, None)) / 14) /
                                     ((db[np.maximum(prev, 0)] * 13 + np.clip(-chb, 0, None)) / 14)), np.nan)
    S["D 10d RSI >=80"] = daily_only(cross_into(None, l10 >= 80)); S["D 10d RSI <=20"] = daily_only(cross_into(None, l10 <= 20))
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().values
    z = (c - sm[20]) / atr
    S["D stretch <=-2.5 ATR"] = daily_only(cross_into(None, z <= -2.5)); S["D stretch >=2.5 ATR"] = daily_only(cross_into(None, z >= 2.5))
    ema = {n: cs.ewm(span=n, adjust=False).mean().values for n in (8, 10, 21)}
    for nm, a, b in (("EMA8/21", ema[8], ema[21]), ("SMA10/20", sm[10], sm[20]), ("SMA20/50", sm[20], sm[50]),
                     ("EMA10/SMA10", ema[10], sm[10])):
        S[f"D {nm} cross up"] = daily_only(cross_into(None, a > b)); S[f"D {nm} cross down"] = daily_only(cross_into(None, a < b))
    dnd = (c < pc).astype(int); upd = (c > pc).astype(int)
    rd_ = pd.Series(dnd).groupby((dnd == 0).cumsum()).cumsum().values
    ru_ = pd.Series(upd).groupby((upd == 0).cumsum()).cumsum().values
    for k in (3, 5):
        S[f"D {k} down closes"] = daily_only(rd_ == k); S[f"D {k} up closes"] = daily_only(ru_ == k)
    S["D inside day"] = daily_only((h < ph) & (l > pl))
    rng = h - l
    S["D NR7"] = daily_only(rng <= pd.Series(rng).rolling(7).min().values)
    c4 = np.r_[np.full(4, np.nan), c[:-4]]
    bc = (c < c4).astype(int); sc = (c > c4).astype(int)
    tb = pd.Series(bc).groupby((bc == 0).cumsum()).cumsum().values
    ts = pd.Series(sc).groupby((sc == 0).cumsum()).cumsum().values
    S["D TD9 buy"] = daily_only(tb == 9); S["D TD9 sell"] = daily_only(ts == 9)
    hh = pd.Series(h).rolling(20).max().shift(1).values; ll = pd.Series(l).rolling(20).min().shift(1).values
    S["D 20d breakout"] = daily_only(cross_into(None, c > hh)); S["D 20d breakdown"] = daily_only(cross_into(None, c < ll))
    va = pd.Series(v).rolling(20).mean().shift(1).values
    S["D volume spike up day"] = daily_only((v > 2 * va) & (c > pc)); S["D volume spike down day"] = daily_only((v > 2 * va) & (c < pc))
    S["D triple break down"] = daily_only(under3 & ~u2); S["D triple break up"] = daily_only(over3 & ~o2)
    # ---------- 3-hour RSI (extended hours) mapped onto the grid
    if h1 is not None and len(h1):
        x = h1[(h1.t.dt.hour >= 4) & (h1.t.dt.hour < 20)].copy()
        x["start"] = 4 + 3 * ((x.t.dt.hour - 4) // 3); x["day"] = x.t.dt.normalize()
        g3 = x.groupby(["day", "start"]).agg(c=("c", "last")).reset_index().sort_values(["day", "start"])
        g3["rsi"] = rsi(g3.c.values, 14); g3["prev"] = g3.rsi.shift(1)
        for lab, cond in (("3h RSI >=80", (g3.rsi >= 80) & (g3.prev < 80)), ("3h RSI <=20", (g3.rsi <= 20) & (g3.prev > 20))):
            E = np.zeros((D, SLOTS), bool)
            for r in g3[cond].itertuples():
                end = r.start + 3
                if end in (10, 13, 16):
                    d = days.get_indexer([r.day])[0]; sl = {10: 5, 13: 41, 16: 77}[end]
                else:
                    d = days.searchsorted(r.day + pd.Timedelta(days=1) if r.start >= 16 else r.day); sl = 0
                if 0 <= d < D:
                    E[d, sl] = True
            S[lab] = E
    return S, dict(c=c, sma200=sm[200])


# ------------------------------------------------------------------ forward moves and baselines
def forwards(G):
    C = G["c"]; D = len(C); s = np.arange(SLOTS)
    F = {}
    for name, k in (("15m", 3), ("30m", 6), ("1h", 12), ("2h", 24)):
        F[name] = (C[:, np.minimum(s + k, SLOTS - 1)] / C - 1) * 100
    F["close"] = (C[:, -1:] / C - 1) * 100
    cl = C[:, -1]
    for k in (1, 3, 5):
        nxt = np.r_[cl[k:], np.full(k, np.nan)]
        F[f"{k}d"] = (nxt[:, None] / C - 1) * 100
    return F


def regime_masks(days, info, vix):
    c, s200 = info["c"], info["sma200"]
    up = np.r_[np.nan, (c > s200).astype(float)[:-1]]
    up[np.r_[True, np.isnan(s200[:-1])]] = np.nan
    vp = vix.reindex(days).shift(1).values if len(vix) else np.full(len(days), np.nan)
    return {"all": np.ones(len(days), bool), "VIX<20": vp < 20, "VIX20+": vp >= 20,
            "uptrend": up == 1, "downtrend": up == 0}


def run_symbol(sym, grp, vix, agg_rows, ev_rows):
    m5 = fetch(sym, "5Min", "2016-01-01T00:00:00Z")
    if len(m5) < 20000:
        print(f"  {sym}: not enough 5-min data"); return
    days, G = build_grid(m5)
    h1 = fetch(sym, "1Hour", "2015-10-01T00:00:00Z")
    S, info = signals(days, G, h1)
    F = forwards(G)
    R = regime_masks(days, info, vix)
    valid = np.arange(len(days)) >= 60
    period = np.where(days < HOLD_SPLIT, "disc", "hold")
    month = days.to_period("M").astype(str).values
    base = {}
    for rn, rm in R.items():
        for p in ("disc", "hold"):
            dm = rm & valid & (period == p)
            for hn, f in F.items():
                base[(rn, p, hn)] = np.nanmean(f[dm], 0) if dm.sum() >= 20 else np.full(SLOTS, np.nan)
    for sig, E in S.items():
        hs = H_INTRA if sig.startswith("I ") else H_DAILY
        d_idx, s_idx = np.nonzero(E & valid[:, None])
        if not len(d_idx):
            continue
        for rn, rm in R.items():
            keep = rm[d_idx]
            dd, ss = d_idx[keep], s_idx[keep]
            if not len(dd):
                continue
            for hn in hs:
                ret = F[hn][dd, ss]
                b = np.where(period[dd] == "disc", base[(rn, "disc", hn)][ss], base[(rn, "hold", hn)][ss])
                e = ret - b
                ok = np.isfinite(e)
                if ok.any():
                    df = pd.DataFrame({"sig": sig, "group": grp, "regime": rn, "hold": hn, "period": period[dd[ok]],
                                       "month": month[dd[ok]], "e": e[ok]})
                    agg_rows.append(df.groupby(["sig", "group", "regime", "hold", "period", "month"]).e.agg(["sum", "count"]).reset_index())
        late = days[d_idx] >= EV_START
        if late.any():
            dd, ss = d_idx[late], s_idx[late]
            ts = days[dd] + pd.to_timedelta(570 + 5 * (ss + 1), unit="m")
            ev_rows.append(pd.DataFrame({"sig": sig, "symbol": sym, "group": grp, "entry": ts,
                                         **{f"r_{rn}": R[rn][dd] for rn in REGIMES}}))
    print(f"  {sym}: {len(days)} days, {len(S)} signals", flush=True)


# ------------------------------------------------------------------ scoring
def score(A):
    A = A.groupby(["sig", "group", "regime", "hold", "period", "month"])[["sum", "count"]].sum().reset_index()
    A["mm"] = A["sum"] / A["count"]
    out = []
    for key, g in A.groupby(["sig", "group", "regime", "hold", "period"]):
        n = g["count"].sum(); mean = g["sum"].sum() / n; m = len(g)
        t = g.mm.mean() / (g.mm.std(ddof=1) / math.sqrt(m)) if m >= 5 and g.mm.std() > 0 else np.nan
        out.append((*key, n, m, mean, t))
    T = pd.DataFrame(out, columns=["sig", "group", "regime", "hold", "period", "n", "months", "edge", "t"])
    W = T.pivot_table(index=["sig", "group", "regime", "hold"], columns="period", values=["n", "months", "edge", "t"])
    W.columns = [f"{a}_{b}" for a, b in W.columns]
    return W.reset_index()


def pick(W):
    W = W.copy()
    W["floor"] = W.hold.map(FLOOR)
    cand = W[(W.n_disc >= DISC_N) & (W.months_disc >= DISC_M) & (W.edge_disc.abs() >= W.floor) & (W.t_disc.abs() >= DISC_T)]
    cand = cand.reindex(cand.t_disc.abs().sort_values(ascending=False).index).head(TOP_N).copy()
    same = np.sign(cand.edge_hold) == np.sign(cand.edge_disc)
    cand["survives"] = (same & (cand.n_hold >= HOLD_N) & (cand.t_hold.abs() >= HOLD_T) &
                        (cand.edge_hold.abs() >= cand.floor / 2)).fillna(False)
    cand["direction"] = np.where(cand.edge_disc > 0, "CALLS (up)", "PUTS (down)")
    return W, cand


def report(W, cand, n_tests):
    def row(r):
        return (f"| {r.sig} | {r.group} | {r.regime} | {r.hold} | {r.direction} | {r.edge_disc:+.2f}% (t {r.t_disc:.1f}, n {r.n_disc:.0f}) | "
                f"{r.edge_hold:+.2f}% (t {r.t_hold:.1f}, n {r.n_hold:.0f}) | {'**SURVIVES**' if r.survives else 'fail'} |")
    L = ["# Edge search, stage 1: what survives on stock moves", "",
         f"{n_tests} variations scored (signal x hold x regime x group). Edge = move after the signal minus the normal move "
         "for the same name, 5-minute slot, hold, regime and period, in % of price. Discovery 2016-2022 picks the top "
         f"{TOP_N}; the untouched 2023-2026 holdout decides. Survivors go to stage 2 (real option prices).", "",
         "## 1. SURVIVORS", "",
         "| Signal | Names | Regime | Hold | Direction | Discovery 2016-22 | Holdout 2023-26 | Verdict |",
         "|---|---|---|---|---|---|---|---|"]
    sv = cand[cand.survives]
    L += [row(r) for r in sv.itertuples()] if len(sv) else ["| none | | | | | | | |"]
    L += ["", f"## 2. All {len(cand)} discovery candidates (top by t) and how they did in the holdout", "",
          "| Signal | Names | Regime | Hold | Direction | Discovery 2016-22 | Holdout 2023-26 | Verdict |",
          "|---|---|---|---|---|---|---|---|"]
    L += [row(r) for r in cand.itertuples()]
    L += ["", "## 3. Your setups, for reference (no regime filter)", "",
          "| Signal | Names | Hold | Discovery 2016-22 | Holdout 2023-26 |", "|---|---|---|---|---|"]
    for sig, grp in ALWAYS_SHOW:
        x = W[(W.sig == sig) & (W.group == grp) & (W.regime == "all")]
        for r in x.itertuples():
            L.append(f"| {sig} | {grp} | {r.hold} | {r.edge_disc:+.2f}% (t {r.t_disc:.1f}, n {r.n_disc:.0f}) | "
                     f"{r.edge_hold:+.2f}% (t {r.t_hold:.1f}, n {r.n_hold:.0f}) |")
    L += ["", "Limits: today's names (survivorship); stock moves only (stage 2 prices survivors with real options); "
          "5-minute bars, so entries are at bar closes; regimes use the prior close. Not financial advice."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    global HD
    HD = keys()
    os.makedirs(OUT, exist_ok=True)
    vix = vix_series()
    agg, ev = [], []
    for grp, syms in (("ETF", ETFS), ("STOCK", STOCKS)):
        for s in syms:
            try:
                run_symbol(s, grp, vix, agg, ev)
            except Exception as ex:
                print(f"  {s}: {type(ex).__name__} {ex}")
    W = score(pd.concat(agg))
    W, cand = pick(W)
    W.to_csv(f"{OUT}/all_tests.csv", index=False)
    cand.to_csv(f"{OUT}/survivors.csv", index=False)
    if ev:
        E = pd.concat(ev)
        keep = set(cand[cand.survives].sig)
        E[E.sig.isin(keep)].to_csv(f"{OUT}/events_2024.csv.gz", index=False, compression="gzip")
    report(W, cand, len(W))


if __name__ == "__main__":
    main()
