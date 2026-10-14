"""Real 1-minute OPRA option bars already downloaded for Taz's 576 exact-time trades (results_minute/bar_cache).
One clean series per contract: volume-weighted close across exchanges, minute by minute (ET, naive)."""
import glob
import numpy as np, pandas as pd

_CACHE = None


def option_minutes():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    parts = []
    for f in glob.glob("results_minute/bar_cache/*.pkl.gz"):
        try:
            d = pd.read_pickle(f)
        except Exception:
            continue
        if len(d) == 0:
            continue
        d = d.reset_index()
        parts.append(d[["ts_event", "high", "low", "close", "volume", "symbol"]])
    a = pd.concat(parts, ignore_index=True)
    a["occ"] = a.symbol.str.replace(" ", "", regex=False)
    a["t"] = pd.to_datetime(a.ts_event, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    a["cv"] = a.close * a.volume
    g = a.groupby(["occ", "t"])
    out = pd.DataFrame({"c": g.cv.sum() / g.volume.sum(), "h": g.high.max(), "l": g.low.min(), "v": g.volume.sum()})
    out = out.reset_index()
    _CACHE = {k: v.set_index("t").sort_index() for k, v in out.groupby("occ")}
    return _CACHE


def price_at(occ, t, how="next"):
    """Option price at time t: first minute bar at or after t (how='next'), within 30 minutes."""
    s = option_minutes().get(occ)
    if s is None:
        return np.nan
    i = s.index.searchsorted(t)
    if i >= len(s) or (s.index[i] - t) > pd.Timedelta(minutes=30):
        return np.nan
    return float(s.c.iloc[i])


def window(occ, t0, t1):
    s = option_minutes().get(occ)
    if s is None:
        return None
    return s[(s.index >= t0) & (s.index <= t1)]
