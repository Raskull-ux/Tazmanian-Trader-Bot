// Tazmanian trade bot: Discord /t command -> clean alert + trade log + rule checks.
// Runs free on Cloudflare Workers. State lives in one SQLite-backed Durable Object.
// It NEVER places orders. Robinhood has no official API; this only posts and logs.

import { DurableObject } from "cloudflare:workers";
import {
  parseCommand, etParts, fmtTime, planTradeDate, daysBetween,
  pct, fmtPct, money, contractLabel, fmtPx,
} from "./parse.js";

const SIGN_OFF = "Pattern. Process. Paid. 🌪️🔴";
const NFA = "_Not financial advice. My own position._";

// ---------------- Worker entry ----------------
export default {
  async fetch(request, env) {
    if (request.method === "GET") return new Response("Tazmanian trade bot is up.");
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });

    const sig = request.headers.get("x-signature-ed25519");
    const ts = request.headers.get("x-signature-timestamp");
    const body = await request.text();
    if (!sig || !ts || !(await verifySig(env.DISCORD_PUBLIC_KEY, sig, ts, body))) {
      return new Response("Bad request signature", { status: 401 });
    }
    const i = JSON.parse(body);
    if (i.type === 1) return json({ type: 1 }); // PING

    if (i.type === 2 && i.data && i.data.name === "t") {
      if (i.channel_id !== env.PRIVATE_CHANNEL_ID) {
        return json(reply("Use `/t` in your private trade channel only.", true));
      }
      const text = ((i.data.options || []).find((o) => o.name === "text") || {}).value || "";
      const store = env.STORE.get(env.STORE.idFromName("taz"));
      let out;
      try {
        out = await store.handle(text, Date.now());
      } catch (e) {
        return json(reply(`⚠️ Bot error, nothing was logged: ${String(e && e.message || e).slice(0, 300)}`));
      }
      if (out.file) {
        const form = new FormData();
        form.append("payload_json", JSON.stringify({
          type: 4,
          data: { content: out.reply, attachments: [{ id: 0, filename: out.file.name }] },
        }));
        form.append("files[0]", new Blob([out.file.content], { type: "text/csv" }), out.file.name);
        return new Response(form);
      }
      return json(reply(out.reply));
    }
    return json(reply("Unknown command.", true));
  },
};

function reply(content, ephemeral = false) {
  return {
    type: 4,
    data: { content: content.slice(0, 1990), flags: ephemeral ? 64 : 0, allowed_mentions: { parse: [] } },
  };
}

function json(obj) {
  return new Response(JSON.stringify(obj), { headers: { "content-type": "application/json" } });
}

function hexToBytes(h) {
  const out = new Uint8Array(h.length / 2);
  for (let k = 0; k < out.length; k++) out[k] = parseInt(h.substr(k * 2, 2), 16);
  return out;
}

async function verifySig(pubHex, sigHex, ts, body) {
  try {
    const data = new TextEncoder().encode(ts + body);
    let key;
    try {
      key = await crypto.subtle.importKey("raw", hexToBytes(pubHex), { name: "Ed25519" }, false, ["verify"]);
      return await crypto.subtle.verify("Ed25519", key, hexToBytes(sigHex), data);
    } catch (_) {
      key = await crypto.subtle.importKey("raw", hexToBytes(pubHex),
        { name: "NODE-ED25519", namedCurve: "NODE-ED25519" }, false, ["verify"]);
      return await crypto.subtle.verify("NODE-ED25519", key, hexToBytes(sigHex), data);
    }
  } catch (_) {
    return false;
  }
}

// ---------------- Durable Object: all state + logic ----------------
export class TradeStore extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.env = env;
    this.sql = ctx.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opened_at INTEGER, trade_date TEXT, ticker TEXT, strike TEXT, right TEXT, exp TEXT,
        entry REAL, qty INTEGER, open_qty INTEGER, status TEXT, paper INTEGER, route TEXT,
        note TEXT, flags TEXT, rule_break INTEGER DEFAULT 0, msg_channel TEXT, msg_id TEXT,
        closed_at INTEGER, close_date TEXT
      );
      CREATE TABLE IF NOT EXISTS fills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position_id INTEGER, ts INTEGER, trade_date TEXT, side TEXT, price REAL, qty INTEGER,
        note TEXT, msg_channel TEXT, msg_id TEXT
      );
      CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at INTEGER, trade_date TEXT, ticker TEXT, text TEXT, stop REAL,
        msg_channel TEXT, msg_id TEXT
      );
      CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
    `);
  }

  // ---- small db helpers ----
  all(q, ...a) { return this.sql.exec(q, ...a).toArray(); }
  one(q, ...a) { const r = this.all(q, ...a); return r.length ? r[0] : null; }
  getSetting(k, d) { const r = this.one("SELECT v FROM settings WHERE k=?", k); return r ? r.v : d; }
  setSetting(k, v) { this.sql.exec("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", k, String(v)); }
  mode() { return this.getSetting("mode", "test"); }
  paper() { return this.getSetting("paper", "0") === "1"; }

  realized(posId) {
    const p = this.one("SELECT * FROM positions WHERE id=?", posId);
    const sells = this.all("SELECT price, qty FROM fills WHERE position_id=? AND side='sell'", posId);
    let dollars = 0, q = 0, wsum = 0;
    for (const s of sells) { dollars += (s.price - p.entry) * 100 * s.qty; q += s.qty; wsum += s.price * s.qty; }
    const avgExit = q ? wsum / q : null;
    return { dollars, soldQty: q, avgExit, pct: avgExit ? pct(avgExit, p.entry) : null };
  }

  lossesOn(dateIso) {
    const rows = this.all("SELECT id FROM positions WHERE status='closed' AND close_date=? AND rule_break>=0", dateIso);
    return rows.filter((r) => this.realized(r.id).dollars < 0).length;
  }

  bigWinnerYesterday(todayIso) {
    const prev = this.one("SELECT MAX(close_date) d FROM positions WHERE status='closed' AND close_date < ?", todayIso);
    if (!prev || !prev.d) return false;
    const rows = this.all("SELECT id FROM positions WHERE status='closed' AND close_date=?", prev.d);
    return rows.some((r) => { const x = this.realized(r.id); return x.pct !== null && x.pct >= 100; });
  }

  activePlan(ticker, todayIso) {
    return this.one("SELECT * FROM plans WHERE trade_date=? AND ticker=? ORDER BY id DESC LIMIT 1", todayIso, ticker);
  }

  // ---- Discord REST (used only in live mode) ----
  async post(channel, content) {
    const r = await fetch(`https://discord.com/api/v10/channels/${channel}/messages`, {
      method: "POST",
      headers: { authorization: `Bot ${this.env.DISCORD_BOT_TOKEN}`, "content-type": "application/json" },
      body: JSON.stringify({ content: content.slice(0, 1990), allowed_mentions: { parse: [] } }),
      signal: AbortSignal.timeout(2200),
    });
    if (!r.ok) throw new Error(`Discord said ${r.status} when posting. Check the bot can see and post in that channel.`);
    return (await r.json()).id;
  }

  async unpost(channel, id) {
    if (!channel || !id) return;
    await fetch(`https://discord.com/api/v10/channels/${channel}/messages/${id}`, {
      method: "DELETE", headers: { authorization: `Bot ${this.env.DISCORD_BOT_TOKEN}` },
    }).catch(() => {});
  }

  targetChannel(route) {
    if (route === "free") return this.env.FREE_CHANNEL_ID || null;
    return this.env.VIP_CHANNEL_ID;
  }

  // Publish an alert. Test mode: the alert is shown only in the private channel (the reply).
  // Live mode: it is posted to VIP (or free), and the private reply is a receipt.
  async publish(route, alert, privateExtras) {
    const extras = privateExtras.filter(Boolean).join("\n");
    if (this.mode() !== "live") {
      return { reply: `${alert}\n\n🧪 **TEST MODE**: nobody else sees this.${extras ? "\n" + extras : ""}`, ch: null, id: null };
    }
    const ch = this.targetChannel(route);
    if (!ch) return { reply: `⚠️ Free channel isn't set up yet, so nothing was posted.\n\n${alert}${extras ? "\n" + extras : ""}`, ch: null, id: null };
    const where = route === "free" ? "FREE" : "VIP";
    try {
      const id = await this.post(ch, alert);
      return { reply: `✅ Posted to ${where}.${extras ? "\n" + extras : ""}`, ch, id };
    } catch (err) {
      return { reply: `⚠️ **Logged, but posting to ${where} failed:** ${String(err.message || err).slice(0, 200)}\nCopy it in by hand:\n\n${alert}${extras ? "\n" + extras : ""}`, ch: null, id: null };
    }
  }

  // ---- command router ----
  async handle(text, now) {
    const c = parseCommand(text, now);
    const e = etParts(now);
    const today = e.date;
    switch (c.cmd) {
      case "error": return { reply: `⚠️ ${c.msg}\nNothing was logged.` };
      case "help": return { reply: HELP };
      case "in": return this.cmdIn(c, now, today, e);
      case "trim": return this.cmdExit(c, now, today, true);
      case "out": return this.cmdExit(c, now, today, false);
      case "plan": return this.cmdPlan(c, now);
      case "recap": return { reply: this.recap(today) };
      case "open": return { reply: this.openList() };
      case "paper": {
        const v = c.value === null ? !this.paper() : c.value;
        this.setSetting("paper", v ? "1" : "0");
        return { reply: v ? "📄 **PAPER MODE ON.** Every alert is labeled PAPER until you turn it off with `/t paper off`." : "💵 Paper mode off. Alerts are real again." };
      }
      case "live":
        this.setSetting("mode", "live");
        return { reply: "🟢 **LIVE.** Alerts now post to VIP. Go back to private-only with `/t test`." };
      case "test":
        this.setSetting("mode", "test");
        return { reply: "🧪 **TEST MODE.** Alerts only show here. Switch with `/t live`." };
      case "note": {
        const p = this.one("SELECT * FROM positions ORDER BY id DESC LIMIT 1");
        if (!p) return { reply: "⚠️ No trade to attach a note to yet." };
        const n = p.note ? `${p.note} / ${c.text}` : c.text;
        this.sql.exec("UPDATE positions SET note=? WHERE id=?", n, p.id);
        return { reply: `📝 Note saved on #${p.id} ${contractLabel(p)}: ${c.text}` };
      }
      case "undo": return this.cmdUndo();
      case "log": return this.cmdLog();
      default: return { reply: HELP };
    }
  }

  async cmdIn(c, now, today, e) {
    const paper = this.paper();
    const dte = daysBetween(today, c.exp);
    const flags = [];
    if (dte < 0) return { reply: "⚠️ That expiration is in the past. Nothing was logged." };
    if (dte === 0) flags.push("⚠️ **0DTE.** Standalone 0DTE breaks your rules.");
    else if (dte < 7) flags.push(`⚠️ Expires in ${dte} day${dte === 1 ? "" : "s"}. Your rule is a week or more out.`);
    if (c.price * 100 > 500) flags.push(`⚠️ **Contract over $500** (${money(c.price * 100)} each).`);
    const plan = this.activePlan(c.ticker, today);
    if (!plan) flags.push("⚠️ **Not in last night's plan.** At 9:30 the only allowed action is the planned order.");
    const mins = e.hour * 60 + e.minute;
    if (mins >= 570 && mins < 600 && this.bigWinnerYesterday(today)) {
      flags.push("⚠️ **Open after a big winner.** Your rule is skip the open.");
    }
    const losses = this.lossesOn(today);
    const locked = losses >= 2;

    const res = this.sql.exec(
      `INSERT INTO positions (opened_at, trade_date, ticker, strike, right, exp, entry, qty, open_qty, status,
         paper, route, note, flags, rule_break) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id`,
      now, today, c.ticker, c.strike, c.right, c.exp, c.price, c.qty, c.qty, "open",
      paper ? 1 : 0, c.route, c.note || "", flags.join(" | "), locked ? 1 : 0,
    ).toArray();
    const id = res[0].id;
    this.sql.exec("INSERT INTO fills (position_id, ts, trade_date, side, price, qty) VALUES (?,?,?,?,?,?)",
      id, now, today, "buy", c.price, c.qty);
    const p = this.one("SELECT * FROM positions WHERE id=?", id);

    if (locked) {
      return {
        reply: `🔒 **LOCKED: 2 losses today. Done for the day.**\nLogged #${id} ${contractLabel(p)} as a **rule break**. Not posted to anyone.` +
          (flags.length ? "\n" + flags.join("\n") : ""),
      };
    }

    const isCall = c.right === "C";
    const lines = [];
    if (paper) lines.push("📄📄 **PAPER ALERT** 📄📄");
    if (c.route === "free") lines.push("🆓 **FREE ALERT** 🆓");
    lines.push(`🚨🌪️ **ENTRY** 🌪️🚨`);
    lines.push(`${isCall ? "🟢" : "🔴"} **${contractLabel(p)}** ${isCall ? "📈" : "📉"}`);
    lines.push(`💵 In at **${fmtPx(c.price)}**${c.qty > 1 ? ` x${c.qty}` : ""}`);
    lines.push(`🎯 Half at 2x: **${fmtPx(c.price * 2)}**`);
    if (plan && plan.stop) lines.push(`🛑 Stop: **${plan.stop}**`);
    if (c.note) lines.push(`📝 ${c.note}`);
    lines.push(`⏰ ${fmtTime(now)}`);
    lines.push("", NFA, SIGN_OFF);
    const alert = lines.join("\n");

    const extras = [
      `📒 Logged #${id}. Cost ${money(c.price * 100 * c.qty)} from your price.`,
      plan ? `🗺️ Plan on file: ${plan.text}` : null,
      ...flags,
    ];
    const pub = await this.publish(c.route, alert, extras);
    if (pub.id) this.sql.exec("UPDATE positions SET msg_channel=?, msg_id=? WHERE id=?", pub.ch, pub.id, id);
    return { reply: pub.reply };
  }

  async cmdExit(c, now, today, isTrim) {
    let p;
    if (c.ticker) p = this.one("SELECT * FROM positions WHERE status='open' AND ticker=? ORDER BY id DESC LIMIT 1", c.ticker);
    else p = this.one("SELECT * FROM positions WHERE status='open' ORDER BY id DESC LIMIT 1");
    if (!p) return { reply: `⚠️ No open ${c.ticker ? c.ticker + " " : ""}trade to ${isTrim ? "trim" : "close"}. Check \`/t open\`.` };

    let sellQty, flags = [], forcedFull = false;
    if (isTrim) {
      sellQty = c.qty || Math.floor(p.open_qty / 2);
      if (sellQty < 1) { sellQty = p.open_qty; forcedFull = true; }
    } else {
      sellQty = c.qty || p.open_qty;
    }
    if (sellQty > p.open_qty) return { reply: `⚠️ You only have ${p.open_qty} open on #${p.id}. Nothing was logged.` };

    const gain = pct(c.price, p.entry);
    if (isTrim && !forcedFull && c.price > p.entry && c.price < p.entry * 2) {
      flags.push(`⚠️ Trimmed at ${fmtPct(gain)}. Your rule is half at 2x (${fmtPx(p.entry * 2)}). Cutting winners early is a known leak.`);
    }
    if (forcedFull) flags.push("ℹ️ Only 1 contract, so this was logged as a full exit.");

    const left = p.open_qty - sellQty;
    const closing = left === 0;
    this.sql.exec("INSERT INTO fills (position_id, ts, trade_date, side, price, qty, note) VALUES (?,?,?,?,?,?,?)",
      p.id, now, today, "sell", c.price, sellQty, c.note || "");
    const fillId = this.one("SELECT MAX(id) id FROM fills").id;
    this.sql.exec("UPDATE positions SET open_qty=?, status=?, closed_at=?, close_date=? WHERE id=?",
      left, closing ? "closed" : "open", closing ? now : null, closing ? today : null, p.id);
    if (c.note) this.sql.exec("UPDATE positions SET note=? WHERE id=?", p.note ? `${p.note} / ${c.note}` : c.note, p.id);

    const r = this.realized(p.id);
    const lines = [];
    if (p.paper) lines.push("📄📄 **PAPER ALERT** 📄📄");
    if (p.route === "free") lines.push("🆓 **FREE ALERT** 🆓");
    const win = gain >= 0;
    if (!closing) {
      lines.push(`💰💰 **SOLD ${sellQty === Math.floor(p.open_qty / 2) ? "HALF" : sellQty}** 💰💰`);
    } else {
      lines.push(win ? "✅🔥 **CLOSED** 🔥✅" : "❌ **CLOSED** ❌");
    }
    lines.push(`${p.right === "C" ? "🟢" : "🔴"} **${contractLabel(p)}**`);
    lines.push(`💵 ${fmtPx(p.entry)} ➡️ **${fmtPx(c.price)}** (${fmtPct(gain)}) ${win ? (gain >= 100 ? "🔥🔥🔥" : "🔥") : "🩸"}`);
    if (!closing) lines.push(`🏃 ${left} runner${left === 1 ? "" : "s"} left`);
    if (c.note) lines.push(`📝 ${c.note}`);
    lines.push(`⏰ ${fmtTime(now)}`);
    lines.push("", SIGN_OFF);
    const alert = lines.join("\n");

    const extras = [
      `📒 Logged on #${p.id}.${closing ? ` Trade result from your prices: **${money(r.dollars)}** (${fmtPct(r.pct)} avg).` : ""}`,
      ...flags,
    ];
    if (closing && r.dollars < 0) {
      const losses = this.lossesOn(today);
      if (losses >= 2) extras.push("🔒 **That's 2 losses. Done for the day.** New entries are locked until tomorrow.");
      else extras.push(`Loss ${losses} of 2 today.`);
    }
    // A rule-break trade (taken while locked) is never published.
    if (p.rule_break) return { reply: `🔒 Logged exit on rule-break trade #${p.id}. Not posted.\n${extras.join("\n")}` };
    const pub = await this.publish(p.route, alert, extras);
    if (pub.id) this.sql.exec("UPDATE fills SET msg_channel=?, msg_id=? WHERE id=?", pub.ch, pub.id, fillId);
    return { reply: pub.reply };
  }

  async cmdPlan(c, now) {
    const td = planTradeDate(now);
    this.sql.exec("INSERT INTO plans (created_at, trade_date, ticker, text, stop) VALUES (?,?,?,?,?)",
      now, td, c.ticker, c.text, c.stop);
    const pid = this.one("SELECT MAX(id) id FROM plans").id;
    const today = etParts(now).date;
    const [, m, d] = td.split("-");
    const lines = [
      `🗺️🌪️ **${td === today ? "TODAY'S" : "TOMORROW'S"} SETUP** (${+m}/${+d}) 🌪️🗺️`,
      `🎯 **${c.ticker}**`,
      `📌 ${c.text}`,
      "⏰ At 9:30 the only move is placing this order. No trigger = no trade.",
      "", NFA, SIGN_OFF,
    ];
    const pub = await this.publish(c.route, lines.join("\n"), [`📒 Plan #${pid} saved for ${td}.`]);
    if (pub.id) this.sql.exec("UPDATE plans SET msg_channel=?, msg_id=? WHERE id=?", pub.ch, pub.id, pid);
    return { reply: pub.reply };
  }

  async cmdUndo() {
    const lastPos = this.one("SELECT id, opened_at FROM positions ORDER BY id DESC LIMIT 1");
    const lastSell = this.one("SELECT * FROM fills WHERE side='sell' ORDER BY id DESC LIMIT 1");
    const lastPlan = this.one("SELECT * FROM plans ORDER BY id DESC LIMIT 1");
    const cands = [];
    if (lastPos) cands.push({ kind: "pos", ts: lastPos.opened_at, id: lastPos.id });
    if (lastSell) cands.push({ kind: "sell", ts: lastSell.ts, id: lastSell.id });
    if (lastPlan) cands.push({ kind: "plan", ts: lastPlan.created_at, id: lastPlan.id });
    if (!cands.length) return { reply: "Nothing to undo." };
    cands.sort((a, b) => b.ts - a.ts || b.id - a.id);
    const t = cands[0];
    if (t.kind === "sell") {
      const f = lastSell;
      const p = this.one("SELECT * FROM positions WHERE id=?", f.position_id);
      this.sql.exec("DELETE FROM fills WHERE id=?", f.id);
      this.sql.exec("UPDATE positions SET open_qty=open_qty+?, status='open', closed_at=NULL, close_date=NULL WHERE id=?", f.qty, p.id);
      await this.unpost(f.msg_channel, f.msg_id);
      return { reply: `↩️ Undid the sell of ${f.qty} at ${fmtPx(f.price)} on #${p.id} ${contractLabel(p)}.${f.msg_id ? " Deleted the post too." : ""}` };
    }
    if (t.kind === "plan") {
      this.sql.exec("DELETE FROM plans WHERE id=?", lastPlan.id);
      await this.unpost(lastPlan.msg_channel, lastPlan.msg_id);
      return { reply: `↩️ Undid plan #${lastPlan.id} (${lastPlan.ticker}).${lastPlan.msg_id ? " Deleted the post too." : ""}` };
    }
    const p = this.one("SELECT * FROM positions WHERE id=?", t.id);
    this.sql.exec("DELETE FROM fills WHERE position_id=?", p.id);
    this.sql.exec("DELETE FROM positions WHERE id=?", p.id);
    await this.unpost(p.msg_channel, p.msg_id);
    return { reply: `↩️ Undid entry #${p.id} ${contractLabel(p)}.${p.msg_id ? " Deleted the post too." : ""}` };
  }

  openList() {
    const rows = this.all("SELECT * FROM positions WHERE status='open' ORDER BY id");
    if (!rows.length) return "No open trades.";
    return "📂 **Open trades**\n" + rows.map((p) =>
      `#${p.id} ${contractLabel(p)} in ${fmtPx(p.entry)} | ${p.open_qty} of ${p.qty} left${p.paper ? " | PAPER" : ""}`).join("\n");
  }

  recap(today) {
    const rows = this.all("SELECT * FROM positions WHERE trade_date=? OR close_date=? ORDER BY id", today, today);
    if (!rows.length) return `📊 **Recap ${today}**\nNo trades logged today.`;
    let total = 0;
    const lines = [`📊 **Recap ${today}**`];
    for (const p of rows) {
      const r = this.realized(p.id);
      const res = p.status === "closed" ? `${money(r.dollars)} (${fmtPct(r.pct)})` : r.soldQty ? `open, ${money(r.dollars)} banked so far` : "open";
      if (p.status === "closed" && !p.paper) total += r.dollars;
      lines.push(`${p.rule_break ? "🔒" : p.status === "closed" ? (r.dollars >= 0 ? "✅" : "❌") : "⏳"} #${p.id} ${contractLabel(p)} in ${fmtPx(p.entry)} x${p.qty} | ${res}${p.paper ? " | PAPER" : ""}`);
      if (p.flags) lines.push(`   ${p.flags}`);
      if (p.note) lines.push(`   📝 ${p.note}`);
    }
    lines.push(`\nLosses today: ${this.lossesOn(today)} of 2`);
    lines.push(`Closed real trades, from your prices: **${money(total)}**`);
    return lines.join("\n");
  }

  cmdLog() {
    const rows = this.all("SELECT * FROM positions ORDER BY id");
    const head = ["id", "date", "time_et", "ticker", "strike", "type", "exp", "entry", "qty", "status",
      "avg_exit", "result_usd", "result_pct", "paper", "route", "rule_break", "flags", "note"];
    const esc = (v) => { const s = v === null || v === undefined ? "" : String(v).replace(/\*\*/g, ""); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const lines = [head.join(",")];
    for (const p of rows) {
      const r = this.realized(p.id);
      lines.push([p.id, p.trade_date, fmtTime(p.opened_at), p.ticker, p.strike, p.right === "C" ? "call" : "put", p.exp,
        p.entry, p.qty, p.status, r.avgExit === null ? "" : r.avgExit.toFixed(2), r.soldQty ? r.dollars.toFixed(2) : "",
        r.pct === null ? "" : r.pct.toFixed(1), p.paper ? "yes" : "no", p.route, p.rule_break ? "yes" : "no", p.flags, p.note].map(esc).join(","));
    }
    lines.push("");
    lines.push("fills");
    lines.push("fill_id,trade_id,date,time_et,side,price,qty");
    for (const f of this.all("SELECT * FROM fills ORDER BY id")) {
      lines.push([f.id, f.position_id, f.trade_date, fmtTime(f.ts), f.side, f.price, f.qty].map(esc).join(","));
    }
    const today = new Date().toISOString().slice(0, 10);
    return { reply: `📒 Full trade log: ${rows.length} trade${rows.length === 1 ? "" : "s"}. Results come from the prices you typed.`, file: { name: `taz_trades_${today}.csv`, content: lines.join("\n") } };
  }
}

const HELP = [
  "🌪️ **Trade bot commands** (type them after `/t`)",
  "`in qqq 717p 10/23 .45 x2`  entry (add `| your read` to save a note)",
  "`half .90`  sell half of the latest open trade",
  "`out .70`  close the rest (`out qqq .70` if more than one is open)",
  "`plan qqq puts 727-733 rejection stop 733`  tomorrow's setup",
  "`note 1h 10 SMA close target`  add your read to the latest trade",
  "`open`  open trades   `recap`  today   `log`  spreadsheet file",
  "`undo`  remove the last thing you logged (and its post)",
  "`paper` / `paper off`  label everything PAPER",
  "`live` / `test`  post to VIP, or only show here",
  "`free in ...`  send that alert to the free channel",
].join("\n");
