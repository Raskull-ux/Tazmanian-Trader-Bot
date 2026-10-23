// Daily setup grade, built from Taz's 666 graded bear calls (2023-2026), judged in both halves of the history.
//   A/A- (5-6 pts): right first 62-67% | B (4): 55% | C (3) and D (0-2): 44%
// Pieces (puts): closed under the 8 EMA (2) · popped into the 8 EMA/10 SMA from below and closed back under (1)
// · riding the 10 SMA, 3 of the last 5 closes within 0.5 ATR (1) · 10 EMA under the 10 SMA (1) · weaker than QQQ over 5 days (1)
// Flags (not points): squeeze between a rising 200 and a falling 10 (his calls 57%), a recent 10/20/8 x 200 bear cross (his calls 21-25%: late).
// Calls are graded as the mirror image (not separately measured). Graded on the last COMPLETED daily bar.
import { ema, atrWilder, getBars } from "./meter.js";

const RECORD = {
  NVDA: "your record: 40 trades, +21% avg, 6 doubles ✅", META: "your record: 37 trades, +11% avg, 6 doubles ✅",
  QQQ: "your record: 169 trades, -6% avg (0DTE is the leak)", SPY: "your record: 48 trades, -9% avg",
  AAPL: "⚠️ your record: 21 trades, 14% wins, -42% avg", TSLA: "⚠️ your record: 30 trades, 23% wins, -35% avg",
  AVGO: "⚠️ your record: 10 trades, 10% wins, -48% avg", SLV: "⚠️ your record: 15 trades, 13% wins, -42% avg",
  NFLX: "⚠️ your record: 8 trades, 0 wins, -55% avg", AMD: "your record: 34 trades, -15% avg (calls 51% right: execution leak)",
};

function smaAt(arr, n, i) { if (i + 1 < n) return NaN; let s = 0; for (let k = i - n + 1; k <= i; k++) s += arr[k]; return s / n; }
function atrSeries(b) { const out = []; let a; for (let i = 0; i < b.length; i++) { const tr = i === 0 ? b[i].h - b[i].l : Math.max(b[i].h - b[i].l, Math.abs(b[i].h - b[i - 1].c), Math.abs(b[i].l - b[i - 1].c)); a = a === undefined ? tr : a + (tr - a) / 14; out.push(a); } return out; }

export function computeGrade(daily, qqqDaily, side = "P") {
  if (!daily || daily.length < 210) return null;
  const c = daily.map((b) => b.c), h = daily.map((b) => b.h);
  const e8 = ema(c, 8), e10 = ema(c, 10), A = atrSeries(daily);
  const i = c.length - 1, put = side !== "C", sg = put ? 1 : -1;
  const s10 = (k) => smaAt(c, 10, k), s20 = (k) => smaAt(c, 20, k), s200 = (k) => smaAt(c, 200, k);
  const below = (x, y) => (put ? x < y : x > y);
  const pieces = [];
  const under8 = below(c[i], e8[i]); pieces.push([put ? "Closed under the 8 EMA" : "Closed over the 8 EMA", under8 ? 2 : 0]);
  const hiLvl = Math.min(e8[i], s10(i)), loLvl = Math.max(e8[i], s10(i));
  const pop = put ? (h[i] >= hiLvl && c[i] < loLvl && c[i - 1] < Math.max(e8[i - 1], s10(i - 1)))
                  : (daily[i].l <= loLvl && c[i] > hiLvl && c[i - 1] > Math.min(e8[i - 1], s10(i - 1)));
  pieces.push([put ? "Popped into the 8 EMA/10 SMA, closed back under" : "Dipped into the 8 EMA/10 SMA, closed back over", pop ? 1 : 0]);
  let hug = 0; for (let k = i - 4; k <= i; k++) if (Math.abs(c[k] - s10(k)) <= 0.5 * A[k]) hug++;
  pieces.push(["Riding the 10 SMA (3 of 5 days)", hug >= 3 ? 1 : 0]);
  pieces.push([put ? "10 EMA under the 10 SMA" : "10 EMA over the 10 SMA", below(e10[i], s10(i)) ? 1 : 0]);
  let rel = null;
  if (qqqDaily && qqqDaily.length > 6) {
    const qc = qqqDaily.map((b) => b.c), qi = qc.length - 1;
    const r5 = c[i] / c[i - 5] - 1, q5 = qc[qi] / qc[qi - 5] - 1; rel = (r5 - q5) * 100;
    pieces.push([put ? "Weaker than QQQ over 5 days" : "Stronger than QQQ over 5 days", (put ? r5 < q5 : r5 > q5) ? 1 : 0]);
  }
  const score = pieces.reduce((s, p) => s + p[1], 0);
  const letter = score >= 6 ? "A" : score === 5 ? "A-" : score === 4 ? "B" : score === 3 ? "C" : "D";
  const odds = score >= 5 ? "your A/A- calls: right first 62-67%" : score === 4 ? "your B calls: 55%" : "your C/D calls: 44% (coin flip)";
  const flags = [];
  if (put && s10(i) > s200(i) && c[i] < s10(i) && c[i] >= s200(i) * 0.99) flags.push("🎯 Between the 200 and the falling 10 SMA, 10 still above the 200 (your calls here: 57%)");
  for (const [nm, f] of [["10 SMA", (k) => s10(k)], ["20 SMA", (k) => s20(k)], ["8 EMA", (k) => e8[k]]]) {
    for (let k = i; k > i - 10; k--) {
      const cross = put ? (f(k) < s200(k) && f(k - 1) >= s200(k - 1)) : (f(k) > s200(k) && f(k - 1) <= s200(k - 1));
      if (cross) { flags.push(`⚠️ ${nm} crossed the 200 ${i - k} day${i - k === 1 ? "" : "s"} ago: late, bounce risk (your calls after these: 21-25%)`); break; }
    }
  }
  return { score, letter, pieces, flags, date: daily[i].t, close: c[i], e8: e8[i], s10: s10(i), s200: s200(i), rel };
}

export function gradeText(ticker, g, side) {
  if (!g) return `📊 Grade: not enough daily data for ${ticker}`;
  const put = side !== "C";
  const d = String(g.date).slice(0, 10);
  const lines = [
    `📊 **${ticker} daily ${put ? "puts" : "calls"} grade: ${g.letter} (${g.score}/6)**: ${g.score >= 5 ? "your A/A- calls: right first 62-67%" : g.score === 4 ? "your B calls: 55%" : "your C/D calls: 44%, a coin flip"}`,
    ...g.pieces.map(([k, v]) => `   ${v > 0 ? "✅" : "❌"} ${k}`),
    ...g.flags.map((f) => `   ${f}`),
    `   Close ${g.close.toFixed(2)} · 8 EMA ${g.e8.toFixed(2)} · 10 SMA ${g.s10.toFixed(2)} · 200 SMA ${g.s200.toFixed(2)} · as of the ${d} close`,
  ];
  if (!put) lines.push("   _Calls are graded as the mirror of the put data (not separately measured)._");
  if (RECORD[ticker]) lines.push(`   ${RECORD[ticker]}`);
  return lines.join("\n");
}

export async function fetchGrade(env, ticker, side, now = Date.now()) {
  if (!env.ALPACA_KEY_ID || !env.ALPACA_SECRET) return null;
  const etDate = (t) => new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date(t));
  const today = etDate(now);
  const p = { timeframe: "1Day", start: new Date(now - 460 * 86400000).toISOString(), end: new Date(now - 16 * 60000).toISOString(), feed: "sip", adjustment: "split" };
  const [d, q] = await Promise.all([getBars(env, ticker, p), getBars(env, "QQQ", p)]);
  const done = (arr) => arr.filter((b) => etDate(b.t) < today || isAfterClose(now));
  const g = computeGrade(done(d), done(q), side);
  return { g, text: gradeText(ticker, g, side) };
}

function isAfterClose(now) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(now)).map((x) => [x.type, x.value]));
  return +p.hour * 60 + +p.minute >= 16 * 60 + 15;
}
