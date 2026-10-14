"""
EXIT SEARCH, STAGE 2: real option prices for every stage-1 survivor, traded with ITS exit rule (stock levels).

Reads results/exit_search/candidates.csv (survivors only, up to 10). For each survivor, every signal since Feb 2024 on
its names (up to 250, spread over time), traded exactly as stage 1 found: entry at the signal bar close, exit when the
STOCK hits the target level, the stop close, or the time limit. Split entries buy the second half when the stock
touches the add level, at the option's real price at that minute.
Contract: expiry at least 7 days out and after the exit (no 0DTE), ATM and 0.5% OTM, flagged under/over $500.
Prices: Alpaca 1-minute option trades, first print at/after the planned minute (within 30 min).
Spread: flat $0.03 per side (stress $0.06).
Also measured: how high the option ran between entry and exit (peak), and how often it reached +100%.
Random: the paired random trade from stage 1 (same slot, VIX state, same target/stop distances) on 2024+ days.
VERDICT (set before running): 30+ signal days, average > 0 AND above random, t >= 2.5 on both (t clustered by day).
Out: results/exit_options/report.md, trades.csv
"""
from __future__ import annotations
import os, math
import numpy as np, pandas as pd
import edge_search as es
import exit_search as xs
import option_reality as orl

OUT = "results/exit_options"
SRC = "results/exit_search/candidates.csv"
START = pd.Timestamp("2024-02-01")
MAX_SURV, MAX_EV, WITHIN = 10, 250, 30
COST, STRESS = 0.03, 0.06


def one(gi, LV, sgn, cb, G, D):
    """Exit position, target hit, add position for ONE combo (same rules as stage 1)."""
    Hf, Lf, Cf = G["h"].ravel(), G["l"].ravel(), G["c"].ravel()
    n = len(gi); last = len(Cf) - 1
    idx = np.minimum(gi[:, None] + np.arange(1, xs.MAXB + 1)[None, :], last)
    Hp, Lp, Cp = Hf[idx], Lf[idx], Cf[idx]; slot = idx % xs.SL; d = gi // xs.SL
    up = sgn > 0
    T = (LV["T_up"] if up else LV["T_dn"])[:, cb["ti"]]
    S = LV["S_up"] if up else LV["S_dn"]; A = LV["A_up"] if up else LV["A_dn"]
    tg = xs.first_idx((Hp >= T[:, None]) if up else (Lp <= T[:, None]))
    if cb["stop"] == "none":
        st = np.full(n, xs.BIG)
    else:
        lvl = A[:, 1] if cb["stop"] == "2nd level" else S[:, xs.STOPS.index(cb["stop"])]
        br = (Cp < lvl[:, None]) if up else (Cp > lvl[:, None])
        st = xs.first_idx(br & xs.TFS[cb["tf"]][slot])
    k = xs.TIMES[cb["time"]]
    e = (d + k) * xs.SL + (xs.SL - 1) - gi - 1
    ok = (d + k < D) & (e >= 0) & np.isfinite(T)
    e = np.minimum(e, xs.MAXB - 1)
    stop_first = (st <= tg) & (st <= e); targ = (tg < st) & (tg <= e)
    x = np.clip(np.where(stop_first, st, np.where(targ, tg, e)), 0, xs.MAXB - 1)
    add = xs.first_idx((Lp <= A[:, 0:1]) if up else (Hp >= A[:, 0:1])) if cb["entry"] == "split" else np.full(n, xs.BIG)
    if cb["entry"] == "split":
        ok &= np.isfinite(A[:, 1])
    return x, targ & ~stop_first, add, ok


def ts_of(days, g):
    return days[g // xs.SL] + pd.to_timedelta(570 + 5 * (g % xs.SL + 1), unit="m")


def price_window(b, t):
    x = b[(b.t >= t) & (b.t <= t + pd.Timedelta(minutes=WITHIN))]
    if len(x):
        return float(x.c.iloc[0])
    x = b[(b.t <= t) & (b.t >= t.normalize())]
    return float(x.c.iloc[-1]) if len(x) else np.nan


def option_trade(sym, cp, t_in, t_out, t_add, spot):
    C = orl.contracts(sym, t_in.normalize(), cp, spot)
    if not len(C):
        return []
    need = max(t_in.normalize() + pd.Timedelta(days=7), t_out.normalize())
    c = C[C.exp >= need]
    if not len(c):
        return []
    c = c[c.exp == c.exp.min()]
    atm = c.iloc[(c.k - spot).abs().argmin()]
    o5 = c[c.k >= spot * 1.005].sort_values("k") if cp == "C" else c[c.k <= spot * 0.995].sort_values("k", ascending=False)
    legs = [("ATM", atm)] + ([("0.5% OTM", o5.iloc[0])] if len(o5) else [])
    B = orl.option_bars(sorted({l.occ for _, l in legs}), t_in.normalize() + pd.Timedelta(hours=9, minutes=30),
                        t_out + pd.Timedelta(minutes=WITHIN + 5))
    rows = []
    for lab, leg in legs:
        b = B.get(leg.occ)
        if b is None:
            continue
        a = price_window(b, t_in); z = price_window(b, t_out)
        if not (np.isfinite(a) and np.isfinite(z) and a > 0):
            continue
        w = b[(b.t >= t_in) & (b.t <= t_out)]
        peak = (w.h.max() / a - 1) * 100 if len(w) else np.nan
        rec = dict(contract=lab, occ=leg.occ, cost=a * 100, peak=peak, hit100=bool(peak >= 100) if np.isfinite(peak) else False)
        for nm, cst in (("ret", COST), ("stress", STRESS)):
            r1 = ((z - cst) / (a + cst) - 1) * 100
            if t_add is not None:
                a2 = price_window(b, t_add)
                r2 = ((z - cst) / (a2 + cst) - 1) * 100 if np.isfinite(a2) and a2 > 0 else 0.0
                rec[nm] = 0.5 * r1 + 0.5 * r2
            else:
                rec[nm] = r1
        rows.append(rec)
    return rows


DATA = {}


def data(sym):
    if sym not in DATA:
        DATA[sym] = xs.prepare(sym, start="2023-01-01T00:00:00Z", h1start="2022-10-01T00:00:00Z")
    return DATA[sym]


def tcl(x, dates):
    x = pd.Series(np.asarray(x, float)); d = pd.Series(pd.DatetimeIndex(dates).normalize())
    ok = x.notna(); x, d = x[ok], d[ok]
    g = x.groupby(d.values).mean()
    if len(g) < 5 or g.std() == 0:
        return float("nan")
    return g.mean() / (g.std(ddof=1) / math.sqrt(len(g)))


def main():
    es.HD = es.keys(); orl.HD = orl.keys()
    os.makedirs(OUT, exist_ok=True)
    try:
        S = pd.read_csv(SRC)
        S = S[S.survives.astype(str).str.lower() == "true"].head(MAX_SURV)
    except FileNotFoundError:
        S = pd.DataFrame()
    if not len(S):
        open(f"{OUT}/report.md", "w").write("# Exit search, stage 2\n\nNo stage-1 survivors, so nothing to price.\n")
        print("No stage-1 survivors, nothing to price."); return
    vix = es.vix_series()
    rng = np.random.default_rng(13)
    rows = []
    for k, s in enumerate(S.itertuples(), 1):
        cb = xs.COMBOS[int(s.combo)]; sgn = 1 if s.dir == "CALLS" else -1; cp = "C" if sgn > 0 else "P"
        syms = es.ETFS if s.group == "ETF" else es.STOCKS
        ev = []
        for sym in syms:
            dat = data(sym)
            if dat is None or s.sig not in dat[2]:
                continue
            days, G, Sg, info, DL, HP = dat
            vp = vix.reindex(days).shift(1).values if len(vix) else np.full(len(days), np.nan)
            dd, ss = np.nonzero(Sg[s.sig])
            m = (days[dd] >= START) & (ss < xs.SL - 1) & np.array([DL[d] is not None for d in dd])
            if s.regime == "VIX20+":
                m &= vp[dd] >= 20
            ev += [(sym, d, t) for d, t in zip(dd[m], ss[m])]
        if len(ev) > MAX_EV:
            ev = [ev[i] for i in np.sort(rng.choice(len(ev), MAX_EV, replace=False))]
        tag = f"{s.sig} | {s.dir} | {s.group} | {s.regime} | {xs.exit_text(s)}"
        for sym in sorted({e[0] for e in ev}):
            days, G, Sg, info, DL, HP = data(sym)
            D = len(days)
            vp = vix.reindex(days).shift(1).values if len(vix) else np.full(D, np.nan)
            locs = [(d, t) for sy, d, t in ev if sy == sym]
            LV = xs.location_levels(locs, days, G, DL, HP)
            gi = np.array([d * xs.SL + t for d, t in locs])
            Cf = G["c"].ravel()
            x, hit, add, ok = one(gi, LV, sgn, cb, G, D)
            pool = {hv: np.where((days >= START) & ((vp >= 20) == hv) & np.array([q is not None for q in DL]))[0] for hv in (False, True)}
            for i, (d, t) in enumerate(locs):
                if not ok[i]:
                    continue
                g0 = gi[i]; t_in = ts_of(days, g0); t_out = ts_of(days, g0 + 1 + x[i])
                t_add = ts_of(days, g0 + 1 + add[i]) if cb["entry"] == "split" and add[i] <= x[i] else None
                for r in option_trade(sym, cp, t_in, t_out, t_add, Cf[g0]):
                    rows.append(dict(r, survivor=tag, symbol=sym, entry=t_in, exit=t_out, target_hit=bool(hit[i]), random=False))
                # paired random trade
                pl = pool[bool(vp[d] >= 20)]
                pl = pl[pl != d]
                if not len(pl):
                    continue
                rd = rng.choice(pl); rg = rd * xs.SL + t
                ratio = Cf[rg] / Cf[g0]
                rLV = {kk: v[i:i + 1] * ratio for kk, v in LV.items()}
                rx, rhit, radd, rok = one(np.array([rg]), rLV, sgn, cb, G, D)
                if not rok[0]:
                    continue
                r_in = ts_of(days, rg); r_out = ts_of(days, rg + 1 + rx[0])
                r_add = ts_of(days, rg + 1 + radd[0]) if cb["entry"] == "split" and radd[0] <= rx[0] else None
                for r in option_trade(sym, cp, r_in, r_out, r_add, Cf[rg]):
                    rows.append(dict(r, survivor=tag, symbol=sym, entry=r_in, exit=r_out, target_hit=bool(rhit[0]), random=True))
        print(f"  [{k}/{len(S)}] {tag}: {len(ev)} signals, rows {len(rows)}", flush=True)
    T = pd.DataFrame(rows)
    T.to_csv(f"{OUT}/trades.csv", index=False)
    report(T)


def report(T):
    L = ["# Exit search, stage 2: survivors on real option prices, with their stock-level exits", "",
         "Real Alpaca option trades since Feb 2024. Expiry 7+ days out and after the exit, no 0DTE. Spread $0.03 per side "
         "(stress $0.06). Peak = highest the option traded between entry and exit. Random = paired random trade with the "
         "same exit distances. t clustered by entry day.", "",
         "| Survivor | Contract | Trades | Signal days | Avg cost | Under $500 | Avg return | Median | Win rate | Hit +100% | Avg peak | Stress avg | Random avg | Edge | t (avg) | t (edge) | Verdict |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    if not len(T):
        L.append("| no trades could be priced | | | | | | | | | | | | | | | | |")
    for (tag, con), x in (T.groupby(["survivor", "contract"]) if len(T) else []):
        sg, rd = x[~x.random], x[x.random]
        if len(sg) < 5:
            continue
        rm = rd.ret.mean() if len(rd) else np.nan
        edge = sg.ret - (rm if np.isfinite(rm) else 0)
        days = sg.entry.dt.normalize().nunique() if hasattr(sg.entry, "dt") else pd.to_datetime(sg.entry).dt.normalize().nunique()
        ta, te = tcl(sg.ret, pd.to_datetime(sg.entry)), tcl(edge, pd.to_datetime(sg.entry))
        ok = days >= 30 and sg.ret.mean() > 0 and edge.mean() > 0 and ta >= 2.5 and te >= 2.5
        L.append(f"| {tag} | {con} | {len(sg)} | {days} | ${sg.cost.mean():,.0f} | {(sg.cost <= 500).mean():.0%} | {sg.ret.mean():+.1f}% | "
                 f"{sg.ret.median():+.1f}% | {(sg.ret > 0).mean():.0%} | {sg.hit100.mean():.0%} | {sg.peak.mean():+.0f}% | {sg.stress.mean():+.1f}% | "
                 f"{rm:+.1f}% | {edge.mean():+.1f} | {ta:.1f} | {te:.1f} | {'**MAKES MONEY**' if ok else ('too few' if days < 30 else 'no')} |")
    L += ["", "Limits: Feb 2024 onward; trade prints, not bid/ask; up to 250 signals per survivor; one option trade swings a "
          "lot, so a small true edge needs many trades to show. Not financial advice."]
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


if __name__ == "__main__":
    main()
