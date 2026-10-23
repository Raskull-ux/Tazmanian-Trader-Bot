import assert from "node:assert/strict";
import { parseCommand, planTradeDate, nextTradingDay } from "../src/parse.js";

// Wed 2026-10-21 10:00 ET = 14:00 UTC
const NOW = Date.UTC(2026, 9, 21, 14, 0);
const p = (t) => parseCommand(t, NOW);

let r = p("in qqq 717p 10/23 .45 x2 | 1h 10 sma");
assert.equal(r.cmd, "in"); assert.equal(r.ticker, "QQQ"); assert.equal(r.strike, "717");
assert.equal(r.right, "P"); assert.equal(r.exp, "2026-10-23"); assert.equal(r.price, 0.45);
assert.equal(r.qty, 2); assert.equal(r.note, "1h 10 sma");

r = p("buy AAPL 342.5 put 10/30 @0.25"); assert.equal(r.strike, "342.5"); assert.equal(r.right, "P"); assert.equal(r.price, 0.25); assert.equal(r.qty, 1);
r = p("qqq 720/722c 10/26 .90 3x"); assert.equal(r.cmd, "in"); assert.equal(r.strike, "720/722"); assert.equal(r.right, "C"); assert.equal(r.qty, 3);
r = p("in spy 600c 0dte .30"); assert.equal(r.exp, "2026-10-21");
r = p("in spy 600c 1/16 2.10"); assert.equal(r.exp, "2027-01-16");
r = p("free in tsla 400p 10/31 1.2"); assert.equal(r.route, "free"); assert.equal(r.price, 1.2);
r = p("in qqq .45"); assert.equal(r.cmd, "error");
r = p("half .90"); assert.equal(r.cmd, "trim"); assert.equal(r.price, 0.9);
r = p("out qqq 1.05"); assert.equal(r.cmd, "out"); assert.equal(r.ticker, "QQQ"); assert.equal(r.price, 1.05);
r = p("out"); assert.equal(r.cmd, "error");
r = p("plan QQQ puts 727-733 rejection stop 733"); assert.equal(r.cmd, "plan"); assert.equal(r.ticker, "QQQ"); assert.equal(r.stop, 733); assert.equal(r.text, "puts 727-733 rejection stop 733");
r = p("paper off"); assert.equal(r.value, false);
r = p("blah"); assert.equal(r.cmd, "error");

// plan dates: Fri 6 PM ET -> Monday; Wed 9 AM -> same day
assert.equal(planTradeDate(Date.UTC(2026, 9, 23, 22, 0)), "2026-10-26");
assert.equal(planTradeDate(Date.UTC(2026, 9, 21, 13, 0)), "2026-10-21");
assert.equal(nextTradingDay("2026-10-23"), "2026-10-26");
console.log("parse tests: all passed");
r = parseCommand("check qqq", NOW); assert.equal(r.cmd, "check"); assert.equal(r.ticker, "QQQ"); assert.equal(r.side, "P");
r = parseCommand("check aapl c", NOW); assert.equal(r.side, "C");
console.log("check tests: passed");
r = parseCommand("grade hood", NOW); assert.equal(r.cmd, "grade"); assert.equal(r.ticker, "HOOD");
console.log("grade parse: passed");
