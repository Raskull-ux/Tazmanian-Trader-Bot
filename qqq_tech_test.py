"""
QQQ + tech test — every chart rule, both directions (puts AND calls), raw moves
==============================================================================
Why: the last test measured stocks vs SPY, which is blind on QQQ (QQQ and SPY dump together).
This one measures the ACTUAL move of the thing you'd buy options on, compared with random days
in that same symbol (so QQQ's normal upward drift is already priced into the comparison).

Data: Yahoo daily history back to 1999 (free, via yfinance); falls back to Alpaca (2016+) per symbol.
Standalone; Alpaca keys optional.

Groups
  QQQ alone
  ETFs  : QQQ SPY IWM DIA XLK SMH SOXX IGV XLC XLY FDN ARKK   (no survivorship bias)
  MEGA  : AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX   (hindsight bias: we know they won -> flatters calls)

Setups (each traded in the direction shown; "edge" = setup minus random days, positive = good for that trade)
  B  Triple MA break DOWN  -> puts   (close under 10/20/50, not under all three 2 days earlier; first fire in 10 days)
       entries: break close / next close (split: follow-through or bounce) / failed retest of the 10 from below
       splits : 50 vs 200 distance, into a golden cross (crossed up last 30d, or 50 within 2% under 200 and rising), bunch
     Triple break DOWN while 50 < 200 -> CALLS  (the bounce the last test found)
  B' Triple MA break UP -> calls (mirror: close over 10/20/50, not over all three 2 days earlier)
       same entries/splits; "into a death cross" = crossed down last 30d or 50 within 2% over 200 and falling
  A  Count from the bottom (bottom = lowest low of 11 days that ends a dump: ETFs 6%+ under 40-day high, stocks 12%+)
       calls at bars 6-8 after the bottom (bottom is only confirmed 5 bars later), puts at bars 9-11 (Taz's top)
     Count from the top (mirror: highest high of 11 days after a 6%/12%+ rally) -> puts at bars 6-10
     Weekly: bottom = lowest low of 7 weeks after a 10%/20%+ dump; calls at weeks 4-6, puts at weeks 9-11;
       plus the week-11-red check (weeks 13-16)
  C  Quiet consolidation (3-15 days, range <= 2.5 ATR, volume <= 50-day avg) then
       volume DUMP (red, >=1.7x consolidation volume, after a rally) -> puts
       volume BREAKOUT (green, >=1.7x, after a decline) -> calls
  R  Daily RSI(14): first close >= 80 / >= 70 -> puts ; first close <= 30 / <= 25 -> calls (10-day cooldown)

PASS RULE (set before running): ETF group, 10-day edge > 0 in EVERY period (2000-15, 2016-21, 2022-26)
AND t >= 3 on all years combined (t clustered by month) AND 100+ events. Mega tech judged the same way, separately.
Checked on fake random-walk prices: 8 runs x 32 tests; the looser t >= 2.5 rule passed noise 2 times in 256.
QQQ alone is shown for every setup but has too few events to pass on its own.
Out: results/qqq_tech/report.md, events.csv.gz
"""
from __future__ import annotations
import os, time, math
import numpy as np, pandas as pd, requests

OUT = "results/qqq_tech"
rng = np.random.default_rng(11)
IDX_ETF = "QQQ SPY IWM DIA XLK SMH SOXX IGV XLC XLY FDN ARKK".split()
MEGA = "AAPL MSFT NVDA AMZN META GOOGL TSLA AMD AVGO NFLX".split()
QQQ_DATES = ["2021-09-17", "2022-01-04", "2023-03-09", "2023-10-18", "2024-04-04", "2024-04-15", "2024-08-30", "2025-02-21"]
PERIODS = (("2000-2015", "1999-01-01", "2016-01-01"), ("2016-2021", "2016-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2100-01-01"))


# ------------------------------------------------------------------ data
def yahoo(sym):
    try:
        import yfinance as yf
        d = yf.download(sym, start="1999-01-01", auto_adjust=True, progress=False, threads=False)
        if d is None or len(d) < 300:
            return None
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        d.columns = ["o", "h", "l", "c", "v"]
        d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
        return d.dropna()
    except Exception as ex:
        print(f"  yahoo {sym}: {ex}")
        return None


def alpaca(sym):
    k = (os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    s = (os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not k or not s:
        return None
    rows, token = [], None
    end = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=20)).isoformat()
    while True:
        p = {"symbols": sym, "timeframe": "1Day", "start": "2016-01-01", "end": end, "feed": "sip",
             "adjustment": "all", "limit": 10000}
        if token:
            p["page_token"] = token
        r = requests.get("https://data.alpaca.markets/v2/stocks/bars", params=p, timeout=60,
                         headers={"APCA-API-KEY-ID": k, "APCA-API-SECRET-KEY": s})
        if r.status_code != 200:
            return None
        j = r.json()
        rows += [(b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in (j.get("bars") or {}).get(sym, [])]
        token = j.get("next_page_token")
        if not token:
            break
    if not rows:
        return None
    d = pd.DataFrame(rows, columns=["t", "o", "h", "l", "c", "v"])
    d.index = pd.to_datetime(d.t, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return d[["o", "h", "l", "c", "v"]]


def load(sym):
    d = yahoo(sym)
    src = "yahoo"
    if d is None:
        d, src = alpaca(sym), "alpaca"
    time.sleep(1)
    return d, src


# ------------------------------------------------------------------ outcome
def outcome(d, j, sign):
    """sign +1 = calls, -1 = puts. Move in the trade's favour, plus 'hit' = moved 3% your way within
    10 days / 5% within 20 days (intraday high/low)."""
    c = d.c.values; h = d.h.values; l = d.l.values
    r = {}
    for n in (5, 10, 20):
        r[f"x{n}"] = sign * (c[j + n] / c[j] - 1) * 100 if j + n < len(c) else np.nan
    c0 = c[j]
    if sign > 0:
        r["hit3"] = float((h[j + 1:j + 11] >= c0 * 1.03).any()); r["hit5"] = float((h[j + 1:j + 21] >= c0 * 1.05).any())
    else:
        r["hit3"] = float((l[j + 1:j + 11] <= c0 * 0.97).any()); r["hit5"] = float((l[j + 1:j + 21] <= c0 * 0.95).any())
    return r


def baseline(d):
    """Every valid day's outcome for both directions, averaged per period. This is the comparison ('random').
    Using a window around each signal was biased: it includes the run-up/sell-off that created the signal
    (it made pure random-walk data 'pass'). A whole-period average has no such leak."""
    rows = [dict(day=d.index[j], sign=s, **outcome(d, j, s)) for j in range(210, len(d) - 21) for s in (-1, 1)]
    b = pd.DataFrame(rows)
    out = {}
    for pn, a, z in PERIODS:
        m = (b.day >= a) & (b.day < z)
        for s in (-1, 1):
            x = b[m & (b.sign == s)]
            if len(x):
                out[(pn, s)] = x.drop(columns=["day", "sign"]).mean().add_prefix("ctrl_").to_dict()
    return out


def period_of(day):
    for pn, a, z in PERIODS:
        if pd.Timestamp(a) <= day < pd.Timestamp(z):
            return pn


def add(out, setup, sign, sym, grp, d, j, **tags):
    if j < 210 or j + 21 >= len(d):
        return
    out.append(dict(setup=setup, side="calls" if sign > 0 else "puts", symbol=sym, group=grp, date=d.index[j],
                    **tags, **outcome(d, j, sign), **d.attrs["base"].get((period_of(d.index[j]), sign), {})))


# ------------------------------------------------------------------ indicators
def prep(d):
    d = d.copy()
    for n in (10, 20, 50, 200):
        d[f"s{n}"] = d.c.rolling(n).mean()
    delta = d.c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    d["rsi"] = 100 - 100 / (1 + up / dn)
    pc = d.c.shift()
    tr = pd.concat([d.h - d.l, (d.h - pc).abs(), (d.l - pc).abs()], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    d["v50"] = d.v.rolling(50).mean()
    return d


# ------------------------------------------------------------------ setups
def setup_B(sym, grp, d, out, calib):
    c, h, l = d.c, d.h, d.l
    s10, s20, s50, s200 = d.s10, d.s20, d.s50, d.s200
    gap = (s50 / s200 - 1) * 100
    bunch = (pd.concat([s10, s20, s50], axis=1).max(axis=1) - pd.concat([s10, s20, s50], axis=1).min(axis=1)) / c * 100
    gc = ((s50 > s200) & (s50.shift() <= s200.shift())).rolling(30, min_periods=1).max().astype(bool)
    dc = ((s50 < s200) & (s50.shift() >= s200.shift())).rolling(30, min_periods=1).max().astype(bool)
    into_gc = gc | ((s50 < s200) & (s50 >= s200 * 0.98) & (s50 > s50.shift(5)))
    into_dc = dc | ((s50 > s200) & (s50 <= s200 * 1.02) & (s50 < s50.shift(5)))
    for side, sign in (("down", -1), ("up", +1)):
        b3 = ((c < s10) & (c < s20) & (c < s50)) if side == "down" else ((c > s10) & (c > s20) & (c > s50))
        fire = b3 & ~b3.shift(2, fill_value=False)
        last = -99
        for j in np.where(fire.values)[0]:
            if j - last < 10 or j < 210 or j + 22 >= len(d):
                continue
            last = j
            tags = dict(gap=gap.iloc[j], bunch=bunch.iloc[j],
                        against_cross=bool(into_gc.iloc[j] if side == "down" else into_dc.iloc[j]))
            name = "B_down" if side == "down" else "B_up"
            add(out, name + "_break", sign, sym, grp, d, j, **tags)
            follow = bool(c.iloc[j + 1] < c.iloc[j]) if side == "down" else bool(c.iloc[j + 1] > c.iloc[j])
            add(out, name + "_next", sign, sym, grp, d, j + 1, follow=follow, **tags)
            for q in range(j + 1, min(j + 8, len(d) - 22)):
                hit = (h.iloc[q] >= s10.iloc[q] and c.iloc[q] < s10.iloc[q]) if side == "down" else \
                      (l.iloc[q] <= s10.iloc[q] and c.iloc[q] > s10.iloc[q])
                if hit:
                    add(out, name + "_retest", sign, sym, grp, d, q, **tags); break
            if side == "down" and gap.iloc[j] < 0:
                add(out, "B_down_50under200_CALLS", +1, sym, grp, d, j, **tags)
            if sym == "QQQ" and side == "down":
                calib.append(d.index[j])


def setup_A(sym, grp, d, out, counts, wk_rows):
    X = 0.06 if grp == "ETF" else 0.12
    XW = 0.10 if grp == "ETF" else 0.20
    h, l = d.h.values, d.l.values
    n = len(d)
    lastb = lastt = -99
    for i in range(45, n - 30):
        if l[i] == l[i - 5:i + 6].min() and h[i - 40:i].max() >= l[i] * (1 + X) and i - lastb > 5:
            lastb = i
            counts.append((grp, "daily bottom", int(h[i + 1:i + 26].argmax()) + 1))
            add(out, "A_bottom_d6to8_CALLS", +1, sym, grp, d, i + 7, k=7)     # one entry per bottom (bar 7)
            add(out, "A_bottom_d9to11_PUTS", -1, sym, grp, d, i + 10, k=10)   # one entry per bottom (bar 10)
        if h[i] == h[i - 5:i + 6].max() and l[i - 40:i].min() <= h[i] / (1 + X) and i - lastt > 5:
            lastt = i
            add(out, "A_top_d6to10_PUTS", -1, sym, grp, d, i + 8, k=8)
    # weekly
    w = d.resample("W-FRI").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    pos = d.index.get_indexer(w.index, method="ffill")        # daily row of each week's last session
    wh, wl, wo, wc = w.h.values, w.l.values, w.o.values, w.c.values
    base_red = (wc < wo).mean()
    lastw = -99
    for i in range(30, len(w) - 20):
        if wl[i] != wl[i - 3:i + 4].min() or wh[i - 26:i].max() < wl[i] * (1 + XW) or i - lastw <= 3:
            continue
        lastw = i
        counts.append((grp, "weekly bottom", int(wh[i + 1:i + 26].argmax()) + 1))
        add(out, "A_week4to6_CALLS", +1, sym, grp, d, int(pos[i + 5]), k=5)
        add(out, "A_week9to11_PUTS", -1, sym, grp, d, int(pos[i + 10]), k=10)
        wk_rows.append(dict(group=grp, symbol=sym, wk11_red=bool(wc[i + 11] < wo[i + 11]),
                            red_13_16=(wc[i + 13:i + 17] < wo[i + 13:i + 17]).mean(), base_red=base_red,
                            move_12_16=(wc[i + 16] / wc[i + 12] - 1) * 100))


def setup_C(sym, grp, d, out):
    X = 0.06 if grp == "ETF" else 0.10
    c, o, h, l, v, atr, v50 = (d[k].values for k in ("c", "o", "h", "l", "v", "atr", "v50"))
    if np.nanmax(v) <= 0:
        return
    last = {"dn": -99, "up": -99}
    for i in range(80, len(d) - 22):
        red, green = c[i] < o[i] and c[i] < c[i - 1], c[i] > o[i] and c[i] > c[i - 1]
        if not (red or green):
            continue
        best = None
        for nb in range(15, 2, -1):
            w = slice(i - nb, i)
            if h[w].max() - l[w].min() <= 2.5 * atr[i - 1] and v[w].mean() <= v50[i - 1]:
                best = nb; break
        if best is None:
            continue
        cv = v[i - best:i].mean()
        if not cv > 0:
            continue
        ratio = v[i] / cv
        if ratio < 1.7:
            continue
        start = i - best
        if red and c[start] >= (1 + X) * l[max(0, start - 40):start].min() and i - last["dn"] >= 10:
            last["dn"] = i
            add(out, "C_volume_dump_PUTS", -1, sym, grp, d, i, consol=best, ratio=ratio)
        if green and c[start] <= (1 - X) * h[max(0, start - 40):start].max() and i - last["up"] >= 10:
            last["up"] = i
            add(out, "C_volume_breakout_CALLS", +1, sym, grp, d, i, consol=best, ratio=ratio)


def setup_R(sym, grp, d, out):
    r = d.rsi.values
    for name, cond, sign in (("R_rsi80_PUTS", r >= 80, -1), ("R_rsi70_PUTS", r >= 70, -1),
                             ("R_rsi30_CALLS", r <= 30, +1), ("R_rsi25_CALLS", r <= 25, +1)):
        last = -99
        for j in np.where(cond)[0]:
            if j > 0 and not cond[j - 1] and j - last >= 10:   # first close at the extreme, 10-day cooldown
                add(out, name, sign, sym, grp, d, j)
                last = j


# ------------------------------------------------------------------ report
def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); dd = pd.Series(np.asarray(dates))
    ok = x.notna(); x, dd = x[ok], dd[ok]
    dm = x.groupby(pd.DatetimeIndex(dd.values).to_period("M")).mean()   # monthly clusters: overlapping trades can't inflate t
    if len(dm) < 5 or dm.std() == 0:
        return float("nan")
    return dm.mean() / (dm.std(ddof=1) / math.sqrt(len(dm)))


def row(name, x):
    if len(x) < 8:
        return f"| {name} | {len(x)} | — | — | — | — |"
    cells = [f"| {name} | {len(x)} |"]
    for n in (5, 10, 20):
        e = x[f"x{n}"] - x[f"ctrl_x{n}"]
        cells.append(f" {x[f'x{n}'].mean():+.2f}% vs {x[f'ctrl_x{n}'].mean():+.2f}% → **{e.mean():+.2f}** (t {tcl(e, x.date.values):.1f}) |")
    cells.append(f" {x.hit3.mean():.0%} vs {x.ctrl_hit3.mean():.0%} |")
    return "".join(cells)


HDR = ("| Group | Count | 5 days: your-way move vs random → edge | 10 days | 20 days | Moved 3%+ your way in 10 days |\n"
       "|---|---|---|---|---|---|")


def per(x, a, b):
    return x[(x.date >= a) & (x.date < b)]


def block(L, E, setup, title, splits=()):
    X = E[E.setup == setup]
    L += [f"\n### {title}\n", HDR, row("QQQ alone (all years)", X[X.symbol == "QQQ"])]
    etf = X[X.group == "ETF"]
    for pn, a, b in PERIODS:
        L.append(row(f"ETFs {pn}", per(etf, a, b)))
    L.append(row("**ETFs all years**", etf))
    for lab, f in splits:
        L.append(row(f"ETFs: {lab}", etf[f(etf)]))
    L.append(row("Mega tech all years", X[X.group == "MEGA"]))


def verdict(E, setup, grp):
    X = E[(E.setup == setup) & (E.group == grp)]
    e = X.x10 - X.ctrl_x10
    pe = [(per(X, a, b).x10 - per(X, a, b).ctrl_x10).mean() for _, a, b in PERIODS]
    t = tcl(e, X.date.values) if len(X) >= 8 else float("nan")
    ok = all(pd.notna(p) and p > 0 for p in pe) and pd.notna(t) and t >= 3 and len(X) >= 100
    return f"{' / '.join('—' if pd.isna(p) else f'{p:+.2f}' for p in pe)} | {e.mean():+.2f} (t {t:.1f}, n {len(X)}) | {'**PASS**' if ok else 'fail'}"


def report(E, W, counts, calib, srcs):
    E = E.copy(); E["date"] = pd.to_datetime(E.date)
    for col in ("against_cross", "follow"):
        if col in E:
            E[col] = E[col].fillna(False).astype(bool)
    L = ["# QQQ + tech — every chart rule, puts and calls", "",
         "Raw moves of the actual symbol (no SPY adjustment). 'Your-way move' = how far it moved in the trade's direction "
         "(puts: down, calls: up). Random = that symbol's average move over ALL days of the same period (2000-15 / 16-21 / 22-26). Edge = setup minus that. t clustered by month (overlapping trades counted once).", "",
         "Data: " + ", ".join(f"{s} from {v}" for s, v in srcs.items()), ""]
    # pass table first
    L += ["## PASS CHECK (set before running): 10-day edge > 0 in EVERY period AND t >= 3 all years AND 100+ events", "",
          "| Setup | Group | 10-day edge 2000-15 / 16-21 / 22-26 | All years | Verdict |", "|---|---|---|---|---|"]
    names = [("B_down_break", "Triple break DOWN → puts"), ("B_down_retest", "Failed retest of the 10 → puts"),
             ("B_down_50under200_CALLS", "Triple break DOWN while 50<200 → CALLS"),
             ("B_up_break", "Triple break UP → calls"), ("B_up_retest", "Retest of the 10 from above → calls"),
             ("A_bottom_d6to8_CALLS", "Bars 6-8 after a daily bottom → calls"),
             ("A_bottom_d9to11_PUTS", "Bars 9-11 after a daily bottom → puts"),
             ("A_top_d6to10_PUTS", "Bars 6-10 after a daily top → puts"),
             ("A_week4to6_CALLS", "Weeks 4-6 after a weekly bottom → calls"),
             ("A_week9to11_PUTS", "Weeks 9-11 after a weekly bottom → puts"),
             ("C_volume_dump_PUTS", "Volume dump → puts"), ("C_volume_breakout_CALLS", "Volume breakout → calls"),
             ("R_rsi80_PUTS", "Daily RSI 80 → puts"), ("R_rsi70_PUTS", "Daily RSI 70 → puts"),
             ("R_rsi30_CALLS", "Daily RSI 30 → calls"), ("R_rsi25_CALLS", "Daily RSI 25 → calls")]
    for s, lab in names:
        for g in ("ETF", "MEGA"):
            L.append(f"| {lab} | {g} | {verdict(E, s, g)} |")
    # calibration
    L += ["\n## Your QQQ dates vs the triple-break-down rule\n"]
    cal = pd.DatetimeIndex(calib)
    for ds in QQQ_DATES:
        t = pd.Timestamp(ds)
        hit = [x for x in cal if -1 <= (x - t).days <= 5]
        L.append(f"- {ds}: {'fired ' + ', '.join(f'{x:%b %d}' for x in hit) if hit else 'no fire (an earlier fire within 10 days may have covered it)'}")
    gap_splits = [("50 under the 200", lambda x: x.gap < 0), ("50 0-5% over the 200", lambda x: x.gap.between(0, 5, inclusive="left")),
                  ("50 5-10% over", lambda x: x.gap.between(5, 10, inclusive="left")), ("50 10%+ over", lambda x: x.gap >= 10)]
    L += ["\n## B. Triple MA break"]
    block(L, E, "B_down_break", "DOWN break → puts (entry at the break close)",
          [("NOT into a golden cross", lambda x: ~x.against_cross), ("INTO a golden cross", lambda x: x.against_cross)]
          + gap_splits + [("bunched under 2%", lambda x: x.bunch < 2), ("bunched 2%+", lambda x: x.bunch >= 2)])
    block(L, E, "B_down_next", "DOWN break, entry next close", [("next day closed lower", lambda x: x.follow),
                                                                 ("next day bounced", lambda x: ~x.follow)])
    block(L, E, "B_down_retest", "DOWN break, failed retest of the 10 → puts")
    block(L, E, "B_down_50under200_CALLS", "DOWN break while the 50 is under the 200 → CALLS (bounce)")
    block(L, E, "B_up_break", "UP break → calls (entry at the break close)",
          [("NOT into a death cross", lambda x: ~x.against_cross), ("INTO a death cross", lambda x: x.against_cross)]
          + gap_splits + [("bunched under 2%", lambda x: x.bunch < 2), ("bunched 2%+", lambda x: x.bunch >= 2)])
    block(L, E, "B_up_next", "UP break, entry next close", [("next day closed higher", lambda x: x.follow),
                                                             ("next day pulled back", lambda x: ~x.follow)])
    block(L, E, "B_up_retest", "UP break, retest of the 10 from above → calls")
    # A
    C = pd.DataFrame(counts, columns=["group", "kind", "top_bar"])
    L += ["\n## A. Counting bars\n", "Which bar the move topped out on (bars 1-25). Random would put ~12% on bars 9-11.\n",
          "| Group | Kind | Count | Top on bar 9-11 | Bar 10 exactly | Median top bar |", "|---|---|---|---|---|---|"]
    for (g, k), x in C.groupby(["group", "kind"]):
        L.append(f"| {g} | {k} | {len(x)} | {x.top_bar.between(9, 11).mean():.0%} | {(x.top_bar == 10).mean():.0%} | {x.top_bar.median():.0f} |")
    for s, t in (("A_bottom_d6to8_CALLS", "Daily bottom, bars 6-8 → calls"), ("A_bottom_d9to11_PUTS", "Daily bottom, bars 9-11 → puts"),
                 ("A_top_d6to10_PUTS", "Daily top, bars 6-10 → puts"), ("A_week4to6_CALLS", "Weekly bottom, weeks 4-6 → calls"),
                 ("A_week9to11_PUTS", "Weekly bottom, weeks 9-11 → puts")):
        block(L, E, s, t)
    if len(W):
        L += ["\n### Weekly: after week 11 closes red\n", "| Group | Case | Bottoms | Weeks 13-16 red | Normal red share | Move week 12→16 |",
              "|---|---|---|---|---|---|"]
        for g, x in W.groupby("group"):
            for lab, m in (("week 11 red", x.wk11_red), ("week 11 green", ~x.wk11_red)):
                y = x[m]
                if len(y):
                    L.append(f"| {g} | {lab} | {len(y)} | {y.red_13_16.mean():.0%} | {y.base_red.mean():.0%} | {y.move_12_16.mean():+.2f}% |")
    L += ["\n## C. Quiet consolidation → volume candle"]
    vol_splits = [("volume 1.7-2x", lambda x: x.ratio < 2), ("volume 2-3x", lambda x: x.ratio.between(2, 3, inclusive="left")),
                  ("volume 3x+", lambda x: x.ratio >= 3), ("consolidation 3-8 days", lambda x: x.consol <= 8),
                  ("consolidation 9-11 days", lambda x: x.consol.between(9, 11)), ("consolidation 12-15 days", lambda x: x.consol >= 12)]
    block(L, E, "C_volume_dump_PUTS", "Volume DUMP after a rally → puts", vol_splits)
    block(L, E, "C_volume_breakout_CALLS", "Volume BREAKOUT after a decline → calls", vol_splits)
    L += ["\n## R. Daily RSI extremes"]
    for s, t in (("R_rsi80_PUTS", "RSI 80 → puts"), ("R_rsi70_PUTS", "RSI 70 → puts"),
                 ("R_rsi30_CALLS", "RSI 30 → calls"), ("R_rsi25_CALLS", "RSI 25 → calls")):
        block(L, E, s, t)
    # QQQ event list for the two main setups
    L += ["\n## QQQ triple breaks since 2022 (raw moves, for eyeballing)\n",
          "| Date | Side | 50 vs 200 | Bunch | 10-day your-way | 20-day your-way | 3%+ your way in 10d |", "|---|---|---|---|---|---|---|"]
    q = E[(E.symbol == "QQQ") & E.setup.isin(["B_down_break", "B_up_break"]) & (E.date >= "2022-01-01")].sort_values("date")
    for r in q.itertuples():
        L.append(f"| {r.date:%Y-%m-%d} | {'DOWN→puts' if r.setup == 'B_down_break' else 'UP→calls'} | {r.gap:+.1f}% | {r.bunch:.1f}% | "
                 f"{r.x10:+.2f}% | {r.x20:+.2f}% | {'yes' if r.hit3 else 'no'} |")
    L += ["", "Limits: ~30 setups x groups were checked, so expect a false 'good-looking' row or two by luck — the pass rule "
          "(every period positive + t >= 3 + 100 events) is there for that. Stock/ETF moves, not option P&L. Mega tech = winners we already know."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    os.makedirs(OUT, exist_ok=True)
    E, W, counts, calib, srcs = [], [], [], [], {}
    for grp, syms in (("ETF", IDX_ETF), ("MEGA", MEGA)):
        for s in syms:
            d, src = load(s)
            if d is None or len(d) < 400:
                print(f"  {s}: no data"); continue
            srcs[s] = f"{src} {d.index[0]:%Y}"
            d = prep(d)
            d.attrs["base"] = baseline(d)
            setup_B(s, grp, d, E, calib); setup_A(s, grp, d, E, counts, W); setup_C(s, grp, d, E); setup_R(s, grp, d, E)
            print(f"  {s}: {len(d)} days from {d.index[0]:%Y-%m-%d} ({src}); events so far {len(E)}", flush=True)
    E = pd.DataFrame(E)
    E.to_csv(f"{OUT}/events.csv.gz", index=False, compression="gzip")
    report(E, pd.DataFrame(W), counts, calib, srcs)


if __name__ == "__main__":
    main()
