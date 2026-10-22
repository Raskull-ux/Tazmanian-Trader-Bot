// EARLY meter: is this entry ahead of the move?
// Built from Taz's 183 early put entries vs the actual high of day (2024-2026):
//   at his early entries: 5m RSI ~60, 15m RSI ~60, ~0.5 ATR of range used from the low
//   at the real high:     5m RSI ~74, 15m RSI ~75, ~1.0 ATR used, a daily level usually tagged
// It is a "not yet" check, not a signal. It never blocks an entry.
// Settings match Taz's charts: RSI 14 exponential, ATR 14 Wilder, 8 EMA, SMAs 10/20/50/200,
// intraday bars with extended hours. Data: Alpaca free plan (IEX intraday, SIP daily history).

const ALPACA = "https://data.alpaca.markets/v2/stocks";

// ---------- pure math (unit tested) ----------
export function ema(vals, span) {
  const a = 2 / (span + 1); const out = []; let e;
  for (const v of vals) { e = e === undefined ? v : e + a * (v - e); out.push(e); }
  return out;
}

export function sma(vals, n) {
  if (vals.length < n) return NaN;
  let s = 0; for (let i = vals.length - n; i < vals.length; i++) s += vals[i];
  return s / n;
}

// RSI 14, exponential averaging (pandas ewm(span=14, adjust=False, min_periods=14))
export function rsiExp(closes, n = 14) {
  if (closes.length < n + 1) return NaN;
  const a = 2 / (n + 1); let g, l;
  for (let i = 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    const up = Math.max(d, 0), dn = Math.max(-d, 0);
    g = g === undefined ? up : g + a * (up - g);
    l = l === undefined ? dn : l + a * (dn - l);
  }
  if (l === 0) return 100;
  return 100 - 100 / (1 + g / l);
}

// ATR 14, Wilder smoothing (ewm alpha=1/14, adjust=False), seeded with the first true range
export function atrWilder(bars, n = 14) {
  let a;
  for (let i = 0; i < bars.length; i++) {
    const b = bars[i];
    const tr = i === 0 ? b.h - b.l : Math.max(b.h - b.l, Math.abs(b.h - bars[i - 1].c), Math.abs(b.l - bars[i - 1].c));
    a = a === undefined ? tr : a + (tr - a) / n;
  }
  return a;
}

// Group 5-minute bars into 15-minute bars anchored at :00/:15/:30/:45
export function to15(bars5) {
  const out = []; let cur = null;
  for (const b of bars5) {
    const t = new Date(b.t); const slot = Math.floor(t.getTime() / 900000);
    if (!cur || cur.slot !== slot) { cur = { slot, o: b.o, h: b.h, l: b.l, c: b.c }; out.push(cur); }
    else { cur.h = Math.max(cur.h, b.h); cur.l = Math.min(cur.l, b.l); cur.c = b.c; }
  }
  return out;
}

// daily: completed daily bars (oldest first), today5: today's 5m bars since 4 AM ET,
// hist5: several days of 5m bars ending now (for RSI warm-up). side: "P" or "C".
export function computeMeter({ daily, hist5, today5, side }) {
  if (!daily || daily.length < 30 || !hist5 || hist5.length < 20 || !today5 || !today5.length) return null;
  const closes = daily.map((b) => b.c);
  const A = atrWilder(daily);
  const prev = daily[daily.length - 1];
  const e8 = ema(closes, 8).at(-1);
  const levels = {
    "8 EMA": e8, "10 SMA": sma(closes, 10), "20 SMA": sma(closes, 20), "50 SMA": sma(closes, 50),
    "200 SMA": sma(closes, 200), "prior day high": prev.h, "5-day high": Math.max(...daily.slice(-5).map((b) => b.h)),
    "prior day low": prev.l, "5-day low": Math.min(...daily.slice(-5).map((b) => b.l)),
  };
  const px = hist5.at(-1).c;
  const r5 = rsiExp(hist5.map((b) => b.c));
  const r15 = rsiExp(to15(hist5).map((b) => b.c));
  const dayLo = Math.min(...today5.map((b) => b.l)), dayHi = Math.max(...today5.map((b) => b.h));
  const put = side !== "C";
  const used = put ? (px - dayLo) / A : (dayHi - px) / A;
  const vsClose = (px - prev.c) / A;
  // nearest level in the direction of the move (overhead for puts, below for calls)
  const cands = Object.entries(levels).filter(([, v]) => Number.isFinite(v))
    .map(([k, v]) => ({ k, v, d: put ? (v - px) / A : (px - v) / A }));
  const ahead = cands.filter((x) => x.d > 0).sort((a, b) => a.d - b.d)[0] || null;
  const atLevel = cands.filter((x) => Math.abs(x.d) <= 0.15).sort((a, b) => Math.abs(a.d) - Math.abs(b.d))[0] || null;

  const stretchR5 = put ? r5 : 100 - r5, stretchR15 = put ? r15 : 100 - r15;
  const signs = [];
  if (Number.isFinite(stretchR5) && stretchR5 < 70) signs.push(put ? `5m RSI ${r5.toFixed(0)} (your real highs averaged 74)` : `5m RSI ${r5.toFixed(0)} (calls: mirror of the put data, lows ~26)`);
  if (used < 0.8) signs.push(`only ${used.toFixed(2)} ATR used (your real ${put ? "highs" : "lows"} came at ~1.0)`);
  if (!atLevel && ahead && ahead.d <= 1.0) signs.push(`${ahead.k} ${ahead.v.toFixed(2)} still ${put ? "overhead" : "below"} (+${ahead.d.toFixed(2)} ATR)`);
  const verdict = signs.length >= 2 ? "🛑 **EARLY**" : signs.length === 1 ? "⚠️ **Maybe early**" : "✅ **Stretched**";
  return {
    verdict, signs, px, r5, r15, used, vsClose, A,
    ahead, atLevel,
    text: [
      `⏱️ EARLY meter: ${verdict}`,
      `   5m RSI ${fmt(r5, 0)} · 15m RSI ${fmt(r15, 0)} · ${used.toFixed(2)} ATR used · ${vsClose >= 0 ? "+" : ""}${vsClose.toFixed(2)} ATR vs yesterday's close`,
      atLevel ? `   At the ${atLevel.k} (${atLevel.v.toFixed(2)})` : ahead ? `   Next level ${put ? "up" : "down"}: ${ahead.k} ${ahead.v.toFixed(2)} (${ahead.d.toFixed(2)} ATR away)` : `   No daily level within reach`,
      ...signs.map((s) => `   • ${s}`),
    ].join("\n"),
  };
}

function fmt(x, d) { return Number.isFinite(x) ? x.toFixed(d) : "n/a"; }

// ---------- data (Alpaca free plan) ----------
async function getBars(env, sym, params) {
  const out = []; let token = null;
  for (let page = 0; page < 5; page++) {
    const q = new URLSearchParams({ ...params, limit: "10000", ...(token ? { page_token: token } : {}) });
    const r = await fetch(`${env.ALPACA_DATA || ALPACA}/${encodeURIComponent(sym)}/bars?${q}`, {
      headers: { "APCA-API-KEY-ID": env.ALPACA_KEY_ID, "APCA-API-SECRET-KEY": env.ALPACA_SECRET },
      signal: AbortSignal.timeout(4000),
    });
    if (!r.ok) throw new Error(`Alpaca ${r.status}`);
    const j = await r.json();
    for (const b of j.bars || []) out.push({ t: b.t, o: b.o, h: b.h, l: b.l, c: b.c });
    token = j.next_page_token; if (!token) break;
  }
  return out;
}

function etMidnightUTC(now) {
  // 00:00 ET today, as an ISO string (handles daylight saving through Intl)
  const f = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23" });
  const p = Object.fromEntries(f.formatToParts(new Date(now)).map((x) => [x.type, x.value]));
  const guess = Date.UTC(+p.year, +p.month - 1, +p.day, 4); // 00:00 EDT = 04:00 UTC
  const h = +new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", hourCycle: "h23" }).format(new Date(guess));
  return new Date(guess - h * 3600000).toISOString();
}

export async function fetchMeter(env, ticker, side, now = Date.now()) {
  if (!env.ALPACA_KEY_ID || !env.ALPACA_SECRET) return null;
  const startDaily = new Date(now - 460 * 86400000).toISOString();
  const start5 = new Date(now - 5 * 86400000).toISOString();
  const [daily, hist5] = await Promise.all([
    getBars(env, ticker, { timeframe: "1Day", start: startDaily, end: new Date(now - 16 * 60000).toISOString(), feed: "sip", adjustment: "split" }),
    getBars(env, ticker, { timeframe: "5Min", start: start5, feed: "iex" }),
  ]);
  if (!hist5.length) return null;
  // Use the latest session in the data: today if it has traded, otherwise the last session
  // (so a check at night reads the day that just finished).
  const etDate = (t) => new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date(t));
  const session = etDate(hist5.at(-1).t);
  const today5 = hist5.filter((b) => etDate(b.t) === session);
  const dailyPrior = daily.filter((b) => etDate(b.t) < session);
  const m = computeMeter({ daily: dailyPrior, hist5, today5, side });
  if (m) {
    m.session = session;
    if (session !== etDate(now)) m.text += `\n   _(market closed: read is from the ${session} session)_`;
  }
  return m;
}
