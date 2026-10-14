"""
EXIT SEARCH, STAGE 1: every intraday signal, calls AND puts, with REAL exits (stock levels), not clock holds.

Taz: "Targets are support and resistance on the hourly and the daily, gaps in between and below.
      Stops are short, on the 15 / 30 minute or hourly. Sometimes I hold overnight. Test everything."

Same 35 names and 5-minute data as the edge search (2016 -> now), same intraday signals (first time per day).
Every signal is traded BOTH ways (calls = long the move, puts = short the move).

LEVELS (only what was known at entry):
  hourly S/R      swing highs/lows on 1-hour bars (confirmed 2 bars later), last 10 sessions
  daily S/R       swing highs/lows on daily bars (confirmed 2 days later), last 60 sessions, prior day high/low,
                  prior week high/low
  gap             unfilled daily gap edges from the last 60 sessions; yesterday's close when today gapped
  volume profile  POC / value-area high / value-area low of the prior 5 sessions
  SMA             20 / 50 / 200 day
  any level       all of the above together
EXITS, every combination (468 per signal and direction):
  TARGET  the 1st or 2nd level of each type in your direction (at least 0.15% away). Filled AT the level.
  STOP    none, or a 15m / 30m / 1h CLOSE through: the nearest level against you, the signal bar's low/high,
          or the day's low/high so far. Filled at that close.
  HOLD    out by the close the same day, next day, or 3 days (whatever comes first: target, stop, time).
  ENTRY   all-in at the signal, or SPLIT: half at the signal, half when price touches the nearest level against
          you, stop on a close through the 2nd level against you (same total money; if the add never fills,
          that half sits in cash).
  Same bar hits target and stop: counted as the stop (conservative).
EDGE = the trade's result (% of the stock price, your direction) MINUS a paired random trade: a random day, same
  5-minute slot, same period, same VIX state (over/under 20), with the signal trade's EXACT target and stop distances
  applied. So the exit geometry is identical and only the signal can make a difference.
  Regimes: all days, VIX 20+. t clustered by month.

HONEST SCORING (set before running):
  DISCOVERY 2016-2022: candidates need 300+ trades, 24+ months, edge >= 0.15% per trade, t >= 3.
    The top 25 by t go on (no more than 3 exit versions of the same signal/direction/names/regime).
  HOLDOUT 2023-2026 (untouched): SURVIVOR = edge > 0 with t >= 2.5, 100+ trades, edge >= 0.075%.
  Checked on random-walk test data first.
Out: results/exit_search/report.md, candidates.csv (stage 2 reads it)
"""
from __future__ import annotations
import os, math, itertools
import numpy as np, pandas as pd
import edge_search as es

OUT = "results/exit_search"
SL = es.SLOTS
MAXB = 4 * SL
HOLD_SPLIT = es.HOLD_SPLIT
TYPES = ["any level", "hourly S/R", "daily S/R", "gap", "volume profile", "SMA"]
TFS = {"15m": np.array([(s + 1) % 3 == 0 for s in range(SL)]),
       "30m": np.array([(s + 1) % 6 == 0 or s == SL - 1 for s in range(SL)]),
       "1h": np.isin(np.arange(SL), [11, 23, 35, 47, 59, 71, 77])}
STOPS = ["level", "signal bar", "day extreme"]
TIMES = {"same day": 0, "next day": 1, "3 days": 3}
MIN_DIST = 0.0015
TOP_N, DISC_T, HOLD_T, DISC_N, DISC_M, HOLD_N, FLOOR = 25, 3.0, 2.5, 300, 24, 100, 0.15


def combos():
    C = []
    for ti, (ty, nth) in enumerate(itertools.product(TYPES, (1, 2))):
        for tn, tk in TIMES.items():
            C.append(dict(entry="all-in", target=f"{'next' if nth == 1 else '2nd'} {ty}", ti=ti, stop="none", tf=None, time=tn, tk=tk))
            for st, tf in itertools.product(STOPS, TFS):
                C.append(dict(entry="all-in", target=f"{'next' if nth == 1 else '2nd'} {ty}", ti=ti, stop=st, tf=tf, time=tn, tk=tk))
            for tf in TFS:
                C.append(dict(entry="split", target=f"{'next' if nth == 1 else '2nd'} {ty}", ti=ti, stop="2nd level", tf=tf, time=tn, tk=tk))
    return C


COMBOS = combos()
NC = len(COMBOS)


# ------------------------------------------------------------------ levels
def daily_levels(days, G):
    """Per day d: dict type -> array of levels known at the open of day d (from closes up to d-1)."""
    O, H, L, C, V = G["o"], G["h"], G["l"], G["c"], G["v"]
    D = len(days)
    o, h, l, c = O[:, 0], H.max(1), L.min(1), C[:, -1]
    cs = pd.Series(c)
    sma = {n: cs.rolling(n).mean().values for n in (20, 50, 200)}
    piv = []                                  # (available_from_day, k, value)
    for k in range(2, D - 2):
        if h[k] > max(h[k - 2], h[k - 1], h[k + 1], h[k + 2]):
            piv.append((k + 3, k, h[k]))
        if l[k] < min(l[k - 2], l[k - 1], l[k + 1], l[k + 2]):
            piv.append((k + 3, k, l[k]))
    piv = np.array(piv) if piv else np.zeros((0, 3))
    out = [None] * D
    flatc = C.ravel(); flatv = V.ravel()
    for d in range(6, D):
        lv = {}
        m = (piv[:, 0] <= d) & (piv[:, 1] >= d - 60) if len(piv) else np.array([], bool)
        lv["daily S/R"] = np.r_[piv[m, 2] if len(piv) else [], h[d - 1], l[d - 1], h[d - 5:d].max(), l[d - 5:d].min()]
        gp = []
        for k in range(max(d - 60, 1), d):
            mn = l[k + 1:d].min() if k + 1 < d else np.inf
            mx = h[k + 1:d].max() if k + 1 < d else -np.inf
            if l[k] > h[k - 1] and mn > h[k - 1]:
                gp += [h[k - 1], min(l[k], mn)]
            if h[k] < l[k - 1] and mx < l[k - 1]:
                gp += [l[k - 1], max(h[k], mx)]
        if abs(o[d] / c[d - 1] - 1) >= 0.003:
            gp.append(c[d - 1])
        lv["gap"] = np.array(gp, float)
        a, b = (d - 5) * SL, d * SL
        pc, pv = flatc[a:b], flatv[a:b]
        w = max(c[d - 1] * 0.001, 1e-6)
        if np.nansum(pv) > 0:
            bins = np.floor(pc / w); ub, inv = np.unique(bins, return_inverse=True)
            vol = np.bincount(inv, weights=np.nan_to_num(pv))
            poc = int(vol.argmax()); lo_i = hi_i = poc; tot = vol.sum(); acc = vol[poc]
            while acc < 0.7 * tot and (lo_i > 0 or hi_i < len(vol) - 1):
                nxt_lo = vol[lo_i - 1] if lo_i > 0 else -1; nxt_hi = vol[hi_i + 1] if hi_i < len(vol) - 1 else -1
                if nxt_hi >= nxt_lo:
                    hi_i += 1; acc += vol[hi_i]
                else:
                    lo_i -= 1; acc += vol[lo_i]
            lv["volume profile"] = (np.array([ub[poc], ub[lo_i], ub[hi_i]]) + 0.5) * w
        else:
            lv["volume profile"] = np.array([])
        lv["SMA"] = np.array([sma[20][d - 1], sma[50][d - 1], sma[200][d - 1]])
        out[d] = {k: v[np.isfinite(v)] for k, v in lv.items()}
    return out


def hourly_pivots(G):
    H, L = G["h"], G["l"]
    D = len(H)
    grp = [(0, 12), (12, 24), (24, 36), (36, 48), (48, 60), (60, 72), (72, 78)]
    ends = np.array([11, 23, 35, 47, 59, 71, 77])
    HH = np.stack([H[:, a:b].max(1) for a, b in grp], 1).ravel()
    LL = np.stack([L[:, a:b].min(1) for a, b in grp], 1).ravel()
    n = len(HH); rec = []
    for i in range(2, n - 2):
        if HH[i] > max(HH[i - 2], HH[i - 1], HH[i + 1], HH[i + 2]):
            rec.append((i + 2, HH[i]))
        if LL[i] < min(LL[i - 2], LL[i - 1], LL[i + 1], LL[i + 2]):
            rec.append((i + 2, LL[i]))
    rec.sort()
    ci = np.array([r[0] for r in rec], int); val = np.array([r[1] for r in rec])
    conf_gi = (ci // 7) * SL + ends[ci % 7]                 # global slot when confirmed
    piv_day = (ci - 2) // 7
    return conf_gi, piv_day, val


def location_levels(locs, days, G, DL, HP):
    """For each (d, s): targets up/down (12 each), stops up/down (3 each), split levels up/down (2 each)."""
    H, L, C = G["h"], G["l"], G["c"]
    conf_gi, piv_day, pval = HP
    n = len(locs)
    T_up = np.full((n, 12), np.nan); T_dn = np.full((n, 12), np.nan)
    S_up = np.full((n, 3), np.nan); S_dn = np.full((n, 3), np.nan)
    A_up = np.full((n, 2), np.nan); A_dn = np.full((n, 2), np.nan)
    for i, (d, s) in enumerate(locs):
        lv = DL[d]
        if lv is None:
            continue
        p = C[d, s]; gi = d * SL + s
        j = np.searchsorted(conf_gi, gi, "right")
        hv = pval[:j][piv_day[:j] >= d - 10]
        lvl = {"hourly S/R": hv, **lv}
        lvl["any level"] = np.concatenate([lvl[k] for k in TYPES[1:]])
        for ti, (ty, nth) in enumerate(itertools.product(TYPES, (1, 2))):
            a = lvl[ty]
            up = np.sort(a[a > p * (1 + MIN_DIST)]); dn = np.sort(a[a < p * (1 - MIN_DIST)])[::-1]
            if len(up) >= nth:
                T_up[i, ti] = up[nth - 1]
            if len(dn) >= nth:
                T_dn[i, ti] = dn[nth - 1]
        a = lvl["any level"]
        below = np.sort(a[a < p * (1 - 0.001)])[::-1]; above = np.sort(a[a > p * (1 + 0.001)])
        S_up[i] = [below[0] if len(below) else np.nan, L[d, s], L[d, :s + 1].min()]
        S_dn[i] = [above[0] if len(above) else np.nan, H[d, s], H[d, :s + 1].max()]
        A_up[i] = [below[0] if len(below) else np.nan, below[1] if len(below) > 1 else np.nan]
        A_dn[i] = [above[0] if len(above) else np.nan, above[1] if len(above) > 1 else np.nan]
    return dict(T_up=T_up, T_dn=T_dn, S_up=S_up, S_dn=S_dn, A_up=A_up, A_dn=A_dn)


# ------------------------------------------------------------------ simulation
BIG = 10 ** 6


def first_idx(M):
    has = M.any(1)
    return np.where(has, M.argmax(1), BIG)


def simulate(gi, LV, sgn, G, D):
    """Returns (n, NC) % results in the trade's direction, target-hit flags (n, NC), held bars (n, NC)."""
    Hf, Lf, Cf = G["h"].ravel(), G["l"].ravel(), G["c"].ravel()
    n = len(gi)
    last = len(Cf) - 1
    idx = np.minimum(gi[:, None] + np.arange(1, MAXB + 1)[None, :], last)
    Hp, Lp, Cp = Hf[idx], Lf[idx], Cf[idx]
    slot = idx % SL
    p = Cf[gi]
    d = gi // SL
    up = sgn > 0
    T = LV["T_up"] if up else LV["T_dn"]; S = LV["S_up"] if up else LV["S_dn"]; A = LV["A_up"] if up else LV["A_dn"]
    tg = np.stack([first_idx((Hp >= T[:, k:k + 1]) if up else (Lp <= T[:, k:k + 1])) for k in range(12)], 1)
    st = {}
    for si in range(3):
        for tf, bm in TFS.items():
            br = (Cp < S[:, si:si + 1]) if up else (Cp > S[:, si:si + 1])
            st[(STOPS[si], tf)] = first_idx(br & bm[slot])
    for tf, bm in TFS.items():
        br = (Cp < A[:, 1:2]) if up else (Cp > A[:, 1:2])
        st[("2nd level", tf)] = first_idx(br & bm[slot])
    add = first_idx((Lp <= A[:, 0:1]) if up else (Hp >= A[:, 0:1]))
    ends = {}
    for tn, k in TIMES.items():
        e = (d + k) * SL + (SL - 1) - gi - 1                  # position in path (0 = first bar after entry)
        ok = (d + k < D) & (e >= 0)
        ends[tn] = np.where(ok, np.minimum(e, MAXB - 1), -1)
    R = np.full((n, NC), np.nan, np.float32); HIT = np.zeros((n, NC), bool); HELD = np.zeros((n, NC), np.float32)
    rows = np.arange(n)
    for j, cb in enumerate(COMBOS):
        e = ends[cb["time"]]
        t_i = tg[:, cb["ti"]]
        s_i = st[(cb["stop"], cb["tf"])] if cb["stop"] != "none" else np.full(n, BIG)
        valid = (e >= 0) & np.isfinite(T[:, cb["ti"]])
        if cb["stop"] in STOPS:
            valid &= np.isfinite(S[:, STOPS.index(cb["stop"])])
        stop_first = (s_i <= t_i) & (s_i <= e)
        targ = (t_i < s_i) & (t_i <= e)
        x = np.where(stop_first, s_i, np.where(targ, t_i, e)); x = np.clip(x, 0, MAXB - 1)
        px = np.where(targ & ~stop_first, T[:, cb["ti"]], Cp[rows, x])
        r1 = (px / p - 1) * 100 * sgn
        if cb["entry"] == "split":
            a1 = A[:, 0]
            filled = (add <= x) & np.isfinite(a1)
            r2 = np.where(filled, (px / a1 - 1) * 100 * sgn, 0.0)
            r = 0.5 * r1 + 0.5 * r2
            valid &= np.isfinite(A[:, 1])
        else:
            r = r1
        R[:, j] = np.where(valid, r, np.nan)
        HIT[:, j] = targ & ~stop_first & valid
        HELD[:, j] = np.where(valid, x + 1, np.nan)
    return R, HIT, HELD


# ------------------------------------------------------------------ per symbol
class Acc:
    def __init__(self, months):
        self.months = months; self.mi = {m: i for i, m in enumerate(months)}; self.d = {}

    def add(self, key, mon_idx, E, RAW, HIT):
        if key not in self.d:
            z = lambda: np.zeros((NC, len(self.months)), np.float32)
            self.d[key] = dict(e=z(), raw=z(), n=z(), hit=z())
        a = self.d[key]
        ii, jj = np.nonzero(np.isfinite(E))
        mm = mon_idx[ii]
        np.add.at(a["e"], (jj, mm), E[ii, jj]); np.add.at(a["raw"], (jj, mm), RAW[ii, jj])
        np.add.at(a["n"], (jj, mm), 1); np.add.at(a["hit"], (jj, mm), HIT[ii, jj])


def prepare(sym, start="2016-01-01T00:00:00Z", h1start="2015-10-01T00:00:00Z"):
    m5 = es.fetch(sym, "5Min", start)
    if len(m5) < 5000:
        return None
    days, G = es.build_grid(m5)
    h1 = es.fetch(sym, "1Hour", h1start)
    S, info = es.signals(days, G, h1)
    S = {k: v for k, v in S.items() if k.startswith("I ") or k.startswith("3h")}
    DL = daily_levels(days, G)
    HP = hourly_pivots(G)
    return days, G, S, info, DL, HP


def run_symbol(sym, grp, vix, acc, rng):
    prep = prepare(sym)
    if prep is None:
        print(f"  {sym}: not enough data"); return
    days, G, S, info, DL, HP = prep
    D = len(days)
    period = np.where(days < HOLD_SPLIT, 0, 1)
    vp = vix.reindex(days).shift(1).values if len(vix) else np.full(D, np.nan)
    hi_vix = vp >= 20
    mon = np.array([acc.mi.get(m, -1) for m in days.to_period("M").astype(str)])
    valid = (np.arange(D) >= 60) & np.array([x is not None for x in DL])
    pools = {(pr, hv): np.where(valid & (period == pr) & (hi_vix == hv))[0] for pr in (0, 1) for hv in (False, True)}
    sig_locs = sorted({(d, s) for E in S.values() for d, s in zip(*np.nonzero(E)) if valid[d] and s < SL - 1})
    li = {x: i for i, x in enumerate(sig_locs)}
    LV = location_levels(sig_locs, days, G, DL, HP)
    Cf = G["c"].ravel()
    for sig, E in S.items():
        dd, ss = np.nonzero(E)
        keep = valid[dd] & (ss < SL - 1) & (mon[dd] >= 0)
        dd, ss = dd[keep], ss[keep]
        if not len(dd):
            continue
        idx = np.array([li[(d, s)] for d, s in zip(dd, ss)])
        sub = {k: v[idx] for k, v in LV.items()}
        gi = dd * SL + ss
        # paired random entry: same period, same VIX state, same 5-minute slot, a different day;
        # the signal trade's exact target/stop distances (as ratios of the entry price) applied to it
        rd = np.array([rng.choice(pools[(period[d], bool(hi_vix[d]))]) if len(pools[(period[d], bool(hi_vix[d]))]) else d for d in dd])
        rgi = rd * SL + ss
        ratio = Cf[rgi] / Cf[gi]
        rsub = {k: v * ratio[:, None] for k, v in sub.items()}
        for sgn, dn in ((1, "CALLS"), (-1, "PUTS")):
            R, HIT, _ = simulate(gi, sub, sgn, G, D)
            Rr, _, _ = simulate(rgi, rsub, sgn, G, D)
            Ed = R - Rr
            for reg, rm in (("all", np.ones(len(dd), bool)), ("VIX20+", hi_vix[dd])):
                if rm.any():
                    acc.add((sig, dn, grp, reg), mon[dd[rm]], Ed[rm], R[rm], HIT[rm].astype(np.float32))
    print(f"  {sym}: {D} days, {len(S)} signals, {len(sig_locs)} entry points", flush=True)


# ------------------------------------------------------------------ scoring / report
def score(acc):
    months = pd.PeriodIndex(acc.months, freq="M")
    disc = np.array(months < pd.Period(HOLD_SPLIT, "M")); hold = ~disc
    rows = []
    for key, a in acc.d.items():
        for part, pm in (("disc", disc), ("hold", hold)):
            n = a["n"][:, pm]; e = a["e"][:, pm]; raw = a["raw"][:, pm]; hit = a["hit"][:, pm]
            N = n.sum(1)
            with np.errstate(invalid="ignore", divide="ignore"):
                mm = np.where(n > 0, e / np.maximum(n, 1), np.nan)
                M = (n > 0).sum(1)
                mu = np.nanmean(mm, 1); sd = np.nanstd(mm, 1, ddof=1)
                t = mu / (sd / np.sqrt(M))
                edge = e.sum(1) / N; avg = raw.sum(1) / N; hr = hit.sum(1) / N
            for j in range(NC):
                rows.append((*key, j, part, N[j], M[j], edge[j], t[j], avg[j], hr[j]))
    T = pd.DataFrame(rows, columns=["sig", "dir", "group", "regime", "combo", "part", "n", "months", "edge", "t", "avg", "hit"])
    W = T.pivot_table(index=["sig", "dir", "group", "regime", "combo"], columns="part",
                      values=["n", "months", "edge", "t", "avg", "hit"])
    W.columns = [f"{a}_{b}" for a, b in W.columns]
    W = W.reset_index()
    for k in ("entry", "target", "stop", "tf", "time"):
        W[k] = W.combo.map(lambda j: COMBOS[j][k])
    return W


def pick(W):
    c = W[(W.n_disc >= DISC_N) & (W.months_disc >= DISC_M) & (W.edge_disc >= FLOOR) & (W.t_disc >= DISC_T)]
    c = c.sort_values("t_disc", ascending=False)
    c = c.groupby(["sig", "dir", "group", "regime"]).head(3).head(TOP_N).copy()
    c["survives"] = ((c.edge_hold > 0) & (c.t_hold >= HOLD_T) & (c.n_hold >= HOLD_N) & (c.edge_hold >= FLOOR / 2)).fillna(False)
    return c


def exit_text(r):
    stop = "no stop" if r.stop == "none" else f"{r.tf} close through {'2nd level against' if r.stop == '2nd level' else r.stop}"
    return f"{r.entry}; target {r.target}; {stop}; max {r.time}"


def report(W, c, n_tests):
    L = ["# Exit search, stage 1: signals traded with real exits (stock levels), calls and puts", "",
         f"{n_tests} combinations scored (signal x direction x names x regime x {NC} exit rules). Edge = the trade's result "
         "(% of the stock price, your direction) minus a paired random trade (same 5-minute slot, period and VIX state, "
         "same target and stop distances). Discovery 2016-2022 picks the top 25, the untouched 2023-2026 holdout decides.", "",
         "## 1. SURVIVORS", "",
         "| Signal | Trade | Names | Regime | Exit rule | Discovery: edge / avg / target hit (t, n) | Holdout: edge / avg / target hit (t, n) | Verdict |",
         "|---|---|---|---|---|---|---|---|"]

    def row(r):
        return (f"| {r.sig} | {r.dir} | {r.group} | {r.regime} | {exit_text(r)} | "
                f"{r.edge_disc:+.2f}% / {r.avg_disc:+.2f}% / {r.hit_disc:.0%} (t {r.t_disc:.1f}, n {r.n_disc:.0f}) | "
                f"{r.edge_hold:+.2f}% / {r.avg_hold:+.2f}% / {r.hit_hold:.0%} (t {r.t_hold:.1f}, n {r.n_hold:.0f}) | "
                f"{'**SURVIVES**' if r.survives else 'fail'} |")
    sv = c[c.survives]
    L += [row(r) for r in sv.itertuples()] if len(sv) else ["| none | | | | | | | |"]
    L += ["", f"## 2. All {len(c)} discovery candidates", "",
          "| Signal | Trade | Names | Regime | Exit rule | Discovery | Holdout | Verdict |", "|---|---|---|---|---|---|---|---|"]
    L += [row(r) for r in c.itertuples()]
    L += ["", "## 3. Best exit rule per signal and direction in DISCOVERY (info only, many tries)", "",
          "| Signal | Trade | Names | Best exit rule | Discovery edge (t) | Holdout edge (t) |", "|---|---|---|---|---|---|"]
    b = W[(W.regime == "all") & (W.n_disc >= DISC_N)].sort_values("t_disc", ascending=False).groupby(["sig", "dir", "group"]).head(1)
    for r in b.sort_values("t_disc", ascending=False).head(40).itertuples():
        L.append(f"| {r.sig} | {r.dir} | {r.group} | {exit_text(r)} | {r.edge_disc:+.2f}% (t {r.t_disc:.1f}) | {r.edge_hold:+.2f}% (t {r.t_hold:.1f}) |")
    L += ["", "Avg = the trade's raw result (% of stock price, your direction). Target hit = share of trades that reached "
          "the target before the stop or time. Limits: today's names; 5-minute bars (target and stop in the same bar = "
          "stop); stock moves, not option prices (stage 2 prices survivors). Not financial advice."]
    os.makedirs(OUT, exist_ok=True)
    open(f"{OUT}/report.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))


def main():
    es.HD = es.keys()
    os.makedirs(OUT, exist_ok=True)
    vix = es.vix_series()
    months = [str(p) for p in pd.period_range("2016-01", pd.Timestamp.now().to_period("M"), freq="M")]
    acc = Acc(months)
    rng = np.random.default_rng(5)
    for grp, syms in (("ETF", es.ETFS), ("STOCK", es.STOCKS)):
        for s in syms:
            try:
                run_symbol(s, grp, vix, acc, rng)
            except Exception as ex:
                import traceback; traceback.print_exc()
                print(f"  {s}: {type(ex).__name__} {ex}")
    W = score(acc)
    c = pick(W)
    c.to_csv(f"{OUT}/candidates.csv", index=False)
    report(W, c, len(W))


if __name__ == "__main__":
    main()
