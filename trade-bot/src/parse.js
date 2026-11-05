// Text parsing and Eastern-time helpers for the Tazmanian trade bot.
// Everything here is pure (no Cloudflare APIs) so it can be tested with plain Node.
//
// The parser reads a trade line in ANY word order. Every token is classified on its own
// (ticker, strike + put/call, spread, expiry, price, quantity, command word), then the pieces
// are put together. Nothing is rejected outright: missing pieces come back in `missing`,
// best guesses in `guesses`, and the bot asks for a one-tap fix.

// ---------- word lists ----------
const ENTRY_WORDS = new Set(["in", "inn", "iin", "ni", "buy", "bought", "bto", "long", "entry", "entered", "enter", "add", "added", "opened"]);
const EXIT_WORDS = new Set(["out", "otu", "oit", "ot", "uot", "outt", "oout", "ou", "sell", "sold", "sel", "sld", "close", "closed",
  "exit", "exited", "stc", "stopped", "flat"]);
const TRIM_WORDS = new Set(["half", "hlaf", "haf", "halff", "trim", "trimmed", "trimed", "trimm", "partial", "scale", "scaled"]);
const OTHER_CMDS = {
  plan: "plan", setup: "plan",
  recap: "recap", today: "recap", status: "recap",
  paper: "paper",
  log: "log", export: "log",
  live: "live", test: "test",
  note: "note",
  undo: "undo",
  help: "help", commands: "help",
  open: "open", positions: "open",
  check: "check", early: "check", meter: "check",
  grade: "grade", score: "grade",
  fix: "fix", fx: "fix", edit: "fix", change: "fix",
  delete: "delete", del: "delete", remove: "delete", rm: "delete",
  cleanup: "cleanup", clean: "cleanup",
};
const YES = new Set(["y", "yes", "yep", "yeah", "yup", "ya", "yea", "ye", "yes!", "ok", "okay", "k", "correct", "confirm", "sure", "👍", "✅"]);
const NO = new Set(["n", "no", "nope", "nah", "cancel", "nevermind", "nvm", "skip", "👎", "❌"]);

const RIGHT = {
  p: "P", put: "P", puts: "P", pt: "P", pts: "P", putt: "P", putz: "P", pust: "P", ptu: "P", ptus: "P", putts: "P",
  c: "C", call: "C", calls: "C", cal: "C", cals: "C", calsl: "C", clal: "C", clals: "C", callz: "C", calss: "C", caal: "C", calll: "C",
};
const RIGHT_RE = "(p|c|puts?|pt|pts|putt|putz|pust|putts|calls?|cals?|calsl|clals?|callz|calss|calll)";
const SPREAD_WORDS = new Set(["spread", "spreads", "spr", "sprd", "vertical", "vert", "debit", "credit", "bear", "bull"]);
const QTY_WORDS = new Set(["contracts", "contract", "cons", "con", "cts", "ct", "lots", "lot", "x"]);
const MONTHS = { jan: 1, january: 1, feb: 2, february: 2, mar: 3, march: 3, apr: 4, april: 4, may: 5, jun: 6, june: 6,
  jul: 7, july: 7, aug: 8, august: 8, sep: 9, sept: 9, september: 9, oct: 10, october: 10, nov: 11, november: 11,
  dec: 12, december: 12 };
const WEEKDAYS = { mon: 1, monday: 1, tue: 2, tues: 2, tuesday: 2, wed: 3, weds: 3, wednesday: 3, thu: 4, thur: 4, thurs: 4,
  thursday: 4, fri: 5, friday: 5, fry: 5, frid: 5 };
const FILLER = new Set(["at", "for", "the", "of", "on", "my", "i", "im", "i'm", "a", "an", "to", "and", "all", "rest", "runner",
  "runners", "more", "some", "price", "px", "exp", "expiry", "expiration", "strike", "net", "fill", "filled", "limit", "lmt", "mkt",
  "dte", "today", "tmr", "tomorrow", "tmrw", "eod", "stop", "sl", "free", "this", "next", "qty", "it", "is", "was", "got", "position",
  "pos", "trade", "contracts", "contract", "cons", "con", "cts", "ct", "lots", "lot", "x", "@", "from", "with", "just", "back",
  "leg", "legs", "short", "puts", "calls", "spread", "nope", "yes", "no", "ok", "via", "please", "pls"]);

const NOT_TICKERS = new Set([...ENTRY_WORDS, ...EXIT_WORDS, ...TRIM_WORDS, ...Object.keys(OTHER_CMDS), ...Object.keys(RIGHT),
  ...SPREAD_WORDS, ...Object.keys(MONTHS), ...Object.keys(WEEKDAYS), ...FILLER, ...YES, ...NO, "0dte", "odte"]);

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

// The coming given weekday (today counts), e.g. "fri" on a Friday = today.
function comingWeekday(todayIso, wd) {
  let d = todayIso;
  while (dow(d) !== wd) d = isoAdd(d, 1);
  return d;
}

// Best-guess expiry when he leaves it out: the nearest Friday at least a week away (his rule: a week or more out).
export function guessExpiry(todayIso) {
  let d = comingWeekday(todayIso, 5);
  while (daysBetween(todayIso, d) < 7) d = isoAdd(d, 7);
  return d;
}

function mkIso(yr, mo, da, todayIso, explicitYear) {
  if (mo < 1 || mo > 12 || da < 1 || da > 31) return null;
  let iso = `${yr}-${String(mo).padStart(2, "0")}-${String(da).padStart(2, "0")}`;
  if (!explicitYear && daysBetween(todayIso, iso) < -7) iso = `${yr + 1}-${String(mo).padStart(2, "0")}-${String(da).padStart(2, "0")}`;
  return iso;
}

// ---------- tokenizer ----------
function tokenize(text) {
  let t = String(text || "").toLowerCase()
    .replace(/[,;!?]+/g, " ")
    .replace(/[‘’]/g, "'")
    .replace(/¢/g, "c ")
    .replace(/#(\d)/g, "$1")
    .replace(/@\s*/g, " @ ")
    .replace(/\bqty[:=]?(\d)/g, "qty $1")
    .replace(/\b([a-z]{3,9})(\d{1,2})\b/g, (m, a, b) => (MONTHS[a] ? `${a} ${b}` : m)) // oct30 -> oct 30
    .replace(/(\d)\s*%/g, "$1%")
    .replace(/(\d)x(\d)/g, "$1 x$2");                                       // .45x2 -> .45 x2
  return t.split(/\s+/).map((x) => x.replace(/^[.:]+(?=[a-z$])/, "").replace(/(?<=[a-z0-9%])[.:]+$/, "")).filter(Boolean);
}

const NUM = String.raw`\$?(\d+(?:\.\d+)?|\.\d+)`;

function num(s) { return +String(s).replace(/^\$/, ""); }

// ---------- the classifier ----------
// Returns the raw pieces found in the tokens, in order of appearance.
function classify(toks, todayIso) {
  const out = {
    words: { entry: [], exit: [], trim: [] }, tickers: [], contracts: [], spreads: [], rights: [], exps: [],
    prices: [], qty: null, pct: null, nums: [], spreadWord: false, credit: false, stop: null, unknown: [],
  };
  const used = new Array(toks.length).fill(false);
  const take = (i, n = 1) => { for (let k = i; k < i + n; k++) used[k] = true; };
  const isRightTok = (s) => s !== undefined && RIGHT[s] !== undefined;

  for (let i = 0; i < toks.length; i++) {
    if (used[i]) continue;
    const t = toks[i], nx = toks[i + 1], nx2 = toks[i + 2];
    let m;

    // command words
    if (ENTRY_WORDS.has(t)) { out.words.entry.push(i); take(i); continue; }
    if (TRIM_WORDS.has(t)) { out.words.trim.push(i); take(i); continue; }
    if (EXIT_WORDS.has(t)) { out.words.exit.push(i); take(i); continue; }
    if (SPREAD_WORDS.has(t)) {
      out.spreadWord = true; take(i);
      if (t === "credit") out.credit = true;
      if ((t === "bull" && (nx === "put" || nx === "puts")) || (t === "bear" && (nx === "call" || nx === "calls"))) out.credit = true;
      continue;
    }
    // stop level: "stop 347" / "sl 347" (kept as a note, never read as a price or strike)
    if ((t === "stop" || t === "sl") && nx && (m = nx.match(new RegExp(`^${NUM}$`)))) { out.stop = num(m[1]); take(i, 2); continue; }
    // quantity
    if ((m = t.match(/^x(\d{1,3})$/)) || (m = t.match(/^(\d{1,3})x$/))) { out.qty = +m[1]; take(i); continue; }
    if (t === "x" && nx && /^\d{1,3}$/.test(nx)) { out.qty = +nx; take(i, 2); continue; }
    if ((t === "qty" || t === "size") && nx && /^\d{1,3}$/.test(nx)) { out.qty = +nx; take(i, 2); continue; }
    if (/^\d{1,3}$/.test(t) && nx && QTY_WORDS.has(nx) && nx !== "x") { out.qty = +t; take(i, 2); continue; }
    if ((m = t.match(/^(\d{1,3})(contracts?|cons?|cts?)$/))) { out.qty = +m[1]; take(i); continue; }
    // percent (trims)
    if ((m = t.match(/^(\d{1,3})%$/))) { out.pct = +m[1]; take(i); continue; }
    // expiry words
    if (t === "0dte" || t === "odte" || t === "today" || t === "eod") { out.exps.push({ i, iso: todayIso }); take(i); continue; }
    if (t === "tmr" || t === "tmrw" || t === "tomorrow") { out.exps.push({ i, iso: nextTradingDay(todayIso) }); take(i); continue; }
    if ((t === "this" || t === "next") && WEEKDAYS[nx]) {
      let iso = comingWeekday(todayIso, WEEKDAYS[nx]);
      if (t === "next") iso = isoAdd(iso, 7);
      out.exps.push({ i, iso }); take(i, 2); continue;
    }
    if (WEEKDAYS[t]) { out.exps.push({ i, iso: comingWeekday(todayIso, WEEKDAYS[t]) }); take(i); continue; }
    if (MONTHS[t] && nx && /^\d{1,2}(st|nd|rd|th)?$/.test(nx)) {
      const iso = mkIso(+todayIso.slice(0, 4), MONTHS[t], parseInt(nx, 10), todayIso, false);
      if (iso) { out.exps.push({ i, iso }); take(i, 2); continue; }
    }
    // price marker: "@ .39" / "at .39"
    if ((t === "@" || t === "at" || t === "for") && nx && (m = nx.match(new RegExp(`^${NUM}(c)?$`)))) {
      const cents = m[2] === "c";
      out.prices.push({ i: i + 1, v: cents ? num(m[1]) / 100 : num(m[1]), score: 10 }); take(i, 2); continue;
    }
    if (t === "@" || t === "at" || t === "for") { take(i); continue; }
    // spread written in one token: 345/340p, 345p/340p, 345-340p, $345/$340, 345/340 (with a right word next)
    if ((m = t.match(new RegExp(`^\\$?(\\d+(?:\\.\\d+)?)${RIGHT_RE}?[/\\-]\\$?(\\d+(?:\\.\\d+)?)${RIGHT_RE}?$`)))) {
      const a = +m[1], b = +m[3], r1 = m[2] && RIGHT[m[2]], r2 = m[4] && RIGHT[m[4]];
      const rightNext = isRightTok(nx) ? RIGHT[nx] : null;
      const looksDate = !r1 && !r2 && a >= 1 && a <= 12 && b >= 1 && b <= 31 && Number.isInteger(a) && Number.isInteger(b);
      if (!looksDate) {
        const right = r1 || r2 || rightNext || null;
        out.spreads.push({ i, a, b, right });
        take(i, rightNext && !r1 && !r2 ? 2 : 1);
        continue;
      }
    }
    // dates: 10/30, 10-30, 10/30/26
    if ((m = t.match(/^(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?$/))) {
      let yr = m[3] ? +m[3] : +todayIso.slice(0, 4);
      if (yr < 100) yr += 2000;
      const iso = mkIso(yr, +m[1], +m[2], todayIso, !!m[3]);
      if (iso) { out.exps.push({ i, iso }); take(i); continue; }
    }
    // strike glued to put/call: 345p, 345.5p, $345p, 345put, 345calsl
    if ((m = t.match(new RegExp(`^\\$?(\\d+(?:\\.\\d+)?)${RIGHT_RE}$`)))) {
      out.contracts.push({ i, strike: +m[1], right: RIGHT[m[2]], raw: m[1], cents: m[2] === "c" && !t.startsWith("$") });
      take(i); continue;
    }
    // p345 / c345
    if ((m = t.match(/^(p|c)\$?(\d+(?:\.\d+)?)$/))) { out.contracts.push({ i, strike: +m[2], right: RIGHT[m[1]], raw: m[2] }); take(i); continue; }
    // number followed by a put/call word: 345 p, 345 put
    if ((m = t.match(new RegExp(`^${NUM}$`))) && isRightTok(nx) && !String(m[1]).startsWith(".")) {
      out.contracts.push({ i, strike: num(m[1]), right: RIGHT[nx], raw: m[1].replace(/^\$/, "") }); take(i, 2); continue;
    }
    // bare right word
    if (isRightTok(t)) { out.rights.push({ i, right: RIGHT[t] }); take(i); continue; }
    // cents: 39c handled above as a contract candidate; 39cents
    if ((m = t.match(/^(\d{1,2})(cents?)$/))) { out.prices.push({ i, v: +m[1] / 100, score: 9 }); take(i); continue; }
    // plain numbers
    if ((m = t.match(new RegExp(`^(\\$)?(\\d+(?:\\.\\d+)?|\\.\\d+)$`)))) {
      out.nums.push({ i, v: +m[2], raw: m[2], dollar: !!m[1] }); take(i); continue;
    }
    // ticker
    if ((m = t.match(/^\$([a-z]{1,5})$/))) { out.tickers.push({ i, t: m[1].toUpperCase(), dollar: true }); take(i); continue; }
    if (/^[a-z]{1,5}$/.test(t) && !NOT_TICKERS.has(t)) { out.tickers.push({ i, t: t.toUpperCase() }); take(i); continue; }
    if (!FILLER.has(t)) out.unknown.push(t);
  }
  return out;
}

// How much a bare number looks like an option price (vs a strike).
function priceScore(n, isLast) {
  let s = 0;
  if (n.raw.startsWith(".") || /^0\.\d/.test(n.raw)) s += 4;
  if (n.dollar && n.v < 50) s += 3;
  const dec = (n.raw.split(".")[1] || "").length;
  if (dec === 2) s += 2;
  if (dec === 1 && n.v < 10) s += 1;
  if (Number.isInteger(n.v) && n.v >= 20) s -= 3;
  if (dec === 1 && n.v >= 10 && /\.5$/.test(n.raw)) s -= 2;
  if (isLast) s += 1;
  return s;
}

// Pull the pieces together. kind: "entry" | "exit" | "fragment"
function assemble(cl, kind) {
  const r = { ticker: null, strike: null, right: null, exp: null, price: null, qty: cl.qty, pct: cl.pct,
    spread: false, long: null, short: null, spreadType: null, nums: [], stop: cl.stop };
  const dollarTick = cl.tickers.find((x) => x.dollar);
  r.ticker = (dollarTick || cl.tickers[0] || {}).t || null;
  if (cl.exps.length) r.exp = cl.exps[cl.exps.length - 1].iso;
  let prices = [...cl.prices];
  let contracts = [...cl.contracts];
  let nums = [...cl.nums];
  const rightWord = cl.rights.length ? cl.rights[0].right : null;

  // "39c" read as 39 cents when there is another strike and it can't be a leg of it
  if (contracts.length >= 2 && !prices.length) {
    const big = Math.max(...contracts.map((c) => c.strike));
    const idx = contracts.findIndex((c) => c.cents && c.strike < 100 && (c.strike < 0.5 * big ||
      contracts.some((o) => o !== c && o.right !== c.right)));
    if (idx >= 0) { prices.push({ i: contracts[idx].i, v: contracts[idx].strike / 100, score: 9 }); contracts.splice(idx, 1); }
  }

  // price: an explicit one wins, otherwise the most money-looking bare number (ties -> the last one)
  if (!prices.length && nums.length) {
    const lastI = Math.max(...nums.map((n) => n.i));
    let best = null;
    for (const n of nums) {
      const s = priceScore(n, n.i === lastI);
      if (!best || s > best.s || (s === best.s && n.i > best.n.i)) best = { n, s };
    }
    const haveStrike = contracts.length || cl.spreads.length;
    // with no strike typed anywhere, the price must look like money; a lone big integer is a strike
    if (best && (haveStrike || best.s >= 1 || nums.length === 1 && kind === "exit")) {
      prices.push({ i: best.n.i, v: best.n.v, score: best.s });
      nums = nums.filter((n) => n !== best.n);
    }
  }
  if (prices.length) r.price = prices.sort((a, b) => b.score - a.score || b.i - a.i)[0].v;

  // spreads
  let legs = null, right = null;
  if (cl.spreads.length) {
    const s = cl.spreads[0]; legs = [s.a, s.b]; right = s.right || rightWord || (contracts[0] && contracts[0].right) || null;
  } else if (contracts.length >= 2 && contracts[0].right === contracts[1].right) {
    legs = [contracts[0].strike, contracts[1].strike]; right = contracts[0].right;
  } else if (contracts.length === 1 && nums.length >= 1 && kind !== "exit" &&
             (cl.spreadWord || (Number.isInteger(nums[0].v) || /\.5$/.test(nums[0].raw)) && Math.abs(nums[0].v - contracts[0].strike) <= 0.25 * contracts[0].strike && nums[0].v >= 5)) {
    legs = [contracts[0].strike, nums[0].v]; right = contracts[0].right; nums = nums.slice(1);
  } else if (!contracts.length && nums.length >= 2 && (cl.spreadWord || rightWord) && kind !== "exit") {
    const strikeNums = nums.filter((n) => !(Number.isInteger(n.v) && n.v <= 3 && nums.length > 2));
    if (strikeNums.length >= 2) { legs = [strikeNums[0].v, strikeNums[1].v]; right = rightWord; nums = nums.filter((n) => !strikeNums.slice(0, 2).includes(n)); }
  }
  if (legs && legs[0] !== legs[1]) {
    r.spread = true; r.right = right;
    r.spreadType = cl.credit ? "credit" : "debit";
    const hi = Math.max(...legs), lo = Math.min(...legs);
    // debit: put spread buys the higher strike, call spread buys the lower. credit: the reverse.
    const buyHigh = (right === "P") === (r.spreadType === "debit");
    r.long = String(buyHigh ? hi : lo); r.short = String(buyHigh ? lo : hi);
    r.strike = `${r.long}/${r.short}`;
  } else if (contracts.length) {
    r.strike = String(contracts[0].raw !== undefined ? +contracts[0].raw : contracts[0].strike);
    r.right = contracts[0].right;
  } else if (cl.spreadWord && kind === "exit") {
    r.spread = true; r.right = rightWord;
  } else {
    r.right = rightWord;
    if (kind !== "exit" && nums.length) {
      // the most strike-looking leftover number
      const n = [...nums].sort((a, b) => priceScore(a, false) - priceScore(b, false))[0];
      r.strike = String(n.v); nums = nums.filter((x) => x !== n);
    }
  }
  r.nums = nums.map((n) => n.v);
  return r;
}

// ---------- main parser ----------
// Returns an object with .cmd. Entries/exits may carry `missing` and `guesses` for the bot to confirm.
export function parseCommand(raw, nowMs, ctx = {}) {
  const today = etParts(nowMs).date;
  let text = String(raw || "").trim();
  let note = "";
  const bar = text.indexOf("|");
  if (bar >= 0) {
    note = text.slice(bar + 1).trim();
    text = text.slice(0, bar).trim();
  }
  let toks = tokenize(text);
  if (!toks.length) return { cmd: "help" };

  const whole = toks.join(" ");
  if (YES.has(whole)) return { cmd: "yes" };
  if (NO.has(whole)) return { cmd: "no" };
  if (/^\d{1,2}$/.test(whole) && +whole >= 1 && +whole <= 20) return { cmd: "pick", n: +whole };

  let route = "main";
  if (toks[0] === "free") {
    route = "free";
    toks = toks.slice(1);
    if (!toks.length) return { cmd: "error", msg: "Free what? Example: `free in qqq 717p 10/23 .45`" };
  }

  const first = toks[0];
  const other = OTHER_CMDS[first];
  if (other === "plan") {
    let original = String(raw).trim().replace(/^(free\s+)?\S+\s*/i, ""); // keep his casing/wording
    const tick = toks.slice(1).find((t) => /^\$?[a-z]{1,5}$/.test(t) && !NOT_TICKERS.has(t.replace(/^\$/, "")));
    if (!tick) return { cmd: "error", msg: "Plan needs a ticker. Example: `plan qqq 727 stop 733`" };
    const tk = tick.replace(/^\$/, "");
    original = original.replace(new RegExp(`^\\$?${tk}\\b\\s*`, "i"), "") || original;
    const sm = original.match(/stop\s*@?\$?(\d+(?:\.\d+)?)/i);
    return { cmd: "plan", ticker: tk.toUpperCase(), text: original, stop: sm ? +sm[1] : null, route };
  }
  if (other === "grade" || other === "check") {
    const tick = toks.slice(1).map((t) => t.replace(/^\$/, "")).find((t) => /^[a-z]{1,5}$/.test(t) && !NOT_TICKERS.has(t));
    if (!tick) return { cmd: "error", msg: `${other === "grade" ? "Grade" : "Check"} what? Example: \`${other} hood\` (puts) or \`${other} hood c\` (calls)` };
    const side = toks.slice(1).some((t) => RIGHT[t] === "C") ? "C" : "P";
    return { cmd: other, ticker: tick.toUpperCase(), side };
  }
  if (other === "paper") {
    const v = toks[1] === "on" ? true : toks[1] === "off" ? false : null;
    return { cmd: "paper", value: v };
  }
  if (other === "note") {
    const t = String(raw).trim().replace(/^\S+\s*/, "");
    if (!t) return { cmd: "error", msg: "Note what? Example: `note 1h 10 SMA close target`" };
    return { cmd: "note", text: t };
  }
  if (other === "fix") return parseFix(toks.slice(1), today);
  if (other === "delete") {
    const n = toks.slice(1).map((t) => t.replace(/^#/, "")).find((t) => /^\d+$/.test(t));
    if (!n) return { cmd: "error", msg: "Delete which trade? Example: `delete 8` (the # from `open` or `recap`)." };
    return { cmd: "delete", id: +n };
  }
  if (other && toks.length <= 2 && !["fix", "delete"].includes(other)) return { cmd: other, route };

  const cl = classify(toks, today);
  const hasContract = cl.contracts.length || cl.spreads.length || (cl.rights.length && cl.nums.length);
  let cmd = null;
  if (cl.words.trim.length) cmd = "trim";
  else if (cl.words.exit.length) cmd = "out";
  else if (cl.words.entry.length) cmd = "in";
  else if (hasContract && (cl.tickers.length || cl.exps.length)) cmd = "in";
  if (!cmd) {
    if (other) return { cmd: other, route };
    return { cmd: "error", msg: `I couldn't read "${String(raw).trim().slice(0, 60)}" as a trade. Type \`help\` for examples.` };
  }
  if (cmd === "in") return { ...buildEntry(cl, today, ctx), note: joinNote(note, cl), route };
  return { ...buildExit(cmd, cl), note: joinNote(note, cl), route };
}

function joinNote(note, cl) {
  const parts = [];
  if (note) parts.push(note);
  if (cl.stop !== null) parts.push(`stop ${cl.stop}`);
  return parts.join(" / ");
}

function buildEntry(cl, today, ctx) {
  const a = assemble(cl, "entry");
  const missing = [], guesses = [];
  if (!a.ticker) {
    if (ctx.lastTicker) { a.ticker = ctx.lastTicker; guesses.push("ticker"); } else missing.push("ticker");
  }
  if (!a.strike) missing.push("strike");
  if (!a.right) { a.right = "P"; guesses.push("right"); }
  if (!a.exp) { a.exp = guessExpiry(today); guesses.push("exp"); }
  if (a.price === null) missing.push("price");
  else if (!(a.price > 0)) missing.push("price");
  return { cmd: "in", ticker: a.ticker, strike: a.strike, right: a.right, exp: a.exp, price: a.price, qty: a.qty || 1,
    spread: a.spread, long: a.long, short: a.short, spreadType: a.spreadType, missing, guesses };
}

function buildExit(cmd, cl) {
  const a = assemble(cl, "exit");
  let qty = a.qty;
  let half = cmd === "trim";
  if (a.pct !== null && a.pct < 100) half = a.pct === 50 ? true : half;
  return { cmd, ticker: a.ticker, strike: a.strike, right: a.right, exp: cl.exps.length ? a.exp : null, price: a.price,
    qty, pct: a.pct, spread: a.spread, nums: a.nums, missing: a.price === null ? ["price"] : [] };
}

// A follow-up message while the bot is waiting on a missing piece ("11/13", ".45", "aapl", "345p", "c").
export function parseFragment(raw, nowMs) {
  const today = etParts(nowMs).date;
  const toks = tokenize(raw);
  const cl = classify(toks, today);
  const a = assemble(cl, "fragment");
  const f = {};
  if (a.ticker) f.ticker = a.ticker;
  if (cl.exps.length) f.exp = a.exp;
  if (cl.contracts.length || cl.spreads.length) { f.strike = a.strike; f.right = a.right; if (a.spread) Object.assign(f, { spread: true, long: a.long, short: a.short, spreadType: a.spreadType }); }
  else if (a.right) f.right = a.right;
  if (a.price !== null) f.price = a.price;
  if (a.qty) f.qty = a.qty;
  // a lone integer with no decimals is a strike only when we asked for a strike
  if (!f.strike && a.strike) f.strikeGuess = a.strike;
  return f;
}

// Merge a follow-up into a pending entry. `asked` = what the bot asked for.
export function mergeEntry(pending, frag, asked = []) {
  const p = { ...pending, missing: [...(pending.missing || [])], guesses: [...(pending.guesses || [])] };
  const drop = (k) => { p.missing = p.missing.filter((x) => x !== k); p.guesses = p.guesses.filter((x) => x !== k); };
  if (frag.ticker) { p.ticker = frag.ticker; drop("ticker"); }
  if (frag.exp) { p.exp = frag.exp; drop("exp"); }
  if (frag.strike) {
    p.strike = frag.strike; drop("strike");
    if (frag.right) { p.right = frag.right; drop("right"); }
    if (frag.spread) Object.assign(p, { spread: true, long: frag.long, short: frag.short, spreadType: frag.spreadType });
  } else if (frag.right) { p.right = frag.right; drop("right"); }
  if (frag.price !== undefined && (asked.includes("price") || p.missing.includes("price"))) { p.price = frag.price; drop("price"); }
  else if (frag.strikeGuess && p.missing.includes("strike")) { p.strike = frag.strikeGuess; drop("strike"); }
  else if (frag.price !== undefined && p.missing.includes("strike") && frag.price >= 5) { p.strike = String(frag.price); drop("strike"); }
  if (frag.qty) p.qty = frag.qty;
  return p;
}

// ---------- fix ----------
function parseFix(toks, today) {
  const field = toks[0];
  const FIELDS = { price: "price", px: "price", prc: "price", prce: "price", entry: "price", fill: "price", cost: "price",
    strike: "strike", strk: "strike", stike: "strike", srike: "strike",
    exp: "exp", expiry: "exp", expiration: "exp", date: "exp", exipry: "exp", epx: "exp",
    qty: "qty", size: "qty", contracts: "qty", quantity: "qty", amt: "qty",
    ticker: "ticker", tick: "ticker", symbol: "ticker", sym: "ticker",
    right: "right", type: "right", side: "right" };
  let f = FIELDS[field];
  let rest = f ? toks.slice(1) : toks;
  const cl = classify(rest, today);
  if (!f) {
    // "fix 1.22" -> price, "fix put" / "fix c" -> right, "fix 11/13" -> exp, "fix x2" -> qty, "fix 345p" -> strike
    if (cl.contracts.length || cl.spreads.length) f = "strike";
    else if (cl.exps.length) f = "exp";
    else if (cl.qty) f = "qty";
    else if (cl.rights.length) f = "right";
    else if (cl.nums.length || cl.prices.length) f = "price";
    else if (cl.tickers.length) f = "ticker";
  }
  if (!f) return { cmd: "error", msg: "Fix what? Examples: `fix price 1.22`, `fix strike 345`, `fix exp 11/13`, `fix qty 2`." };
  if (f === "price") {
    const v = cl.prices.length ? cl.prices[0].v : cl.nums.length ? cl.nums[cl.nums.length - 1].v : cl.contracts.length && cl.contracts[0].cents ? cl.contracts[0].strike / 100 : null;
    if (!(v > 0)) return { cmd: "error", msg: "Fix price to what? Example: `fix price 1.22`" };
    return { cmd: "fix", field: "price", value: v };
  }
  if (f === "strike") {
    if (cl.spreads.length || (cl.contracts.length >= 2)) {
      const a = assemble(cl, "entry");
      return { cmd: "fix", field: "strike", value: a.strike, right: a.right, spread: true, long: a.long, short: a.short };
    }
    if (cl.contracts.length) return { cmd: "fix", field: "strike", value: String(cl.contracts[0].strike), right: cl.contracts[0].right };
    if (cl.nums.length) return { cmd: "fix", field: "strike", value: String(cl.nums[0].v), right: cl.rights[0] ? cl.rights[0].right : null };
    return { cmd: "error", msg: "Fix strike to what? Example: `fix strike 345`" };
  }
  if (f === "exp") {
    if (!cl.exps.length) return { cmd: "error", msg: "Fix exp to what? Example: `fix exp 11/13` or `fix exp fri`" };
    return { cmd: "fix", field: "exp", value: cl.exps[cl.exps.length - 1].iso };
  }
  if (f === "qty") {
    const v = cl.qty || (cl.nums.length ? cl.nums[0].v : null);
    if (!(v >= 1) || !Number.isInteger(v)) return { cmd: "error", msg: "Fix qty to what? Example: `fix qty 2`" };
    return { cmd: "fix", field: "qty", value: v };
  }
  if (f === "right") {
    const r = cl.rights[0] ? cl.rights[0].right : (rest[0] && RIGHT[rest[0]]) || null;
    if (!r) return { cmd: "error", msg: "Fix to put or call? Example: `fix put`" };
    return { cmd: "fix", field: "right", value: r };
  }
  if (f === "ticker") {
    if (!cl.tickers.length) return { cmd: "error", msg: "Fix ticker to what? Example: `fix ticker aapl`" };
    return { cmd: "fix", field: "ticker", value: cl.tickers[0].t };
  }
  return { cmd: "error", msg: "Fix what?" };
}

// ---------- matching an exit to open positions ----------
// rows: open positions. Returns { matches, used: {strike, qty} } where matches is the filtered list.
export function matchExit(c, rows) {
  let m = rows.slice();
  const usedNums = [];
  let qty = c.qty || null;
  if (c.ticker) m = m.filter((p) => p.ticker === c.ticker);
  if (c.right) m = m.filter((p) => p.right === c.right);
  if (c.exp) m = m.filter((p) => p.exp === c.exp);
  if (c.spread) m = m.filter((p) => String(p.strike).includes("/"));
  const legs = (p) => String(p.strike).split("/").map(Number);
  if (c.strike) {
    const want = String(c.strike).split("/").map(Number);
    m = m.filter((p) => want.every((w) => legs(p).includes(w)));
  }
  for (const n of c.nums || []) {
    const hit = m.filter((p) => legs(p).includes(n));
    if (hit.length) { m = hit; usedNums.push(n); }
    else if (!qty && Number.isInteger(n) && n >= 1 && m.some((p) => p.open_qty >= n)) { qty = n; usedNums.push(n); }
  }
  return { matches: m, qty };
}

// True when the message carries its own in/out/trim word (so it is a new order, not an answer to a question).
export function hasCommandWord(text) {
  return tokenize(text).some((t) => ENTRY_WORDS.has(t) || EXIT_WORDS.has(t) || TRIM_WORDS.has(t));
}

// ---------- which messages are meant for the bot ----------
const SOLO = new Set(["recap", "today", "status", "open", "positions", "log", "export", "undo", "help",
  "commands", "live", "test", "paper", "paper on", "paper off", "cleanup"]);
export function looksLikeTrade(text, hasPending = false) {
  const t = String(text || "").trim().toLowerCase().replace(/\s+/g, " ");
  if (!t) return false;
  if (SOLO.has(t)) return true;
  const toks = tokenize(t);
  if (!toks.length) return false;
  const w = toks.join(" ");
  if (hasPending && (YES.has(w) || NO.has(w))) return true;
  if (hasPending && hasPending !== "cleanup" && (/^\d{1,2}$/.test(w) || /\d/.test(w) || toks.length <= 3)) return true;
  if (/^(free\s+)?(plan|setup|note|check|early|meter|grade|score|fix|fx|edit|delete|del|remove|rm)\s+\S/.test(t)) return true;
  const cl = classify(toks.filter((x) => x !== "free"), "2026-01-01");
  const cmdWord = cl.words.entry.length + cl.words.exit.length + cl.words.trim.length > 0;
  const contract = cl.contracts.length || cl.spreads.length || (cl.rights.length && cl.nums.length);
  const money = cl.prices.length || cl.nums.length;
  if (cmdWord && (money || contract)) return true;
  if (contract && (cl.tickers.length || cl.exps.length)) return true;
  return false;
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

export function fmtDate(iso) {
  const [, m, d] = iso.split("-");
  return `${+m}/${+d}`;
}

export function contractLabel(p) {
  return `${p.ticker} ${p.strike}${p.right} ${fmtDate(p.exp)}`;
}

export function fmtPx(n) {
  return Number(n).toFixed(2);
}

// "AAPL 345/340P 11/13 @ 0.79"
export function tradeLine(p, price) {
  return `${contractLabel(p)} @ ${fmtPx(price)}`;
}
