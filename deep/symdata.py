"""
One symbol, every timeframe, every indicator, ready to be asked:
  features_at(t)  what the chart looked like at moment t (only bars finished by t)
  path(t, n)      the 5-min bars after t for the next n sessions
"""
import numpy as np, pandas as pd
from . import lib

TFS = {"m5": 5, "m15": 15, "m30": 30, "h1": 60, "h4": 240}


class SymData:
    def __init__(self, sym, spy=None, vix=None):
        self.sym = sym
        self.daily = lib.load_daily(sym)
        m5 = lib.load_m5(sym)
        self.ok = self.daily is not None and m5 is not None and len(m5) > 1000
        if not self.ok:
            return
        self.m5 = m5                                       # stamped at bar start
        self.D = lib.add_ind(self.daily)
        self.D["green"] = self.D.c > self.D.o
        self.D["body"] = (self.D.c - self.D.o) / self.D.atr
        self.W = lib.add_ind(lib.weekly(self.daily), smas=(10, 20, 50))
        self.tf = {}
        for k, mins in TFS.items():
            bars = lib.m5_end_index(m5) if k == "m5" else lib.resample_intraday(m5, mins)
            self.tf[k] = lib.add_ind(bars, smas=(9, 20, 50, 200))
        self.sessions = self.D.index
        self.spy = spy
        self.vix = vix
        self._tidx = {k: v.index.values for k, v in self.tf.items()}

    # ---------- helpers ----------
    def session_of(self, t):
        """The session whose decisions happen at t: same day if before 16:00 on a trading day, else next."""
        d = t.normalize()
        i = self.sessions.searchsorted(d)
        if i < len(self.sessions) and self.sessions[i] == d and t.hour * 60 + t.minute < 960:
            return self.sessions[i]
        j = self.sessions.searchsorted(d, side="right")
        return self.sessions[j] if j < len(self.sessions) else None

    def entry_point(self, t):
        """Where a call posted at t can actually be traded: inside regular hours -> close of the 5-min bar it
        was posted in; outside -> the next session's 9:30 open."""
        s = self.session_of(t)
        if s is None:
            return None, None
        tod = t.hour * 60 + t.minute
        if t.normalize() == s and 570 <= tod < 960:
            te = s + pd.Timedelta(minutes=570 + ((tod - 570) // 5 + 1) * 5)
            m = self.tf["m5"]
            i = m.index.searchsorted(te, side="right") - 1
            if i < 0:
                return None, None
            return m.index[i], float(m.c.iloc[i])
        first = self.m5[self.m5.index >= s + pd.Timedelta(minutes=570)]
        if len(first) == 0 or first.index[0].normalize() != s:
            return None, None
        return s + pd.Timedelta(minutes=570), float(first.o.iloc[0])

    def last_bar(self, k, t):
        idx = self._tidx[k]
        i = idx.searchsorted(np.datetime64(t), side="right") - 1
        return (self.tf[k].iloc[i], self.tf[k].iloc[i - 1], i) if i >= 1 else (None, None, None)

    # ---------- features ----------
    def features_at(self, t, price=None):
        f = {}
        s = self.session_of(t) if t.hour * 60 + t.minute < 960 else None
        day = t.normalize() if s is None else s
        D = self.D[self.D.index < day]
        if len(D) < 210:
            return None
        d0, d1 = D.iloc[-1], D.iloc[-2]
        price = price if price is not None else d0.c
        a = d0.atr
        f["d_rsi"] = d0.rsi
        f["d_rsi_above_ma"] = d0.rsi > d0.rsi_ma
        f["d_rsi_max5"] = D.rsi.iloc[-5:].max()
        f["d_rsi_cross_down_3d"] = bool(((D.rsi < D.rsi_ma) & (D.rsi.shift() >= D.rsi_ma.shift())).iloc[-3:].any())
        f["d_macd_above_sig"] = d0.macd > d0.macd_sig
        f["d_macd_cross_down_3d"] = bool(((D.macd < D.macd_sig) & (D.macd.shift() >= D.macd_sig.shift())).iloc[-3:].any())
        f["d_hist_falling"] = d0["hist"] < d1["hist"]
        f["d_macd_above_0"] = d0.macd > 0
        for n in (10, 20, 50, 200):
            f[f"d_vs_sma{n}_atr"] = (price - d0[f"sma{n}"]) / a
        f["d_10_below_50"] = d0.sma10 < d0.sma50
        cr = (D.sma10 < D.sma50) & (D.sma10.shift() >= D.sma50.shift())
        last_cross = cr[cr].index
        f["d_days_since_10_50_bear_cross"] = (len(D) - 1 - D.index.get_loc(last_cross[-1])) if len(last_cross) else 999
        f["d_20_below_50"] = d0.sma20 < d0.sma50
        f["d_50_below_200"] = d0.sma50 < d0.sma200
        f["d_ret_10d_atr"] = (d0.c - D.c.iloc[-11]) / a
        f["d_ret_5d_atr"] = (d0.c - D.c.iloc[-6]) / a
        f["d_from_20d_high_atr"] = (D.h.iloc[-20:].max() - price) / a
        f["d_from_60d_high_atr"] = (D.h.iloc[-60:].max() - price) / a
        f["d_days_since_20d_high"] = 19 - int(np.argmax(D.h.iloc[-20:].values))
        f["d_greens_last10"] = int(D.green.iloc[-10:].sum())
        f["d_seq4"] = "".join("G" if g else "R" for g in D.green.iloc[-4:])
        f["d_last_body_atr"] = d0.body
        f["d_up_streak"] = int((~D.green.iloc[::-1]).cumsum().eq(0).sum())
        f["d_atr_pct"] = a / d0.c * 100
        f["d_vol_vs_20"] = d0.v / D.v.iloc[-21:-1].mean()
        # weekly
        W = self.W[self.W.index < day]
        if len(W) > 60:
            w0 = W.iloc[-1]
            f["w_rsi"] = w0.rsi
            f["w_rsi_above_ma"] = w0.rsi > w0.rsi_ma
            f["w_macd_above_sig"] = w0.macd > w0.macd_sig
            f["w_10_below_20"] = w0.sma10 < w0.sma20
        # intraday timeframes (bars finished by t)
        for k in ("m5", "m15", "h1", "h4"):
            b, pb, i = self.last_bar(k, t)
            if b is None:
                continue
            f[f"{k}_rsi"] = b.rsi
            f[f"{k}_rsi_above_ma"] = b.rsi > b.rsi_ma
            f[f"{k}_macd_above_sig"] = b.macd > b.macd_sig
            f[f"{k}_hist_falling"] = b["hist"] < pb["hist"]
            f[f"{k}_vs_sma20_atr"] = (price - b.sma20) / a
            f[f"{k}_vs_sma50_atr"] = (price - b.sma50) / a
            f[f"{k}_vs_sma200_atr"] = (price - b.sma200) / a
            f[f"{k}_20_below_50"] = b.sma20 < b.sma50
            X = self.tf[k].iloc[max(0, i - 40): i + 1]
            f[f"{k}_rsi_max_recent"] = X.rsi.iloc[-12:].max()
        # today so far (if intraday)
        if t.normalize() == day and t.hour * 60 + t.minute >= 575:
            td = self.m5[(self.m5.index >= day) & (self.m5.index < t)]
            if len(td):
                f["today_gap_atr"] = (td.o.iloc[0] - d0.c) / a
                f["today_move_atr"] = (price - d0.c) / a
                f["today_from_high_atr"] = (td.h.max() - price) / a
        else:
            f["today_gap_atr"] = np.nan
        f["minute_of_day"] = t.hour * 60 + t.minute
        if self.spy is not None:
            S = self.spy[self.spy.index < day]
            if len(S) > 50:
                f["spy_above_20"] = S.c.iloc[-1] > S.sma20.iloc[-1]
                f["spy_above_50"] = S.c.iloc[-1] > S.sma50.iloc[-1]
                f["spy_rsi"] = S.rsi.iloc[-1]
        if self.vix is not None:
            v = self.vix[self.vix.index < day]
            if len(v):
                f["vix"] = float(v.iloc[-1])
        f["atr"] = a
        return f

    # ---------- what happened next ----------
    def path(self, t0, sessions=10):
        """5-min bars (stamped at END) strictly after t0, through `sessions` sessions incl. t0's session."""
        m = self.tf["m5"]
        s = self.session_of(t0 - pd.Timedelta(minutes=1)) or t0.normalize()
        i = self.sessions.searchsorted(s)
        last = self.sessions[min(i + sessions - 1, len(self.sessions) - 1)]
        return m[(m.index > t0) & (m.index <= last + pd.Timedelta(hours=16))]

    def outcome_short(self, t0, p0, atr):
        """Bear outcomes from entry (t0, p0)."""
        P = self.path(t0, 10)
        if len(P) < 20:
            return None
        o = {}
        days = P.index.normalize()
        ud = days.unique()
        for k in (1, 3, 5, 10):
            X = P[days <= ud[min(k - 1, len(ud) - 1)]]
            o[f"drop_{k}d_pct"] = (p0 - X.l.min()) / p0 * 100
            o[f"rise_{k}d_pct"] = (X.h.max() - p0) / p0 * 100
            o[f"ret_{k}d_pct"] = (p0 - X.c.iloc[-1]) / p0 * 100       # positive = went your way
        o["ret_close_pct"] = (p0 - P[days == ud[0]].c.iloc[-1]) / p0 * 100
        # target-first: 1 ATR down before 1 ATR up, 5 sessions
        X = P[days <= ud[min(4, len(ud) - 1)]]
        dn = np.where(X.l.values <= p0 - atr)[0]
        up = np.where(X.h.values >= p0 + atr)[0]
        fd = dn[0] if len(dn) else 10 ** 9
        fu = up[0] if len(up) else 10 ** 9
        o["win_1atr"] = 1.0 if fd < fu else (0.0 if fu < fd else 0.5)
        # early: how far it went against before the 10-day low
        il = int(np.argmin(P.l.values))
        o["low10_pct"] = (p0 - P.l.values[il]) / p0 * 100
        o["low10_session"] = int(np.searchsorted(ud, days[il])) + 1
        o["rise_before_low_pct"] = (P.h.values[: il + 1].max() - p0) / p0 * 100
        ih = int(np.argmax(P.h.values[: max(1, min(len(P), 78 * 3))]))
        o["top3d_pct"] = (P.h.values[ih] - p0) / p0 * 100
        o["top3d_session"] = int(np.searchsorted(ud, days[ih])) + 1
        return o
