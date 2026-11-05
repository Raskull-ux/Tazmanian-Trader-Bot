// End-to-end: the real TradeStore (index.js) on a real SQLite db, with Discord and market data mocked.
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { TradeStore } from "../src/index.js";

const posted = [], edited = [], deleted = [];
let nextMsg = 100;
globalThis.fetch = async (url, opts = {}) => {
  const u = String(url);
  if (u.includes("discord.com")) {
    const m = opts.method || "GET";
    if (m === "POST") { posted.push(JSON.parse(opts.body)); return new Response(JSON.stringify({ id: String(nextMsg++) }), { status: 200 }); }
    if (m === "PATCH") { edited.push({ url: u, body: JSON.parse(opts.body) }); return new Response("{}", { status: 200 }); }
    if (m === "DELETE") { deleted.push(u); return new Response(null, { status: 204 }); }
    return new Response("[]", { status: 200 });
  }
  return new Response("no data in tests", { status: 503 }); // Alpaca: meter/grade say "no data"
};

function makeStore() {
  const db = new DatabaseSync(":memory:");
  const sql = {
    exec(q, ...args) {
      if (!args.length && q.trim().split(";").filter((x) => x.trim()).length > 1) { db.exec(q); return { toArray: () => [] }; }
      const st = db.prepare(q);
      const rows = st.all(...args);
      return { toArray: () => rows.map((r) => ({ ...r })) };
    },
  };
  const ctx = { storage: { sql, getAlarm: async () => null, setAlarm: async () => {} } };
  const env = { PRIVATE_CHANNEL_ID: "priv", VIP_CHANNEL_ID: "vip", DISCORD_BOT_TOKEN: "x", DISCORD_API: "https://discord.com/api/v10" };
  return new TradeStore(ctx, env);
}

// Wed 2026-10-21, 11:00 ET
let T = Date.UTC(2026, 9, 21, 15, 0);
const S = makeStore();
const say = async (t) => { T += 60000; const r = await S.handle(t, T, { meterTimeout: 50 }); return r.reply; };
const pos = (id) => S.one("SELECT * FROM positions WHERE id=?", id);
const openN = () => S.all("SELECT * FROM positions WHERE status='open'").length;
let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };

// 1) the three word orders log the same trade
let r = await say("aapl 345p 10/30 .39 in"); ok(r.includes("AAPL 345P 10/30 @ 0.39"), r);
ok(r.includes("My position, not advice. Education and entertainment only."), "footer on entry alerts");
r = await say("in .39 aapl 10/30 345p"); ok(pos(2).ticker === "AAPL" && pos(2).strike === "345" && pos(2).entry === 0.39, "order 2");
r = await say("345 put aapl 10/30 @ .39"); ok(pos(3).exp === "2026-10-30" && pos(3).right === "P", "order 3");
ok(openN() === 3, "3 open");

// 2) exits: several match -> numbered list -> "1"
r = await say("out aapl 1.22"); ok(r.includes("❓") && r.includes("**1**)") && r.includes("**3**)"), r);
r = await say("2"); ok(pos(2).status === "closed", "picked #2 closed: " + r);
ok(S.one("SELECT price FROM fills WHERE position_id=2 AND side='sell'").price === 1.22, "price kept through the pick");

// 3) the real failed message: never reads 345 or 10/26 as the price
await say("delete 1"); await say("delete 3"); ok(openN() === 0, "clean slate");
await say("in aapl 345p 10/26 .80");
r = await say("Out aapl 345 10/26 put 1.22");
const p4 = S.one("SELECT * FROM positions ORDER BY id DESC LIMIT 1");
ok(p4.status === "closed" && S.one("SELECT price FROM fills WHERE position_id=? AND side='sell'", p4.id).price === 1.22, r);

// 4) missing expiry -> best guess + y
r = await say("in aapl 345p .39"); ok(r.includes("❓") && r.includes("10/30") && r.includes("**y**"), r);
const before = S.one("SELECT COUNT(*) n FROM positions").n;
r = await say("y"); ok(S.one("SELECT COUNT(*) n FROM positions").n === before + 1, "y logs it: " + r);

// 5) missing price -> send it
r = await say("in qqq 717p 10/23"); ok(r.includes("price"), r);
r = await say(".45"); const q = S.one("SELECT * FROM positions WHERE ticker='QQQ'"); ok(q && q.entry === 0.45, "price follow-up: " + r);

// 6) no put/call -> guess put, reply c fixes it
r = await say("In aapl 342.5 10/23 2x @ .84"); ok(r.includes("PUT"), r);
r = await say("c"); ok(r.includes("342.5C"), "sending the fix logs it: " + r);
const a2 = S.one("SELECT * FROM positions WHERE strike='342.5'"); ok(a2 && a2.right === "C" && a2.qty === 2 && a2.entry === 0.84, "342.5C x2");

// 7) MSFT $522.5p and PLTR exits
await say("In MSFT $522.5p 10/26 1.82"); ok(S.one("SELECT * FROM positions WHERE ticker='MSFT'").strike === "522.5", "msft");
await say("in pltr 195p 10/30 .40"); r = await say("Out PLTR 195 put .59");
ok(S.one("SELECT * FROM positions WHERE ticker='PLTR'").status === "closed", r);

// 8) spreads: logged as one position, exits by "out spread"
r = await say("bear put aapl 345 340 11/13 .79"); ok(r.includes("AAPL 345/340P 11/13 @ 0.79"), r);
const sp = S.one("SELECT * FROM positions WHERE strike='345/340'");
ok(sp.long_strike === "345" && sp.short_strike === "340" && sp.spread_type === "debit", "legs");
r = await say("out spread 1.20"); ok(S.one("SELECT * FROM positions WHERE id=?", sp.id).status === "closed", r);
ok(r.includes("My position, not advice."), "footer on exit alerts");
await say("paper"); r = await say("in amd 230p 11/13 1.05"); ok(r.includes("PAPER IDEA") && r.includes("Idea, not a position") && !r.includes("PAPER ALERT"), "paper = Idea");
await say("undo"); await say("paper off");

// 9) half / trim / sold half (only one open, so no ticker needed)
for (const o of S.all("SELECT id FROM positions WHERE status='open'")) await say(`delete ${o.id}`);
await say("in tsla 400p 11/13 1.00 x4");
const ts = S.one("SELECT * FROM positions WHERE ticker='TSLA'");
r = await say("half 2.10"); ok(pos(ts.id).open_qty === 2, r);
r = await say("sold half at 2.5"); ok(pos(ts.id).open_qty === 1, r);
r = await say("out tsla 1.80"); ok(pos(ts.id).status === "closed", r);

// 10) fix after the fact (and the post gets edited in live mode)
await say("live");
await say("in nvda 180p 11/13 .62");
const nv = S.one("SELECT * FROM positions WHERE ticker='NVDA'");
ok(nv.msg_id, "posted to VIP");
r = await say("fix price .65"); ok(pos(nv.id).entry === 0.65 && edited.length === 1 && edited[0].body.content.includes("0.65"), r);
r = await say("fix strike 182"); ok(pos(nv.id).strike === "182", r);
r = await say("fix exp 11/20"); ok(pos(nv.id).exp === "2026-11-20", r);
r = await say("fix qty 2"); ok(pos(nv.id).qty === 2 && pos(nv.id).open_qty === 2, r);
r = await say("out nvda 1.00 x1"); r = await say("fix price 1.05");
ok(S.one("SELECT price FROM fills WHERE position_id=? AND side='sell'", nv.id).price === 1.05, "fix the sell price: " + r);
await say("test");

// 11) undo and delete
const cnt = S.one("SELECT COUNT(*) n FROM positions").n;
await say("in amd 230c 11/13 1.05"); r = await say("undo"); ok(S.one("SELECT COUNT(*) n FROM positions").n === cnt, r);
r = await say("delete 999"); ok(r.includes("No trade #999"), r);

// 12) a new full trade line while a question is open replaces the question
r = await say("in hood 120p .88"); ok(r.includes("❓"), r);
r = await say("in meta 700p 11/13 2.15"); ok(S.one("SELECT * FROM positions WHERE ticker='META'"), "new trade logged");
r = await say("y"); ok(!S.one("SELECT * FROM positions WHERE ticker='HOOD'"), "old question dropped");

// 13) cleanup of the stuck positions: listed first, removed only after y
const S2 = makeStore();
for (let k = 1; k <= 8; k++) await S2.handle(`in qqq ${700 + k}p 11/13 .50`, T + k * 1000, { meterTimeout: 50 });
for (const k of [1, 4, 5, 6]) await S2.handle(`out qqq ${700 + k}p .60`, T + 20000 + k, { meterTimeout: 50 });
posted.length = 0;
await S2.cleanupAsk(T + 60000);
ok(posted.length === 1 && posted[0].content.includes("#2") && posted[0].content.includes("#8") && !posted[0].content.includes("#1 "), "listed in private");
ok(S2.all("SELECT * FROM positions WHERE status='open'").length === 4, "nothing removed before y");
r = (await S2.handle("y", T + 70000)).reply; ok(r.includes("Removed #2, #3, #7, #8") && S2.all("SELECT * FROM positions WHERE status='open'").length === 0, r);
await S2.cleanupAsk(T + 99999999); ok(posted.length === 1, "never asks again");

console.log(`bot tests: all ${n} passed`);
