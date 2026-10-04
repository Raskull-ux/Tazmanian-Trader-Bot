"""
Tazmanian Trader — Event Study (which conditions actually matter)
=================================================================
The strict setup backtest required 6 conditions at once and almost never
fired. This script flips the approach: it records EVERY intraday rejection
near the high of day across the universe, measures the conditions Taz uses
as features, and then measures which features actually lead to profitable
puts. The data picks the rule; Taz's charts tell us what to measure.

Base event (5-min bars, 09:45-15:30 ET, max 2 per name per day, 30 min apart):
  - the day has run up: high of day >= open + 2 ATR
  - price is within 3 ATR of the high of day
  - rejection bar: closes below the prior bar's low AND below the 10 SMA

Features recorded at the event (all from Taz's charts / framework):
  run_atr        size of the run-up from the open, in ATR
  consol         bars price has held within 1.5 ATR of the high (consolidation)
  div_pts        RSI divergence: earlier RSI peak minus recent RSI peak (points)
  box_break      close below the lowest low of the prior 6 bars
  ma_cross       10 SMA crossed below 20 SMA within the last 3 bars
  rsi_below_ma   RSI(14) under its 14-bar MA
  ext50_atr      distance above the 5-min 50 SMA, in ATR
  below200       close under the 5-min 200 SMA
  room_atr       distance down to T1 (nearest Taz level below), in ATR
  above_d8       price above the daily 8 SMA (Taz's daily target)
  hour           entry hour

Outcomes (put direction):
  r30 / r60      stock move after 30 / 60 minutes
  r_eod          stock move to 15:55
  opt1_50        1-day ATM put, take +50%, else exit on 5-min close above the
                 50 SMA or at 15:55 the same day
  opt3_30_hold   3-day ATM put, take +30%, else same stop, held through the
                 NEXT day's close (Taz holds overnight)
  opt7_30_hold   7-day ATM put, same, +30%

Selection is walk-forward: filters are chosen on the first 2/3 of the period
and scored on the last 1/3 only.

Env: ALPACA keys. Opt: SYMBOLS, MAX_SYMBOLS (300), MONTHS (9), OPT_COST (0.04)
Out: results/event_study/{report.md, events.csv}
"""
from __future__ import annotations
import os, math
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
from scipy.special import ndtr

import setup_backtest as sb   # reuse fetch / indicators

OUT = "results/event_study"
MONTHS = int(os.environ.get("MONTHS", 9))
MAX_SYMBOLS = int(os.environ.get("MAX_SYMBOLS", 300))
COST = float(os.environ.get("OPT_COST", 0.04))
CHUNK = 40


def bs_put_vec(S, K, T, sig):
    T = np.maximum(T, 1e-6)
    v = sig * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * v * v) / v
    return K * ndtr(-(d1 - v)) - S * ndtr(-d1)


def minutes_left(tod_min):
    return np.maximum(960 - tod_min, 5)


def events_for_symbol(sym, b5, b1h, b1d):
    if len(b5) < 400:
        return []
    b = sb.prep_5m(b5)
    pc = b["c"].shift()
    tr = np.maximum(b["h"] - b["l"], np.maximum((b["h"] - pc).abs(), (b["l"] - pc).abs()))
    b["atr"] = tr.rolling(14).mean()
    c, h, l, o = (b[k].values for k in ("c", "h", "l", "o"))
    s10, s20, s50, s200 = (b[f"sma{n}"].values for n in (10, 20, 50, 200))
    r, rma, atr = b["rsi"].values, b["rsima"].values, b["atr"].values
    tmin = (b["t"].dt.hour * 60 + b["t"].dt.minute).values
    cross = (s10 < s20) & (np.roll(s10, 1) >= np.roll(s20, 1))

    d = b1d.sort_values("t").copy()
    d["day"] = d["t"].dt.date
    d["sma8"] = d["c"].rolling(8).mean()
    d["rv"] = (np.log(d["c"]).diff().rolling(20).std() * math.sqrt(252) * 1.15).clip(lower=0.15)
    prev = {dy: (pl, pcl, ps8, rv) for dy, pl, pcl, ps8, rv in
            zip(d["day"], d["l"].shift(), d["c"].shift(), d["sma8"].shift(), d["rv"].shift())}
    hh = b1h.sort_values("t").copy()
    for n in (50, 100, 200):
        hh[f"h{n}"] = hh["c"].rolling(n).mean()
    h_av = (hh["t"] + pd.Timedelta(hours=1)).values

    rth = b[b["rth"]]
    days = list(rth.groupby("day").groups.items())
    day_pos = {dy: k for k, (dy, _) in enumerate(days)}
    out = []
    for dy, idx in days:
        idx = np.asarray(idx)
        if dy not in prev or len(idx) < 30:
            continue
        pl, pcl, ps8, rv = prev[dy]
        if not rv == rv:
            continue
        nxt = days[day_pos[dy] + 1][1] if day_pos[dy] + 1 < len(days) else np.array([], dtype=int)
        path_all = np.concatenate([idx, np.asarray(nxt)])
        day_open = o[idx[0]]
        hod = np.maximum.accumulate(h[idx]); lod = np.minimum.accumulate(l[idx])
        last_j, count = -99, 0
        for j in range(12, len(idx)):
            i = idx[j]
            if not (585 <= tmin[i] <= 930) or count >= 2 or j - last_j < 6:
                continue
            a = atr[i]
            if not a > 0 or i < 30:
                continue
            hp = hod[j - 1]
            if not (hp >= day_open + 2 * a and c[i] >= hp - 3 * a):
                continue
            if not (c[i] < l[i - 1] and c[i] < s10[i]):
                continue
            last_j, count = j, count + 1
            # features
            k = j - 1; consol = 0
            while k >= 0 and c[idx[k]] >= hp - 1.5 * a and consol < 48:
                consol += 1; k -= 1
            div = np.nanmax(r[i - 24:i - 6]) - np.nanmax(r[i - 6:i])
            entry = c[i]
            levels = [lod[j - 1], pl, pcl, ps8]
            hk = np.searchsorted(h_av, b["t"].values[i], side="right") - 1
            if hk >= 0:
                levels += [hh[f"h{n}"].iat[hk] for n in (50, 100, 200)]
            below = [v for v in levels if v == v and v < entry * 0.999]
            t1 = max(below) if below else np.nan
            ev = dict(symbol=sym, date=str(dy), time=b["tod"].iat[i], entry=entry,
                      run_atr=(hp - day_open) / a, consol=consol, div_pts=div,
                      box_break=bool(c[i] < l[i - 6:i].min()),
                      ma_cross=bool(cross[i - 2:i + 1].any()),
                      rsi_below_ma=bool(r[i] < rma[i]),
                      ext50_atr=(c[i] - s50[i]) / a, below200=bool(c[i] < s200[i]),
                      room_atr=(entry - t1) / a if t1 == t1 else np.nan,
                      above_d8=bool(ps8 == ps8 and entry > ps8),
                      hour=int(tmin[i] // 60), iv=rv)
            # stock outcomes
            for nb, name in ((6, "r30"), (12, "r60")):
                ev[name] = (entry - c[idx[min(j + nb, len(idx) - 1)]]) / entry
            eod = [q for q in idx[j + 1:] if tmin[q] <= 955]
            ev["r_eod"] = (entry - c[eod[-1]]) / entry if eod else 0.0
            ev["mfe_day"] = (entry - l[idx[j + 1:]].min()) / entry if j + 1 < len(idx) else 0.0
            # option outcomes
            setup_high = h[idx[max(j - 6, 0):j]].max()
            ev.update(option_paths(c, s50, tmin, i, path_all, entry, rv, setup_high, len(idx)))
            out.append(ev)
    return out


def option_paths(c, s50, tmin, i, path_all, entry, sig, setup_high, n_today):
    pos = np.where(path_all == i)[0][0]
    fut = path_all[pos + 1:]
    res = {}
    if len(fut) == 0:
        return res
    cf = c[fut]
    below50 = c[i] < s50[i]
    stop_k = None
    for k, q in enumerate(fut):
        if c[q] < s50[q]:
            below50 = True
        if (c[q] > s50[q]) if below50 else (c[q] > setup_high):
            stop_k = k; break
    today_n = max(n_today - (pos + 1), 0)          # bars left today after entry
    day_idx = np.r_[np.zeros(today_n), np.ones(len(fut) - today_n)]
    for dte, tg, hold, name in ((1, 0.50, False, "opt1_50"), (3, 0.30, True, "opt3_30_hold"),
                                (7, 0.30, True, "opt7_30_hold")):
        last = today_n - 1 if not hold else len(fut) - 1
        if last < 0:
            continue
        end = last if stop_k is None else min(last, stop_k)
        T = (minutes_left(tmin[fut[:end + 1]]) + 390 * np.maximum(dte - day_idx[:end + 1], 0)) / (390 * 252)
        T0 = (minutes_left(tmin[i]) + 390 * dte) / (390 * 252)
        p0 = bs_put_vec(np.array([entry]), entry, np.array([T0]), sig)[0]
        if p0 <= 0.01:
            continue
        pr = bs_put_vec(cf[:end + 1], entry, T, sig) / p0 - 1
        hit = np.where(pr >= tg)[0]
        res[name] = (tg if len(hit) else pr[-1]) - COST
        res[name + "_hit"] = bool(len(hit))
    return res


# ------------------------------------------------------------------ analysis
OUTCOMES = ["opt1_50", "opt3_30_hold", "opt7_30_hold", "r_eod"]


def tstat(x):
    x = x.dropna()
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def row(name, x):
    cells = [f"{len(x)}"]
    for o in OUTCOMES:
        if o not in x:
            cells.append("—"); continue
        v = x[o].dropna()
        hit = x.get(o + "_hit")
        hs = f"{hit.dropna().astype(bool).mean():.0%} hit, " if hit is not None and len(v) else ""
        scale = 100
        cells.append(f"{hs}{v.mean()*scale:+.1f}% (t {tstat(v):.1f})" if len(v) else "—")
    return f"| {name} | " + " | ".join(cells) + " |"


HDR = ("| Condition | Events | 1-day put +50% | 3-day put +30%, hold to next day | "
       "7-day put +30%, hold | Stock move to 3:55 |\n|---|---|---|---|---|---|")


def buckets(df):
    B = {
        "run_atr": [("run 2-4 ATR", df.run_atr < 4), ("run 4-7 ATR", df.run_atr.between(4, 7)),
                    ("run 7+ ATR", df.run_atr > 7)],
        "consol": [("consolidation 0-2 bars", df.consol <= 2), ("3-8 bars", df.consol.between(3, 8)),
                   ("9-20 bars", df.consol.between(9, 20)), ("21+ bars", df.consol > 20)],
        "div_pts": [("no divergence (<0)", df.div_pts < 0), ("divergence 0-5", df.div_pts.between(0, 5)),
                    ("divergence 5-10", df.div_pts.between(5, 10)), ("divergence 10+", df.div_pts > 10)],
        "box_break": [("box break yes", df.box_break), ("box break no", ~df.box_break)],
        "ma_cross": [("10/20 cross yes", df.ma_cross), ("10/20 cross no", ~df.ma_cross)],
        "rsi_below_ma": [("RSI under its MA", df.rsi_below_ma), ("RSI over its MA", ~df.rsi_below_ma)],
        "ext50_atr": [("below 50 SMA", df.ext50_atr < 0), ("0-2 ATR above 50", df.ext50_atr.between(0, 2)),
                      ("2-4 ATR above 50", df.ext50_atr.between(2, 4)), ("4+ ATR above 50", df.ext50_atr > 4)],
        "below200": [("under 5m 200 SMA", df.below200), ("over 5m 200 SMA", ~df.below200)],
        "room_atr": [("T1 room <2 ATR", df.room_atr < 2), ("room 2-5 ATR", df.room_atr.between(2, 5)),
                     ("room 5+ ATR", df.room_atr > 5)],
        "above_d8": [("above daily 8 SMA", df.above_d8), ("below daily 8 SMA", ~df.above_d8)],
        "hour": [(f"{hh}:00 hour", df.hour == hh) for hh in range(9, 16)],
    }
    return B


def pick_rule(train, metric="opt3_30_hold", min_n=60):
    """Greedy: add the single bucket that most improves the train average, up to 3."""
    chosen, cur = [], pd.Series(True, index=train.index)
    allb = [(f, n, m) for f, lst in buckets(train).items() for n, m in lst]
    for _ in range(3):
        best = None
        base = train.loc[cur, metric].mean()
        for f, n, m in allb:
            if f in [x[0] for x in chosen]:
                continue
            sel = cur & m.reindex(train.index, fill_value=False)
            if sel.sum() < min_n:
                continue
            v = train.loc[sel, metric].mean()
            if v > base + 0.005 and (best is None or v > best[3]):
                best = (f, n, sel, v)
        if best is None:
            break
        chosen.append((best[0], best[1])); cur = best[2]
    return chosen


def apply_rule(df, rule):
    m = pd.Series(True, index=df.index)
    B = buckets(df)
    for f, n in rule:
        m &= dict(B[f])[n]
    return df[m]


def report(df, start, end, nsym, split):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(f"{OUT}/events.csv", index=False)
    L = [f"# Event Study — {start} to {end}",
         f"\n{nsym} names, 5-min SIP bars. Base event: rejection bar within 3 ATR of the high "
         "of day after a 2+ ATR run from the open. Option columns are Black-Scholes estimates "
         f"(realized-vol IV proxy, {COST:.0%} round-trip cost). Each cell: average return per trade (t-stat).\n",
         "## Every event (baseline)\n", HDR, row("all events", df)]
    for f, lst in buckets(df).items():
        L += [f"\n## {f}\n", HDR] + [row(n, df[m]) for n, m in lst if m.sum() > 0]
    train, test = df[df.date < split], df[df.date >= split]
    L.append(f"\n## Walk-forward rule (picked on events before {split}, scored after)\n")
    for metric in ("opt3_30_hold", "opt1_50"):
        rule = pick_rule(train, metric)
        desc = " AND ".join(n for _, n in rule) or "(no filter beat the baseline)"
        tr, te = apply_rule(train, rule), apply_rule(test, rule)
        L += [f"**Target: {metric}** — rule: {desc}\n", HDR,
              row("train, rule", tr), row("TEST, rule", te), row("TEST, all events", test), ""]
    L.append("Only TEST rows count. Pass bar: TEST t ≥ 3 on the option column before going live.")
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


def main():
    end_dt = datetime.now(timezone.utc) - timedelta(minutes=20)
    start_dt = end_dt - timedelta(days=int(MONTHS * 30.5))
    warm = start_dt - timedelta(days=60)
    s, e = start_dt.date().isoformat(), end_dt.isoformat()
    if os.environ.get("SYMBOLS"):
        syms = [x.strip().upper() for x in os.environ["SYMBOLS"].split(",") if x.strip()]
    else:
        u = pd.read_csv("universe/universe.csv")
        u = u[u["group"] != "gauge"].sort_values("avg_dollar_vol", ascending=False)
        syms = u["symbol"].head(MAX_SYMBOLS).tolist()
    print(f"Event study {s} -> {e[:10]}, {len(syms)} symbols")
    # resume: progress is saved after every chunk, so a cancelled or timed-out run
    # picks up where it stopped (delete results/event_study/ to start fresh)
    os.makedirs(OUT, exist_ok=True)
    part, donef = f"{OUT}/events_partial.csv", f"{OUT}/done_symbols.txt"
    ev, done = [], set()
    if os.path.exists(part) and os.path.exists(donef):
        ev = pd.read_csv(part).to_dict("records")
        done = set(open(donef).read().split())
        print(f"Resuming: {len(done)} symbols already done, {len(ev)} events loaded")
    syms_todo = [x for x in syms if x not in done]
    for ci in range(0, len(syms_todo), CHUNK):
        ch = syms_todo[ci:ci + CHUNK]
        try:
            m5 = sb.fetch(ch, "5Min", warm.date().isoformat(), e)
            h1 = sb.fetch(ch, "1Hour", (warm - timedelta(days=60)).date().isoformat(), e)
            d1 = sb.fetch(ch, "1Day", (warm - timedelta(days=30)).date().isoformat(), e)
        except Exception as ex:
            print(f"  chunk {ci}: {ex}"); continue
        for sym in ch:
            try:
                ev += [x for x in events_for_symbol(sym, m5[m5.symbol == sym], h1[h1.symbol == sym],
                                                    d1[d1.symbol == sym]) if x["date"] >= s]
            except Exception as ex:
                print(f"  {sym}: {ex}")
        pd.DataFrame(ev).to_csv(part, index=False)
        done |= set(ch)
        open(donef, "w").write("\n".join(sorted(done)))
        print(f"  {len(done)}/{len(syms)} symbols done, {len(ev)} events (progress saved)")
    df = pd.DataFrame(ev)
    if df.empty:
        print("No events."); return
    split = (pd.Timestamp(s) + (pd.Timestamp(e[:10]) - pd.Timestamp(s)) * 2 / 3).date().isoformat()
    report(df, s, e[:10], len(syms), split)


if __name__ == "__main__":
    main()
