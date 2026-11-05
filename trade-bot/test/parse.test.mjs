import assert from "node:assert/strict";
import {
  parseCommand, parseFragment, mergeEntry, matchExit, looksLikeTrade, planTradeDate, nextTradingDay, guessExpiry,
  contractLabel, tradeLine,
} from "../src/parse.js";

// Wed 2026-10-21 10:00 ET = 14:00 UTC
const NOW = Date.UTC(2026, 9, 21, 14, 0);
const p = (t, ctx = { lastTicker: "QQQ" }) => parseCommand(t, NOW, ctx);
let n = 0;
const ok = (cond, msg) => { assert.ok(cond, msg); n++; };
function entry(t, want) {
  const r = p(t);
  assert.equal(r.cmd, "in", `${t}: cmd ${r.cmd} ${r.msg || ""}`);
  for (const [k, v] of Object.entries(want)) assert.deepEqual(r[k], v, `${t}: ${k} = ${JSON.stringify(r[k])}, want ${JSON.stringify(v)}`);
  n++; return r;
}
function exit(t, want) {
  const r = p(t);
  assert.ok(r.cmd === "out" || r.cmd === "trim", `${t}: cmd ${r.cmd} ${r.msg || ""}`);
  for (const [k, v] of Object.entries(want)) assert.deepEqual(r[k], v, `${t}: ${k} = ${JSON.stringify(r[k])}, want ${JSON.stringify(v)}`);
  n++; return r;
}
const AAPL = { ticker: "AAPL", strike: "345", right: "P", exp: "2026-10-30", price: 0.39, missing: [], guesses: [] };

// ---------------- any word order: all mean the same entry ----------------
entry("aapl 345p 10/30 .39 in", AAPL);
entry("in .39 aapl 10/30 345p", AAPL);
entry("345 put aapl 10/30 @ .39", AAPL);

// ---------------- sloppy input ----------------
for (const tk of ["$AAPL", "aapl", "Aapl", "AAPL"]) entry(`in ${tk} 345p 10/30 .39`, AAPL);
for (const k of ["345p", "345 p", "345 put", "345P", "$345p", "p345", "345 puts", "345put"]) entry(`in aapl ${k} 10/30 .39`, AAPL);
for (const pr of [".39", "0.39", "$.39", "@.39", "@ .39", "39c", "at .39"]) entry(`in aapl 345p 10/30 ${pr}`, AAPL);
for (const q of ["x2", "2x", "2 contracts", "qty 2", "x 2", "qty:2", "2 cons"]) entry(`in aapl 345p 10/30 .39 ${q}`, { ...AAPL, qty: 2 });
entry("in aapl 345p 10/30 .39", { qty: 1 });
// dates (today = Wed 10/21)
for (const [d, iso] of [["10/30", "2026-10-30"], ["10-30", "2026-10-30"], ["oct 30", "2026-10-30"], ["Oct30", "2026-10-30"],
  ["october 30", "2026-10-30"], ["10/30/26", "2026-10-30"], ["fri", "2026-10-23"], ["friday", "2026-10-23"], ["this fri", "2026-10-23"],
  ["next fri", "2026-10-30"], ["tmr", "2026-10-22"], ["tomorrow", "2026-10-22"], ["0dte", "2026-10-21"], ["today", "2026-10-21"]]) {
  entry(`in aapl 345p ${d} .39`, { exp: iso });
}
// common typos
entry("inn aapl 345p 10/30 .39", AAPL);
entry("in aapl 345 puts 10/30 .39", AAPL);
entry("in aapl 345 calsl 10/30 .39", { right: "C", strike: "345" });
exit("otu 1.22", { cmd: "out", price: 1.22 });
exit("oit aapl 1.22", { cmd: "out", ticker: "AAPL", price: 1.22 });

// ---------------- spreads ----------------
const SPR = { ticker: "AAPL", strike: "345/340", right: "P", exp: "2026-11-13", price: 0.79, spread: true, long: "345", short: "340", spreadType: "debit" };
for (const t of ["in aapl 345/340p 11/13 .79", "in aapl 345p/340p 11/13 .79", "in aapl 345p 340p 11/13 .79", "in aapl 345/340 put spread 11/13 .79",
  "bear put aapl 345 340 11/13 .79", "spread aapl 345 340 put 11/13 .79", "in aapl 345-340 p 11/13 .79", "aapl 345 340 put 11/13 .79",
  "in aapl 340/345p 11/13 .79"]) entry(t, SPR);
const CSPR = { ticker: "AAPL", strike: "340/345", right: "C", spread: true, long: "340", short: "345", spreadType: "debit", price: 0.79 };
for (const t of ["in aapl 340/345c 11/13 .79", "in aapl 340c/345c 11/13 .79", "bull call aapl 340 345 11/13 .79", "in aapl 340-345 c 11/13 .79",
  "in aapl 340/345 call spread 11/13 .79", "spread aapl 340 345 calls 11/13 .79"]) entry(t, CSPR);
entry("in aapl 340/335p 11/13 1.10 credit", { spreadType: "credit", long: "335", short: "340", strike: "335/340", price: 1.1 });
ok(contractLabel({ ticker: "AAPL", strike: "345/340", right: "P", exp: "2026-11-13" }) === "AAPL 345/340P 11/13", "spread label");
ok(tradeLine({ ticker: "AAPL", strike: "345/340", right: "P", exp: "2026-11-13" }, 0.79) === "AAPL 345/340P 11/13 @ 0.79", "spread line");
exit("out spread 1.20", { cmd: "out", spread: true, price: 1.2 });
exit("out aapl 1.20", { ticker: "AAPL", price: 1.2 });

// ---------------- exits that just work ----------------
exit("out 1.22", { cmd: "out", price: 1.22, ticker: null });
exit("out aapl 1.22", { cmd: "out", ticker: "AAPL", price: 1.22 });
exit("out aapl 345 10/26 put 1.22", { cmd: "out", ticker: "AAPL", right: "P", exp: "2026-10-26", price: 1.22, nums: [345] });
exit("half 0.80", { cmd: "trim", price: 0.8 });
exit("trim 50% .80", { cmd: "trim", price: 0.8, pct: 50 });
exit("sold half at .8", { cmd: "trim", price: 0.8 });

// ---------------- Taz's real failed messages ----------------
exit("Out aapl 345 10/26 put 1.22", { cmd: "out", ticker: "AAPL", right: "P", price: 1.22, nums: [345], exp: "2026-10-26" });
entry("In MSFT $522.5p 10/26 1.82", { ticker: "MSFT", strike: "522.5", right: "P", exp: "2026-10-26", price: 1.82, missing: [], guesses: [] });
entry("In aapl 342.5 10/23 2x @ .84", { ticker: "AAPL", strike: "342.5", right: "P", exp: "2026-10-23", price: 0.84, qty: 2, guesses: ["right"], missing: [] });
exit("Out PLTR 195 put .59", { cmd: "out", ticker: "PLTR", strike: "195", right: "P", price: 0.59 });

// ---------------- never just fail: best guess + what's missing ----------------
entry("in aapl 345p .39", { exp: guessExpiry("2026-10-21"), guesses: ["exp"], missing: [] });
ok(guessExpiry("2026-10-21") === "2026-10-30" && guessExpiry("2026-11-05") === "2026-11-13", "nearest Friday a week out");
entry("in aapl 345p 10/30", { missing: ["price"] });
entry("in qqq .45", { missing: ["strike"] });
entry("in 717p 10/23 .45", { ticker: "QQQ", guesses: ["ticker"] });
ok(p("in 717p 10/23 .45", {}).missing.includes("ticker"), "no last ticker -> ask");
exit("out", { missing: ["price"] });
exit("out aapl", { ticker: "AAPL", missing: ["price"] });

// ---------------- confirmations and picks ----------------
for (const y of ["y", "Y", "yes", "yep", "yeah", "yup", "ok"]) ok(p(y).cmd === "yes", y);
for (const no of ["n", "no", "nope", "cancel"]) ok(p(no).cmd === "no", no);
ok(p("1").cmd === "pick" && p("1").n === 1 && p("#2").n === 2, "pick");

// fragments answering a question
let pend = p("in aapl 345p");
let fr = parseFragment("11/13", NOW); ok(fr.exp === "2026-11-13", "frag date");
pend = mergeEntry(pend, fr, pend.missing); ok(pend.exp === "2026-11-13" && !pend.guesses.includes("exp"), "merge date");
pend = mergeEntry(pend, parseFragment(".39", NOW), pend.missing); ok(pend.price === 0.39 && !pend.missing.length, "merge price");
let pend2 = p("in qqq .45"); pend2 = mergeEntry(pend2, parseFragment("717p", NOW), pend2.missing);
ok(pend2.strike === "717" && pend2.right === "P" && !pend2.missing.length, "merge strike");
let pend3 = p("In aapl 342.5 10/23 2x @ .84"); pend3 = mergeEntry(pend3, parseFragment("c", NOW), []);
ok(pend3.right === "C" && !pend3.guesses.length, "merge right");
let pend4 = p("in qqq .45"); pend4 = mergeEntry(pend4, parseFragment("717", NOW), pend4.missing); ok(pend4.strike === "717", "bare strike");

// ---------------- fix / delete / undo ----------------
const fx = (t, f, v) => { const r = p(t); assert.equal(r.cmd, "fix", t); assert.equal(r.field, f, t); assert.deepEqual(r.value, v, t); n++; };
fx("fix price 1.22", "price", 1.22); fx("fix px .5", "price", 0.5); fx("fix 1.22", "price", 1.22);
fx("fix strike 345", "strike", "345"); fx("fix strike 345p", "strike", "345"); fx("fix 345c", "strike", "345");
fx("fix exp 11/13", "exp", "2026-11-13"); fx("fix date fri", "exp", "2026-10-23"); fx("fix 11/13", "exp", "2026-11-13");
fx("fix qty 2", "qty", 2); fx("fix size 3", "qty", 3); fx("fix x2", "qty", 2);
fx("fix put", "right", "P"); fx("fix ticker msft", "ticker", "MSFT");
fx("fix strike 345/340p", "strike", "345/340");
ok(p("delete 8").cmd === "delete" && p("delete 8").id === 8 && p("del #8").id === 8 && p("remove 8").id === 8, "delete");
ok(p("undo").cmd === "undo", "undo");
ok(p("cleanup").cmd === "cleanup", "cleanup");

// ---------------- 30+ more realistic sloppy messages ----------------
entry("IN QQQ 717P 10/23 .45 X2", { ticker: "QQQ", strike: "717", right: "P", exp: "2026-10-23", price: 0.45, qty: 2 });
entry("in qqq 717 p 10/23 @ .45 x 2", { strike: "717", price: 0.45, qty: 2 });
entry("qqq 717p 10/23 .45", { ticker: "QQQ", price: 0.45 });
entry("in qqq 717p fri .45 2x", { exp: "2026-10-23", qty: 2 });
entry("In tsla 400p nov 6 1.2", { ticker: "TSLA", strike: "400", exp: "2026-11-06", price: 1.2 });
entry("in tsla 400 puts 11/6 $1.20 qty 3", { strike: "400", price: 1.2, qty: 3 });
entry("buy nvda 180p 10/30 .62", { ticker: "NVDA", strike: "180", price: 0.62 });
entry("bought meta 700p 10-30 2.15 2 cons", { ticker: "META", strike: "700", price: 2.15, qty: 2, exp: "2026-10-30" });
entry("in hood 120p next fri .88", { ticker: "HOOD", exp: "2026-10-30", price: 0.88 });
entry("in spy 600c tmr .30", { right: "C", exp: "2026-10-22", price: 0.3 });
entry("in amd 230 call 10/30 1.05", { ticker: "AMD", strike: "230", right: "C", price: 1.05 });
entry("in cvna 300p 10/30 3.1 | weekly lower highs", { ticker: "CVNA", price: 3.1, note: "weekly lower highs" });
entry("in qqq 717p 10/23 45c", { price: 0.45, strike: "717" });
entry("in qqq 717p 10/23 .45 stop 720", { price: 0.45, note: "stop 720", strike: "717" });
entry("in .39 x2 aapl 10/30 345p", { ...AAPL, qty: 2 });
entry("in msft 522.5p 10/26 1.82", { strike: "522.5", price: 1.82 });
entry("in sofi 12.5p 11/13 .21", { ticker: "SOFI", strike: "12.5", price: 0.21 });
entry("in qqq 717p 10/23 .45x2", { price: 0.45, qty: 2 });
entry("in qqq 717p 10/23/26 .45", { exp: "2026-10-23" });
entry("in spy 600c 1/16 2.10", { exp: "2027-01-16", price: 2.1 });
entry("in qqq 717p 10/23 1", { price: 1 });
entry("long pltr 195p 10/30 1.15", { ticker: "PLTR", strike: "195" });
exit("out qqq .70", { ticker: "QQQ", price: 0.7 });
exit("OUT QQQ .7", { ticker: "QQQ", price: 0.7 });
exit("sold qqq 1.05", { cmd: "out", ticker: "QQQ", price: 1.05 });
exit("out nvda 180 put .91", { ticker: "NVDA", strike: "180", right: "P", price: 0.91 });
exit("out .90 nvda", { ticker: "NVDA", price: 0.9 });
exit("out x1 .90", { qty: 1, price: 0.9 });
exit("trim 1 .90", { cmd: "trim", price: 0.9, nums: [1] });
exit("sold 2 at .8", { cmd: "out", price: 0.8, nums: [2] });
exit("stopped out .22", { cmd: "out", price: 0.22 });
exit("out 345/340p 1.20", { strike: "345/340", spread: true, price: 1.2 });
exit("out qqq 717p .70", { strike: "717", price: 0.7 });
exit("trim half qqq .90", { cmd: "trim", ticker: "QQQ", price: 0.9 });
exit("out aapl 1.22 | hit the 15m 200", { note: "hit the 15m 200", price: 1.22 });
exit("sell tsla 400p 2.3", { ticker: "TSLA", strike: "400", price: 2.3 });
exit("closed hood 1.4", { ticker: "HOOD", price: 1.4 });
ok(p("free in tsla 400p 10/31 1.2").route === "free" && p("free in tsla 400p 10/31 1.2").price === 1.2, "free route");
ok(p("blah").cmd === "error", "blah");

// ---------------- which chat lines the bot reads ----------------
for (const t of ["aapl 345p 10/30 .39 in", "in .39 aapl 10/30 345p", "345 put aapl 10/30 @ .39", "out 1.22", "half .80", "sold half at .8",
  "Out PLTR 195 put .59", "In aapl 342.5 10/23 2x @ .84", "fix price 1.22", "delete 8", "undo", "open", "recap", "bear put aapl 345 340 11/13 .79",
  "otu 1.22", "cleanup"]) ok(looksLikeTrade(t), `reads: ${t}`);
for (const t of ["I'm out for lunch", "lol", "in the zone today", "good morning", "out of here", "that was a nice dump"]) ok(!looksLikeTrade(t), `ignores: ${t}`);
ok(looksLikeTrade("y", true) && !looksLikeTrade("y", false), "y only while a question is open");
ok(looksLikeTrade("11/13", "entry") && looksLikeTrade(".45", "exitPrice") && looksLikeTrade("2", "choose"), "answers while a question is open");
ok(looksLikeTrade("y", "cleanup") && !looksLikeTrade("nice", "cleanup") && !looksLikeTrade("lol 2", "cleanup"), "cleanup question only takes y/n");

// ---------------- matching an exit to open positions ----------------
const rows = [
  { id: 2, ticker: "AAPL", strike: "345", right: "P", exp: "2026-10-26", open_qty: 1 },
  { id: 3, ticker: "AAPL", strike: "340", right: "P", exp: "2026-10-30", open_qty: 2 },
  { id: 5, ticker: "QQQ", strike: "717", right: "P", exp: "2026-10-23", open_qty: 2 },
  { id: 6, ticker: "AAPL", strike: "345/340", right: "P", exp: "2026-11-13", open_qty: 1 },
];
let m = matchExit(p("out aapl 345 10/26 put 1.22"), rows); ok(m.matches.length === 1 && m.matches[0].id === 2, "match by strike+date");
m = matchExit(p("out aapl 1.22"), rows); ok(m.matches.length === 3, "ambiguous -> ask");
m = matchExit(p("out qqq .70"), rows); ok(m.matches.length === 1 && m.matches[0].id === 5, "by ticker");
m = matchExit(p("out spread 1.20"), rows); ok(m.matches.length === 1 && m.matches[0].id === 6, "spread");
m = matchExit(p("out 345/340p 1.20"), rows); ok(m.matches.length === 1 && m.matches[0].id === 6, "spread by legs");
m = matchExit(p("out aapl 340 .5"), rows); ok(m.matches.length === 2, "340 matches the single and the spread leg");
m = matchExit(p("trim 1 .90"), [rows[2]]); ok(m.matches.length === 1 && m.qty === 1, "bare 1 = qty when no strike 1");
m = matchExit(p("out 1.22"), [rows[0]]); ok(m.matches.length === 1, "only one open");
m = matchExit(p("out msft 1.22"), rows); ok(m.matches.length === 0, "no match -> list");

// ---------------- plan + misc (unchanged behavior) ----------------
let r = p("plan QQQ puts 727-733 rejection stop 733"); ok(r.cmd === "plan" && r.ticker === "QQQ" && r.stop === 733 && r.text === "puts 727-733 rejection stop 733", "plan");
ok(p("paper off").value === false, "paper off");
ok(planTradeDate(Date.UTC(2026, 9, 23, 22, 0)) === "2026-10-26" && planTradeDate(Date.UTC(2026, 9, 21, 13, 0)) === "2026-10-21", "plan dates");
ok(nextTradingDay("2026-10-23") === "2026-10-26", "next trading day");
r = p("check qqq"); ok(r.cmd === "check" && r.ticker === "QQQ" && r.side === "P", "check");
ok(p("check aapl c").side === "C", "check calls");
ok(p("grade hood").cmd === "grade" && p("grade hood").ticker === "HOOD", "grade");
console.log(`parse tests: all ${n} passed`);
