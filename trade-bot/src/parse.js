// Text parsing and Eastern-time helpers for the Tazmanian trade bot.
// Everything here is pure (no Cloudflare APIs) so it can be tested with plain Node.

const CMD_WORDS = {
  in: "in", buy: "in", bto: "in", long: "in", entry: "in",
  half: "trim", trim: "trim", partial: "trim",
  out: "out", sell: "out", close: "out", exit: "out", stc: "out", stopped: "out",
  plan: "plan", setup: "plan",
  recap: "recap", today: "recap", status: "recap",
  paper: "paper",
  log: "log", export: "log",
  live: "live", test: "test",
  note: "note",
  undo: "undo",
  help: "help", commands: "help",
  open: "open", positions: "open",
};

const NOT_TICKERS = new Set([
  ...Object.keys(CMD_WORDS), "c", "p", "call", "calls", "put", "puts", "x", "at",
  "stop", "free", "on", "off", "dte", "today", "tmr",
]);

const RIGHT = { c: "C", call: "C", calls: "C", p: "P", put: "P", puts: "P" };

// ---------- Eastern time ----------
export function etParts(ms) {
  const f = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23", weekday: "short",
  });
  const p = Object.fromEntries(f.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  return {
    date: `${p.year}-${p.month}-${p.day}`,
    year: +p.year, month: +p.month, day: +p.day,
    hour: +p.hour, minute: +p.minute, weekday: p.weekday,
  };
}

export function fmtTime(ms) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York", hour: "numeric", minute: "2-digit",
  }).format(new Date(ms)) + " ET";
}

function isoAdd(iso, days) {
  const d = new Date(iso + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function dow(iso) {
  return new Date(iso + "T12:00:00Z").getUTCDay(); // 0 Sun .. 6 Sat
}

export function nextTradingDay(iso) {
  let d = isoAdd(iso, 1);
  while (dow(d) === 0 || dow(d) === 6) d = isoAdd(d, 1);
  return d;
}

export function daysBetween(aIso, bIso) {
  return Math.round((new Date(bIso + "T12:00:00Z") - new Date(aIso + "T12:00:00Z")) / 86400000);
}

// A plan posted after 4 PM ET, or on a weekend, is for the next trading day.
export function planTradeDate(ms) {
  const e = etParts(ms);
  const wd = dow(e.date);
  if (wd === 0 || wd === 6 || e.hour >= 16) return nextTradingDay(e.date);
  return e.date;
}

// ---------- token helpers ----------
function parseExp(tok, todayIso) {
  if (tok === "0dte" || tok === "today") return todayIso;
  if (tok === "tmr" || tok === "tomorrow") return nextTradingDay(todayIso);
  const m = tok.match(/^(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?$/);
  if (!m) return null;
  const mo = +m[1], da = +m[2];
  if (mo < 1 || mo > 12 || da < 1 || da > 31) return null;
  let yr = m[3] ? +m[3] : +todayIso.slice(0, 4);
  if (yr < 100) yr += 2000;
  let iso = `${yr}-${String(mo).padStart(2, "0")}-${String(da).padStart(2, "0")}`;
  if (!m[3] && daysBetween(todayIso, iso) < -7) {
    iso = `${yr + 1}-${String(mo).padStart(2, "0")}-${String(da).padStart(2, "0")}`;
  }
  return iso;
}

function parseQty(tok) {
  let m = tok.match(/^x(\d+)$/) || tok.match(/^(\d+)x$/);
  return m ? +m[1] : null;
}

function parsePrice(tok) {
  const m = tok.match(/^@?\$?(\d*\.\d+|\d+(?:\.\d+)?)$/);
  return m ? +m[1] : null;
}

function isTicker(tok) {
  return /^[a-z]{1,5}$/.test(tok) && !NOT_TICKERS.has(tok);
}

// Returns {strike, right, consumed} or null. Handles 717p, 717.5c, 717 p, 720/722c.
function parseContract(toks, i) {
  const t = toks[i];
  if (t === undefined) return null;
  let m = t.match(/^(\d+(?:\.\d+)?(?:\/\d+(?:\.\d+)?)?)(c|p|call|calls|put|puts)$/);
  if (m) return { strike: m[1], right: RIGHT[m[2]], consumed: 1 };
  m = t.match(/^(\d+(?:\.\d+)?(?:\/\d+(?:\.\d+)?)?)$/);
  if (m && toks[i + 1] && RIGHT[toks[i + 1]]) {
    return { strike: m[1], right: RIGHT[toks[i + 1]], consumed: 2 };
  }
  return null;
}

// ---------- main parser ----------
// Returns an object with .cmd, or {cmd:"error", msg}.
export function parseCommand(raw, nowMs) {
  const today = etParts(nowMs).date;
  let text = String(raw || "").trim();
  let note = "";
  const bar = text.indexOf("|");
  if (bar >= 0) {
    note = text.slice(bar + 1).trim();
    text = text.slice(0, bar).trim();
  }
  let toks = text.toLowerCase().replace(/,/g, " ").split(/\s+/).filter(Boolean);
  if (!toks.length) return { cmd: "help" };

  let route = "main";
  if (toks[0] === "free") {
    route = "free";
    toks = toks.slice(1);
    if (!toks.length) return { cmd: "error", msg: "Free what? Example: `/t free in qqq 717p 10/23 .45`" };
  }

  let cmd = CMD_WORDS[toks[0]];
  let rest = toks.slice(1);
  // "qqq 717p 10/23 .45" with no command word means an entry.
  if (!cmd && isTicker(toks[0]) && parseContract(toks, 1)) {
    cmd = "in";
    rest = toks;
  }
  if (!cmd) return { cmd: "error", msg: `I don't know "${toks[0]}". Type \`/t help\`.` };

  if (cmd === "in") return { ...parseEntry(rest, today, note), route };
  if (cmd === "trim" || cmd === "out") return { ...parseExit(cmd, rest, note), route };
  if (cmd === "plan") {
    let original = String(raw).trim().replace(/^(free\s+)?\S+\s*/i, ""); // keep his casing/wording
    const tick = rest.find(isTicker);
    if (!tick) return { cmd: "error", msg: "Plan needs a ticker. Example: `/t plan qqq 727 stop 733`" };
    original = original.replace(new RegExp(`^\\$?${tick}\\b\\s*`, "i"), "") || original;
    const sm = original.match(/stop\s*@?\$?(\d+(?:\.\d+)?)/i);
    return { cmd: "plan", ticker: tick.toUpperCase(), text: original, stop: sm ? +sm[1] : null, route };
  }
  if (cmd === "paper") {
    const v = rest[0] === "on" ? true : rest[0] === "off" ? false : null;
    return { cmd: "paper", value: v };
  }
  if (cmd === "note") {
    const t = String(raw).trim().replace(/^\S+\s*/, "");
    if (!t) return { cmd: "error", msg: "Note what? Example: `/t note 1h 10 SMA close target`" };
    return { cmd: "note", text: t };
  }
  return { cmd, route };
}

function parseEntry(toks, today, note) {
  let ticker = null, strike = null, right = null, exp = null, price = null, qty = null;
  for (let i = 0; i < toks.length; i++) {
    const t = toks[i];
    if (!ticker && isTicker(t)) { ticker = t.toUpperCase(); continue; }
    if (ticker && !strike) {
      const c = parseContract(toks, i);
      if (c) { strike = c.strike; right = c.right; i += c.consumed - 1; continue; }
    }
    const q = parseQty(t);
    if (q !== null) { qty = q; continue; }
    if (!exp) {
      const e = parseExp(t, today);
      if (e) { exp = e; continue; }
    }
    if (t === "at") continue;
    const pr = parsePrice(t);
    if (pr !== null && strike) { price = pr; continue; }
  }
  const missing = [];
  if (!ticker) missing.push("ticker");
  if (!strike) missing.push("strike + c/p (like 717p)");
  if (!exp) missing.push("expiration (like 10/23)");
  if (price === null) missing.push("price (like .45)");
  if (missing.length) {
    return { cmd: "error", msg: `Missing ${missing.join(", ")}. Example: \`/t in qqq 717p 10/23 .45 x2\`` };
  }
  if (price <= 0) return { cmd: "error", msg: "Price has to be above 0." };
  return { cmd: "in", ticker, strike, right, exp, price, qty: qty || 1, note };
}

function parseExit(cmd, toks, note) {
  let ticker = null, price = null, qty = null;
  for (const t of toks) {
    if (!ticker && isTicker(t)) { ticker = t.toUpperCase(); continue; }
    const q = parseQty(t);
    if (q !== null) { qty = q; continue; }
    if (t === "at") continue;
    const pr = parsePrice(t);
    if (pr !== null && price === null) { price = pr; continue; }
  }
  if (price === null) {
    const ex = cmd === "trim" ? "/t half .90" : "/t out .70";
    return { cmd: "error", msg: `Missing the price. Example: \`${ex}\`` };
  }
  return { cmd, ticker, price, qty, note };
}

// ---------- formatting ----------
export function money(n) {
  const s = Math.abs(n).toFixed(2);
  return (n < 0 ? "-$" : "$") + s;
}

export function pct(exitPx, entryPx) {
  return (exitPx / entryPx - 1) * 100;
}

export function fmtPct(p) {
  return (p >= 0 ? "+" : "") + p.toFixed(0) + "%";
}

export function contractLabel(p) {
  const [y, m, d] = p.exp.split("-");
  return `${p.ticker} ${p.strike}${p.right} ${+m}/${+d}`;
}

export function fmtPx(n) {
  return Number(n).toFixed(2);
}
