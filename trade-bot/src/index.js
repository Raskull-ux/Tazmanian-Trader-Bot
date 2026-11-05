// Tazmanian trade bot: type a trade line in the private channel (no slash needed)
// -> clean alert + trade log + rule checks. /t still works as a backup.
// Runs free on Cloudflare Workers. State lives in one SQLite-backed Durable Object.
// It NEVER places orders. Robinhood has no official API; this only posts and logs.

import { DurableObject } from "cloudflare:workers";
import { fetchMeter, getBars } from "./meter.js";
import { fetchGrade } from "./grade.js";
import {
  parseCommand, parseFragment, mergeEntry, matchExit, looksLikeTrade, hasCommandWord, etParts, fmtTime, planTradeDate, daysBetween,
  pct, fmtPct, money, contractLabel, fmtPx, fmtDate, tradeLine,
} from "./parse.js";

const SIGN_OFF = "Pattern. Process. Paid. 🌪️🔴";
const NFA = "_My position, not advice. Education and entertainment only._";
const IDEA = "_💡 Idea, not a position I'm in. Not advice. Education and entertainment only._";
const PLAN = "_My plan, not a position yet. Not advice. Education and entertainment only._";

// ---------------- Worker entry ----------------
export default {
  // Every minute: make sure the channel watcher is running.
  async scheduled(event, env, ctx) {
    const stub = env.STORE.get(env.STORE.idFromName("taz"));
    ctx.waitUntil(stub.ensureAlarm());
    ctx.waitUntil(stub.maTag().catch(() => {}));
  },

  async fetch(request, env) {
    if (request.method === "GET") {
      const u = new URL(request.url);
      if (u.pathname === "/kick") {
        const r = await env.STORE.get(env.STORE.idFromName("taz")).ensureAlarm();
        return new Response(r);
      }
      if (u.pathname === "/status") {
        const r = await env.STORE.get(env.STORE.idFromName("taz")).status();
        return new Response(JSON.stringify(r, null, 1), { headers: { "content-type": "application/json" } });
      }
      return new Response("Tazmanian trade bot is up.");
    }
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
        out = await store.handle(text, Date.now(), { meterTimeout: 1800 });
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
    for (const col of ["grade TEXT", "spread_type TEXT", "long_strike TEXT", "short_strike TEXT"]) {
      try { this.sql.exec(`ALTER TABLE positions ADD COLUMN ${col}`); } catch (_) { /* already there */ }
    }
  }


  // ---------------- channel watcher (no-slash mode) ----------------
  api(method, path, body) {
    const base = this.env.DISCORD_API || "https://discord.com/api/v10";
    const headers = { authorization: `Bot ${this.env.DISCORD_BOT_TOKEN}` };
    if (body !== undefined) headers["content-type"] = "application/json";
    return fetch(base + path, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(4000),
    });
  }

  // Fast checks while you trade, slower when you don't.
  interval(now) {
    const e = etParts(now);
    const wd = new Date(e.date + "T12:00:00Z").getUTCDay();
    if (wd === 0 || wd === 6) return 60000;
    const m = e.hour * 60 + e.minute;
    if (m >= 8 * 60 && m < 16 * 60 + 30) return 5000;
    if (m >= 7 * 60 && m < 21 * 60) return 15000;
    return 60000;
  }

  async status() {
    const a = await this.ctx.storage.getAlarm();
    const g = (k) => this.getSetting(k, null);
    const ok = g("last_poll_ok");
    return {
      mode: this.mode(), paper: this.paper(), next_check: a ? new Date(a).toISOString() : null,
      last_ok: ok ? new Date(+ok).toISOString() : null, last_error: g("last_poll_error"),
      trades: this.one("SELECT COUNT(*) n FROM positions").n,
    };
  }

  // ---- QQQ 8-day EMA / SMA tag alert (every minute, 9:30-4:00 ET weekdays) ----
  async maTag(now = Date.now()) {
    const e = etParts(now);
    const mins = e.hour * 60 + e.minute;
    if (["Sat", "Sun"].includes(e.weekday) || mins < 570 || mins >= 960) return "closed";
    const day = e.date;
    let base = null;
    try { base = JSON.parse(this.getSetting("ma8_base", "null")); } catch (_) {}
    if (!base || base.day !== day) {
      const start = new Date(now - 40 * 86400000).toISOString();
      const bars = await getBars(this.env, "QQQ", { timeframe: "1Day", start, end: new Date(now - 16 * 60000).toISOString(), feed: "sip", adjustment: "raw" });
      const done = bars.filter((b) => etParts(Date.parse(b.t)).date < day).map((b) => b.c);
      if (done.length < 20) return "no bars";
      let ema = done[0];
      for (let i = 1; i < done.length; i++) ema += (2 / 9) * (done[i] - ema);
      base = { day, ema, last7: done.slice(-7) };
      this.setSetting("ma8_base", JSON.stringify(base));
    }
    const r = await fetch("https://data.alpaca.markets/v2/stocks/QQQ/trades/latest?feed=iex", {
      headers: { "APCA-API-KEY-ID": this.env.ALPACA_KEY_ID, "APCA-API-SECRET-KEY": this.env.ALPACA_SECRET },
      signal: AbortSignal.timeout(4000),
    });
    if (!r.ok) return `quote ${r.status}`;
    const p = (await r.json())?.trade?.p;
    if (!p) return "no price";
    const lines = {
      "8 EMA": base.ema + (2 / 9) * (p - base.ema),
      "8 SMA": (base.last7.reduce((a, b) => a + b, 0) + p) / 8,
    };
    let st = {};
    try { st = JSON.parse(this.getSetting("ma8_state", "{}")); } catch (_) {}
    if (st.day !== day) st = { day };
    const out = [];
    for (const [name, v] of Object.entries(lines)) {
      const side = p >= v ? "above" : "below";
      const dist = Math.abs(p - v) / v;
      const s = st[name] || { side, armed: true };
      const crossed = s.side && s.side !== side;
      if (s.armed && (dist <= 0.0005 || crossed)) {
        const other = Object.entries(lines).filter(([k]) => k !== name).map(([k, w]) => `${k} ${w.toFixed(2)}`).join(" · ");
        const how = crossed ? (side === "above" ? "crossed UP through" : "crossed DOWN through") : `tagged (from ${side === "above" ? "above" : "below"})`;
        out.push(`🎯 **QQQ ${how} the daily ${name}** at **${v.toFixed(2)}** · price ${p.toFixed(2)} · ${other} · ${fmtTime(now)}\n${IDEA}`);
        s.armed = false;
      }
      if (dist >= 0.001) s.armed = true;
      s.side = side;
      st[name] = s;
    }
    this.setSetting("ma8_state", JSON.stringify(st));
    if (out.length) await this.api("POST", `/channels/${this.env.PRIVATE_CHANNEL_ID}/messages`, { content: out.join("\n"), allowed_mentions: { parse: [] } });
    return out.length ? out.join("\n") : `ok ${p}`;
  }

  async ensureAlarm() {
    const a = await this.ctx.storage.getAlarm();
    if (a === null || a < Date.now() - 30000) {
      await this.ctx.storage.setAlarm(Date.now() + 1000);
      return "watcher started";
    }
    return "watcher running";
  }

  async alarm() {
    try {
      await this.poll();
      this.setSetting("last_poll_ok", String(Date.now()));
    } catch (e) {
      this.setSetting("last_poll_error", `${new Date().toISOString()} ${String(e && e.message || e).slice(0, 300)}`);
    } finally {
      await this.ctx.storage.setAlarm(Date.now() + this.interval(Date.now()));
    }
  }

  async poll() {
    const ch = this.env.PRIVATE_CHANNEL_ID;
    const last = this.getSetting("last_msg_id", "");
    if (!last) {
      // First run: start from now. Old chat history is never replayed.
      const r = await this.api("GET", `/channels/${ch}/messages?limit=1`);
      if (!r.ok) throw new Error(`read channel: HTTP ${r.status}`);
      const arr = await r.json();
      this.setSetting("last_msg_id", arr.length ? arr[0].id : "0");
      return;
    }
    const r = await this.api("GET", `/channels/${ch}/messages?after=${last}&limit=50`);
    if (r.status === 429) return;
    if (!r.ok) throw new Error(`read channel: HTTP ${r.status}`);
    const msgs = (await r.json()).sort((a, b) => (BigInt(a.id) < BigInt(b.id) ? -1 : 1));
    for (const m of msgs) {
      this.setSetting("last_msg_id", m.id); // mark first: a crash never double-logs a trade
      if (!m.author || m.author.bot) continue;
      await this.onMessage(m);
    }
    await this.cleanupAsk(Date.now()).catch(() => {});
  }

  // One-time: the old parser left positions #2, #3, #7, #8 stuck open. List them in the private channel
  // and remove them only after a "y". Asked again at most every 6 hours until answered.
  async cleanupAsk(now, force = false) {
    const st = this.getSetting("cleanup_v1", "");
    if (st === "done" && !force) return null;
    const rows = this.all("SELECT * FROM positions WHERE id IN (2,3,7,8) AND status='open' ORDER BY id");
    if (!rows.length) { this.setSetting("cleanup_v1", "done"); return force ? "No stuck positions from the old bug are open." : null; }
    const last = +this.getSetting("cleanup_v1_asked", "0");
    const pend = this.getPending(now);
    if (!force && (now - last < 6 * 3600000 || (pend && pend.kind !== "cleanup"))) return null;
    const text = ["🧹 **Stuck open positions from the old parser bug**",
      ...rows.map((p) => `#${p.id} ${contractLabel(p)} in ${fmtPx(p.entry)} x${p.open_qty} open (logged ${p.trade_date})`),
      "", "Reply **y** to remove these from the log (only these, nothing else is touched), or **n** to keep them."].join("\n");
    this.setPending({ kind: "cleanup", ids: rows.map((r) => r.id) }, now);
    this.setSetting("cleanup_v1_asked", String(now));
    if (force) return text;
    await this.api("POST", `/channels/${this.env.PRIVATE_CHANNEL_ID}/messages`, { content: text, allowed_mentions: { parse: [] } });
    return text;
  }

  async onMessage(m) {
    const text = (m.content || "").trim();
    const pend = this.getPending(Date.now());
    if (!text || !looksLikeTrade(text, pend ? pend.kind : false)) return;
    let out;
    try {
      out = await this.handle(text, Date.now());
    } catch (e) {
      out = { reply: `⚠️ Bot error, nothing was logged: ${String(e && e.message || e).slice(0, 300)}` };
    }
    // Plain chat that only looked like a command (no numbers, didn't parse) stays ignored.
    if (out.silent) return;
    const failed = out.reply.startsWith("⚠️") && out.reply.includes("Nothing was logged");
    if (failed && !/\d/.test(text) && text.trim().split(/\s+/).length > 1) return;
    await this.replyTo(m, out);
    const emoji = failed ? "⚠️" : out.ask ? "❓" : out.reply.startsWith("🔒") ? "🔒" : "✅";
    await this.api("PUT", `/channels/${m.channel_id}/messages/${m.id}/reactions/${encodeURIComponent(emoji)}/@me`).catch(() => {});
  }

  async replyTo(m, out) {
    const ref = { message_id: m.id, fail_if_not_exists: false };
    const base = this.env.DISCORD_API || "https://discord.com/api/v10";
    if (out.file) {
      const form = new FormData();
      form.append("payload_json", JSON.stringify({
        content: out.reply.slice(0, 1990), message_reference: ref, allowed_mentions: { parse: [] },
        attachments: [{ id: 0, filename: out.file.name }],
      }));
      form.append("files[0]", new Blob([out.file.content], { type: "text/csv" }), out.file.name);
      await fetch(`${base}/channels/${m.channel_id}/messages`, {
        method: "POST", headers: { authorization: `Bot ${this.env.DISCORD_BOT_TOKEN}` }, body: form,
      });
      return;
    }
    // Split long replies so nothing gets cut off.
    const chunks = [];
    let rest = out.reply;
    while (rest.length > 1900) {
      let cut = rest.lastIndexOf("\n", 1900);
      if (cut < 500) cut = 1900;
      chunks.push(rest.slice(0, cut));
      rest = rest.slice(cut).replace(/^\n/, "");
    }
    chunks.push(rest);
    for (let k = 0; k < chunks.length; k++) {
      await this.api("POST", `/channels/${m.channel_id}/messages`, {
        content: chunks[k], allowed_mentions: { parse: [] }, ...(k === 0 ? { message_reference: ref } : {}),
      });
    }
  }

  // ---- small db helpers ----
  all(q, ...a) { return this.sql.exec(q, ...a).toArray(); }
  one(q, ...a) { const r = this.all(q, ...a); return r.length ? r[0] : null; }
  getSetting(k, d) { const r = this.one("SELECT v FROM settings WHERE k=?", k); return r ? r.v : d; }
  setSetting(k, v) { this.sql.exec("INSERT INTO settings(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", k, String(v)); }
  mode() { return this.getSetting("mode", "test"); }
  getPending(now) {
    try {
      const p = JSON.parse(this.getSetting("pending", "null"));
      if (!p) return null;
      if (p.kind !== "cleanup" && now - p.ts > 30 * 60000) return null; // a question goes stale after 30 minutes
      return p;
    } catch (_) { return null; }
  }
  setPending(obj, now) { this.setSetting("pending", JSON.stringify({ ...obj, ts: now })); }
  clearPending() { this.setSetting("pending", "null"); }
  lastTicker() { const r = this.one("SELECT ticker FROM positions ORDER BY id DESC LIMIT 1"); return r ? r.ticker : null; }
  paper() { return this.getSetting("paper", "0") === "1"; }

  realized(posId) {
    const p = this.one("SELECT * FROM positions WHERE id=?", posId);
    const sells = this.all("SELECT price, qty FROM fills WHERE position_id=? AND side='sell'", posId);
    let dollars = 0, q = 0, wsum = 0;
    const credit = p.spread_type === "credit";
    for (const s of sells) { dollars += (credit ? p.entry - s.price : s.price - p.entry) * 100 * s.qty; q += s.qty; wsum += s.price * s.qty; }
    const avgExit = q ? wsum / q : null;
    return { dollars, soldQty: q, avgExit, pct: avgExit ? (credit ? (p.entry - avgExit) / p.entry * 100 : pct(avgExit, p.entry)) : null };
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
    const r = await this.api("POST", `/channels/${channel}/messages`,
      { content: content.slice(0, 1990), allowed_mentions: { parse: [] } });
    if (!r.ok) throw new Error(`Discord said ${r.status} when posting. Check the bot can see and post in that channel.`);
    return (await r.json()).id;
  }

  async unpost(channel, id) {
    if (!channel || !id) return;
    await this.api("DELETE", `/channels/${channel}/messages/${id}`).catch(() => {});
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

  async grade(ticker, side) {
    try {
      const t = new Promise((res) => setTimeout(() => res(null), this.meterTimeout || 9000));
      return await Promise.race([fetchGrade(this.env, ticker.split("/")[0], side), t]);
    } catch (_) { return null; }
  }

  async meter(ticker, side) {
    try {
      const t = new Promise((res) => setTimeout(() => res(null), this.meterTimeout || 9000));
      return await Promise.race([fetchMeter(this.env, ticker.split("/")[0], side), t]);
    } catch (_) { return null; }
  }

  // ---- command router ----
  async handle(text, now, opts = {}) {
    this.meterTimeout = opts.meterTimeout || 9000;
    const pend = this.getPending(now);
    const c = parseCommand(text, now, { lastTicker: this.lastTicker() });
    const e = etParts(now);
    const today = e.date;

    // A question is waiting: y / n / a number / the missing piece.
    if (pend) {
      if (c.cmd === "yes") return this.resolvePending(pend, { yes: true }, now, today, e);
      if (c.cmd === "no") {
        this.clearPending();
        if (pend.kind === "cleanup") { this.setSetting("cleanup_v1", "done"); return { reply: "👍 Kept them. Nothing was removed." }; }
        return { reply: "👍 Cancelled. Nothing was logged." };
      }
      if (c.cmd === "pick" && (pend.kind === "choose" || pend.kind === "cleanup")) return this.resolvePending(pend, { pick: c.n }, now, today, e);
      const fresh = ["in", "out", "trim"].includes(c.cmd) && (hasCommandWord(text) || (!(c.missing || []).length && !(c.guesses || []).length));
      const other = !["in", "out", "trim", "error", "pick", "yes", "no"].includes(c.cmd);
      if (!fresh && !other && (pend.kind === "entry" || pend.kind === "exitPrice")) {
        const frag = parseFragment(text, now);
        if (c.cmd === "pick") frag.price = c.n; // "1" while waiting on a price = 1.00
        if (Object.keys(frag).length) return this.resolvePending(pend, { frag }, now, today, e);
        if (c.cmd === "error") return { reply: "", silent: true };
      }
      if (fresh || other) { if (pend.kind !== "cleanup") this.clearPending(); }
    }

    switch (c.cmd) {
      case "error": return { reply: `⚠️ ${c.msg}\nNothing was logged.` };
      case "yes": case "no": case "pick": return { reply: "Nothing is waiting on an answer right now.", silent: true };
      case "help": return { reply: HELP };
      case "in": return this.cmdIn(c, now, today, e);
      case "trim": return this.cmdExit(c, now, today, true);
      case "out": return this.cmdExit(c, now, today, false);
      case "fix": return this.cmdFix(c, now);
      case "delete": return this.cmdDelete(c.id);
      case "plan": return this.cmdPlan(c, now);
      case "recap": return { reply: this.recap(today) };
      case "grade": {
        const g = await this.grade(c.ticker, c.side);
        return { reply: g ? `${g.text}\n_Nothing logged._` : `⚠️ Couldn't get ${c.ticker} daily data right now. Nothing logged.` };
      }
      case "check": {
        const m = await this.meter(c.ticker, c.side);
        return { reply: m ? `🔎 **${c.ticker}** ${c.side === "C" ? "calls" : "puts"} @ ${m.px.toFixed(2)}\n${m.text}\n_Nothing logged._` : `⚠️ Couldn't get ${c.ticker} data right now. Nothing logged.` };
      }
      case "open": return { reply: this.openList() };
      case "cleanup": { const t = await this.cleanupAsk(now, true); return { reply: t, ask: true }; }
      case "paper": {
        const v = c.value === null ? !this.paper() : c.value;
        this.setSetting("paper", v ? "1" : "0");
        return { reply: v ? "📄 **PAPER MODE ON.** Every alert is labeled PAPER until you turn it off with `paper off`." : "💵 Paper mode off. Alerts are real again." };
      }
      case "live":
        this.setSetting("mode", "live");
        return { reply: "🟢 **LIVE.** Alerts now post to VIP. Go back to private-only with `test`." };
      case "test":
        this.setSetting("mode", "test");
        return { reply: "🧪 **TEST MODE.** Alerts only show here. Switch with `live`." };
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

  async resolvePending(pend, ans, now, today, e) {
    if (pend.kind === "cleanup") {
      if (!ans.yes) return { reply: "Reply **y** to remove the stuck positions or **n** to keep them." , ask: true };
      const ids = pend.ids.filter((id) => this.one("SELECT id FROM positions WHERE id=? AND status='open'", id));
      for (const id of ids) {
        this.sql.exec("DELETE FROM fills WHERE position_id=?", id);
        this.sql.exec("DELETE FROM positions WHERE id=?", id);
      }
      this.clearPending(); this.setSetting("cleanup_v1", "done");
      return { reply: `🧹 Removed ${ids.map((i) => "#" + i).join(", ") || "nothing (already gone)"} from the log. Old Discord posts were left as they are.` };
    }
    if (pend.kind === "entry") {
      let c = pend.c;
      if (ans.frag) c = mergeEntry(c, ans.frag, pend.asked || []);
      if (ans.yes) c = { ...c, guesses: [] };
      if (c.missing.length || c.guesses.length) return this.askEntry(c, now);
      this.clearPending();
      return this.cmdIn({ ...c, missing: [], guesses: [] }, now, today, e);
    }
    if (pend.kind === "choose") {
      const id = ans.pick ? pend.ids[ans.pick - 1] : pend.ids.length === 1 && ans.yes ? pend.ids[0] : null;
      if (!id) return { reply: `Reply with a number from 1 to ${pend.ids.length}.`, ask: true };
      this.clearPending();
      return this.cmdExit({ ...pend.c, posId: id }, now, today, pend.isTrim);
    }
    if (pend.kind === "exitPrice") {
      const price = ans.frag && ans.frag.price !== undefined ? ans.frag.price : ans.frag && ans.frag.strikeGuess ? +ans.frag.strikeGuess : null;
      if (!(price > 0)) return { reply: "Send the price, like `1.22`.", ask: true };
      this.clearPending();
      return this.cmdExit({ ...pend.c, price, posId: pend.posId }, now, today, pend.isTrim);
    }
    this.clearPending();
    return { reply: "Nothing is waiting on an answer right now." };
  }

  // Never just fail: show the best read and ask for the one missing piece.
  askEntry(c, now) {
    const show = (v, ph) => (v === null || v === undefined || v === "" ? ph : v);
    const label = `${show(c.ticker, "???")} ${show(c.strike, "???")}${c.right || ""} ${c.exp ? fmtDate(c.exp) : "?/?"}` +
      `${c.price !== null && c.price !== undefined ? " @ " + fmtPx(c.price) : ""}${c.qty > 1 ? " x" + c.qty : ""}`;
    const notes = [];
    if (c.guesses.includes("exp")) notes.push(`no expiry, so I used the nearest Friday a week out: **${fmtDate(c.exp)}**`);
    if (c.guesses.includes("right")) notes.push("no put/call, so I read it as a **PUT** (reply `c` if it was a call)");
    if (c.guesses.includes("ticker")) notes.push(`no ticker, so I used your last one: **${c.ticker}**`);
    const need = [];
    if (c.missing.includes("ticker")) need.push("the ticker (like `aapl`)");
    if (c.missing.includes("strike")) need.push("the strike (like `345p`)");
    if (c.missing.includes("price")) need.push("the price (like `.45`)");
    const asked = [...c.missing];
    this.setPending({ kind: "entry", c, asked }, now);
    const lines = [`❓ Got **${label}**${notes.length ? ": " + notes.join("; ") : ""}.`];
    if (need.length) lines.push(`Send ${need.join(" and ")} and I'll log it.${notes.length ? " Or send a fix for anything above." : ""}`);
    else lines.push("Reply **y** to log it, or send the fix (like `11/13`).");
    lines.push("_Nothing logged yet._");
    return { reply: lines.join("\n"), ask: true };
  }

  entryAlert(p, plan, ts) {
    const isCall = p.right === "C";
    const lines = [];
    if (p.paper) lines.push("📄📄 **PAPER IDEA** (not a real position) 📄📄");
    if (p.route === "free") lines.push(`🆓 **FREE ${p.paper ? "IDEA" : "ALERT"}** 🆓`);
    lines.push(p.paper ? `💡🌪️ **IDEA: ENTRY** 🌪️💡` : `🚨🌪️ **ENTRY** 🌪️🚨`);
    lines.push(`${isCall ? "🟢" : "🔴"} **${tradeLine(p, p.entry)}**${p.qty > 1 ? ` x${p.qty}` : ""} ${isCall ? "📈" : "📉"}`);
    if (p.long_strike) {
      const kind = `${isCall ? "call" : "put"} ${p.spread_type || "debit"} spread`;
      lines.push(`🧩 ${kind}: long ${p.long_strike}${p.right} / short ${p.short_strike}${p.right}, net ${p.spread_type === "credit" ? "credit" : "debit"} ${fmtPx(p.entry)}`);
    }
    if (p.spread_type !== "credit") lines.push(`🎯 Half at 2x: **${fmtPx(p.entry * 2)}**`);
    if (plan && plan.stop) lines.push(`🛑 Stop: **${plan.stop}**`);
    if (p.note) lines.push(`📝 ${p.note}`);
    lines.push(`⏰ ${fmtTime(ts)}`);
    lines.push("", p.paper ? IDEA : NFA, SIGN_OFF);
    return lines.join("\n");
  }

  exitAlert(p, f, left, wasHalf) {
    const gain = p.spread_type === "credit" ? (p.entry - f.price) / p.entry * 100 : pct(f.price, p.entry);
    const win = gain >= 0;
    const lines = [];
    if (p.paper) lines.push("📄📄 **PAPER IDEA** (not a real position) 📄📄");
    if (p.route === "free") lines.push(`🆓 **FREE ${p.paper ? "IDEA" : "ALERT"}** 🆓`);
    if (left > 0) lines.push(`💰💰 **SOLD ${wasHalf ? "HALF" : f.qty}** 💰💰`);
    else lines.push(win ? "✅🔥 **CLOSED** 🔥✅" : "❌ **CLOSED** ❌");
    lines.push(`${p.right === "C" ? "🟢" : "🔴"} **${contractLabel(p)}**`);
    lines.push(`💵 ${fmtPx(p.entry)} ➡️ **${fmtPx(f.price)}** (${fmtPct(gain)}) ${win ? (gain >= 100 ? "🔥🔥🔥" : "🔥") : "🩸"}`);
    if (left > 0) lines.push(`🏃 ${left} runner${left === 1 ? "" : "s"} left`);
    if (f.note) lines.push(`📝 ${f.note}`);
    lines.push(`⏰ ${fmtTime(f.ts)}`);
    lines.push("", p.paper ? IDEA : NFA, SIGN_OFF);
    return lines.join("\n");
  }

  async cmdIn(c, now, today, e) {
    if ((c.missing && c.missing.length) || (c.guesses && c.guesses.length)) return this.askEntry(c, now);
    const paper = this.paper();
    const dte = daysBetween(today, c.exp);
    const flags = [];
    if (dte < 0) {
      this.setPending({ kind: "entry", c: { ...c, missing: [], guesses: ["exp"] }, asked: [] }, now);
      return { reply: `❓ Expiry ${fmtDate(c.exp)} is in the past. Send the right date (like \`11/13\`).\n_Nothing logged yet._`, ask: true };
    }
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
         paper, route, note, flags, rule_break, spread_type, long_strike, short_strike) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING id`,
      now, today, c.ticker, c.strike, c.right, c.exp, c.price, c.qty, c.qty, "open",
      paper ? 1 : 0, c.route || "main", c.note || "", flags.join(" | "), locked ? 1 : 0,
      c.spread ? c.spreadType : null, c.spread ? c.long : null, c.spread ? c.short : null,
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
    const alert = this.entryAlert(p, plan, now);
    const [mt, gr] = await Promise.all([this.meter(c.ticker, c.right), this.grade(c.ticker, c.right)]);
    if (gr && gr.g) this.sql.exec("UPDATE positions SET grade=? WHERE id=?", `${gr.g.letter} (${gr.g.score}/6)`, id);
    const extras = [
      `📒 Logged #${id}: ${tradeLine(p, p.entry)}${p.qty > 1 ? " x" + p.qty : ""}. Wrong? \`fix price 1.22\` / \`fix strike 345\` / \`fix exp 11/13\` / \`fix qty 2\` / \`undo\``,
      mt ? mt.text : "⏱️ EARLY meter: no data right now",
      gr ? gr.text : "📊 Grade: no data right now",
      plan ? `🗺️ Plan on file: ${plan.text}` : null,
      ...flags,
    ];
    const pub = await this.publish(p.route, alert, extras);
    if (pub.id) this.sql.exec("UPDATE positions SET msg_channel=?, msg_id=? WHERE id=?", pub.ch, pub.id, id);
    return { reply: pub.reply };
  }

  async cmdExit(c, now, today, isTrim) {
    const rows = this.all("SELECT * FROM positions WHERE status='open' ORDER BY id");
    let p;
    if (c.posId) p = rows.find((r) => r.id === c.posId);
    let qty = c.qty || null;
    if (!p) {
      if (!rows.length) return { reply: "⚠️ No open trades to close. Check `open`.\nNothing was logged." };
      const mt = matchExit(c, rows);
      qty = mt.qty;
      let list = mt.matches;
      const gave = [c.ticker, c.strike, c.right === "C" ? "call" : c.right === "P" ? "put" : null, c.exp ? fmtDate(c.exp) : null, c.spread ? "spread" : null]
        .filter(Boolean).join(" ");
      if (list.length === 1) p = list[0];
      else {
        const none = list.length === 0;
        if (none) list = rows;
        if (none && rows.length === 1 && !c.ticker) p = rows[0];
        else {
          const ids = list.map((r) => r.id);
          this.setPending({ kind: "choose", c: { ...c, qty }, ids, isTrim }, now);
          const head = none ? `❓ No open trade matches **${gave}**. Which one did you mean?` : `❓ ${list.length} open trades match${gave ? " **" + gave + "**" : ""}. Which one?`;
          return { reply: [head, ...list.map((r, k) => `**${k + 1}**) #${r.id} ${contractLabel(r)} in ${fmtPx(r.entry)}, ${r.open_qty} open`),
            `Reply with the number.${c.price === null ? "" : ` Price ${fmtPx(c.price)} is saved.`}`, "_Nothing logged yet._"].join("\n"), ask: true };
        }
      }
    }
    if (c.price === null || c.price === undefined) {
      this.setPending({ kind: "exitPrice", c: { ...c, qty }, posId: p.id, isTrim }, now);
      return { reply: `❓ ${isTrim ? "Trimming" : "Closing"} #${p.id} **${contractLabel(p)}** (in ${fmtPx(p.entry)}). At what price? Send it like \`1.22\`.\n_Nothing logged yet._`, ask: true };
    }

    let sellQty, flags = [], forcedFull = false;
    if (isTrim) {
      sellQty = qty || (c.pct && c.pct !== 50 ? Math.max(1, Math.round(p.open_qty * c.pct / 100)) : Math.floor(p.open_qty / 2));
      if (sellQty < 1) { sellQty = p.open_qty; forcedFull = true; }
    } else {
      sellQty = qty || p.open_qty;
    }
    if (sellQty > p.open_qty) return { reply: `⚠️ You only have ${p.open_qty} open on #${p.id} ${contractLabel(p)}. Nothing was logged.` };

    const credit = p.spread_type === "credit";
    const gain = credit ? (p.entry - c.price) / p.entry * 100 : pct(c.price, p.entry);
    if (isTrim && !forcedFull && !credit && c.price > p.entry && c.price < p.entry * 2) {
      flags.push(`⚠️ Trimmed at ${fmtPct(gain)}. Your rule is half at 2x (${fmtPx(p.entry * 2)}). Cutting winners early is a known leak.`);
    }
    if (forcedFull) flags.push("ℹ️ Only 1 contract, so this was logged as a full exit.");

    const wasHalf = sellQty === Math.floor(p.open_qty / 2);
    const left = p.open_qty - sellQty;
    const closing = left === 0;
    this.sql.exec("INSERT INTO fills (position_id, ts, trade_date, side, price, qty, note) VALUES (?,?,?,?,?,?,?)",
      p.id, now, today, "sell", c.price, sellQty, c.note || "");
    const fillId = this.one("SELECT MAX(id) id FROM fills").id;
    this.sql.exec("UPDATE positions SET open_qty=?, status=?, closed_at=?, close_date=? WHERE id=?",
      left, closing ? "closed" : "open", closing ? now : null, closing ? today : null, p.id);
    if (c.note) this.sql.exec("UPDATE positions SET note=? WHERE id=?", p.note ? `${p.note} / ${c.note}` : c.note, p.id);

    const r = this.realized(p.id);
    const alert = this.exitAlert(p, { price: c.price, qty: sellQty, note: c.note, ts: now }, left, wasHalf);
    const extras = [
      `📒 Logged on #${p.id} ${contractLabel(p)}: sold ${sellQty} at ${fmtPx(c.price)}.${closing ? ` Trade result from your prices: **${money(r.dollars)}** (${fmtPct(r.pct)} avg).` : ""} Wrong? \`fix price 1.25\` / \`undo\``,
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

  // The last thing logged: an entry or a sell, whichever is newer.
  lastAction() {
    const pos = this.one("SELECT * FROM positions ORDER BY opened_at DESC, id DESC LIMIT 1");
    const sell = this.one("SELECT * FROM fills WHERE side='sell' ORDER BY ts DESC, id DESC LIMIT 1");
    if (!pos && !sell) return null;
    if (sell && (!pos || sell.ts > pos.opened_at || (sell.ts === pos.opened_at && sell.position_id === pos.id))) return { kind: "sell", fill: sell };
    return { kind: "entry", pos };
  }

  async editPost(ch, id, content) {
    if (!ch || !id) return false;
    const r = await this.api("PATCH", `/channels/${ch}/messages/${id}`, { content: content.slice(0, 1990) }).catch(() => null);
    return !!(r && r.ok);
  }

  async cmdFix(c, now) {
    const la = this.lastAction();
    if (!la) return { reply: "⚠️ Nothing logged yet to fix." };
    const posId = la.kind === "entry" ? la.pos.id : la.fill.position_id;
    const before = this.one("SELECT * FROM positions WHERE id=?", posId);
    let what = "";
    if (c.field === "price") {
      if (la.kind === "entry") {
        this.sql.exec("UPDATE positions SET entry=? WHERE id=?", c.value, posId);
        this.sql.exec("UPDATE fills SET price=? WHERE position_id=? AND side='buy'", c.value, posId);
        what = `entry price ${fmtPx(before.entry)} ➡️ **${fmtPx(c.value)}**`;
      } else {
        this.sql.exec("UPDATE fills SET price=? WHERE id=?", c.value, la.fill.id);
        what = `sell price ${fmtPx(la.fill.price)} ➡️ **${fmtPx(c.value)}**`;
      }
    } else if (c.field === "qty") {
      if (la.kind === "entry") {
        const sold = before.qty - before.open_qty;
        if (c.value < sold) return { reply: `⚠️ ${sold} already sold on #${posId}, so qty can't be ${c.value}.` };
        this.sql.exec("UPDATE positions SET qty=?, open_qty=?, status=? WHERE id=?", c.value, c.value - sold, c.value - sold > 0 ? "open" : "closed", posId);
        this.sql.exec("UPDATE fills SET qty=? WHERE position_id=? AND side='buy'", c.value, posId);
        what = `qty ${before.qty} ➡️ **${c.value}**`;
      } else {
        const room = before.open_qty + la.fill.qty;
        if (c.value > room) return { reply: `⚠️ Only ${room} were open before that sell.` };
        const left = room - c.value;
        this.sql.exec("UPDATE fills SET qty=? WHERE id=?", c.value, la.fill.id);
        this.sql.exec("UPDATE positions SET open_qty=?, status=?, closed_at=?, close_date=? WHERE id=?", left, left ? "open" : "closed",
          left ? null : la.fill.ts, left ? null : la.fill.trade_date, posId);
        what = `sold qty ${la.fill.qty} ➡️ **${c.value}**`;
      }
    } else if (c.field === "strike") {
      const right = c.right || before.right;
      if (c.spread) this.sql.exec("UPDATE positions SET strike=?, right=?, long_strike=?, short_strike=?, spread_type=COALESCE(spread_type,'debit') WHERE id=?", c.value, right, c.long, c.short, posId);
      else this.sql.exec("UPDATE positions SET strike=?, right=?, long_strike=NULL, short_strike=NULL, spread_type=NULL WHERE id=?", c.value, right, posId);
      what = `strike ${before.strike}${before.right} ➡️ **${c.value}${right}**`;
    } else if (c.field === "exp") {
      this.sql.exec("UPDATE positions SET exp=? WHERE id=?", c.value, posId);
      what = `expiry ${fmtDate(before.exp)} ➡️ **${fmtDate(c.value)}**`;
    } else if (c.field === "right") {
      this.sql.exec("UPDATE positions SET right=? WHERE id=?", c.value, posId);
      what = `${before.right === "C" ? "call" : "put"} ➡️ **${c.value === "C" ? "call" : "put"}**`;
    } else if (c.field === "ticker") {
      this.sql.exec("UPDATE positions SET ticker=? WHERE id=?", c.value, posId);
      what = `ticker ${before.ticker} ➡️ **${c.value}**`;
    }
    // Rewrite the Discord post(s) so the room sees the corrected numbers.
    const p = this.one("SELECT * FROM positions WHERE id=?", posId);
    let edited = 0;
    if (la.kind === "entry" || ["strike", "exp", "right", "ticker"].includes(c.field)) {
      if (await this.editPost(p.msg_channel, p.msg_id, this.entryAlert(p, this.activePlan(p.ticker, p.trade_date), p.opened_at))) edited++;
    }
    if (la.kind === "sell") {
      const f = this.one("SELECT * FROM fills WHERE id=?", la.fill.id);
      const prevOpen = p.open_qty + f.qty;
      if (await this.editPost(f.msg_channel, f.msg_id, this.exitAlert(p, f, p.open_qty, f.qty === Math.floor(prevOpen / 2) && p.open_qty > 0))) edited++;
    }
    const hadPost = p.msg_id || (la.kind === "sell" && la.fill.msg_id);
    return { reply: `✏️ Fixed #${posId} ${contractLabel(p)}: ${what}.${edited ? " Updated the Discord post too." : hadPost ? " ⚠️ Couldn't edit the Discord post, fix it by hand." : ""}` };
  }

  async cmdDelete(id) {
    const p = this.one("SELECT * FROM positions WHERE id=?", id);
    if (!p) return { reply: `⚠️ No trade #${id} in the log. Check \`recap\` or \`log\`.` };
    const fills = this.all("SELECT * FROM fills WHERE position_id=?", id);
    this.sql.exec("DELETE FROM fills WHERE position_id=?", id);
    this.sql.exec("DELETE FROM positions WHERE id=?", id);
    let gone = 0;
    if (p.msg_id) { await this.unpost(p.msg_channel, p.msg_id); gone++; }
    for (const f of fills) if (f.msg_id) { await this.unpost(f.msg_channel, f.msg_id); gone++; }
    return { reply: `🗑️ Deleted trade #${id} ${contractLabel(p)} (${fills.length} fill${fills.length === 1 ? "" : "s"}).${gone ? ` Removed ${gone} Discord post${gone === 1 ? "" : "s"} too.` : ""}` };
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
      "", PLAN, SIGN_OFF,
    ];
    const pub = await this.publish(c.route, lines.join("\n"), [`📒 Plan #${pid} saved for ${td}.`]);
    if (pub.id) this.sql.exec("UPDATE plans SET msg_channel=?, msg_id=? WHERE id=?", pub.ch, pub.id, pid);
    return { reply: pub.reply };
  }

  async cmdUndo() {
    const pend = this.getPending(Date.now());
    if (pend && pend.kind !== "cleanup") { this.clearPending(); return { reply: "↩️ Dropped the question I was waiting on. Nothing was logged for it." }; }
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
      lines.push(`${p.rule_break ? "🔒" : p.status === "closed" ? (r.dollars >= 0 ? "✅" : "❌") : "⏳"} #${p.id} ${contractLabel(p)} in ${fmtPx(p.entry)} x${p.qty} | ${res}${p.grade ? " | grade " + p.grade : ""}${p.paper ? " | PAPER" : ""}`);
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
      "avg_exit", "result_usd", "result_pct", "grade", "paper", "route", "rule_break", "flags", "note"];
    const esc = (v) => { const s = v === null || v === undefined ? "" : String(v).replace(/\*\*/g, ""); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const lines = [head.join(",")];
    for (const p of rows) {
      const r = this.realized(p.id);
      lines.push([p.id, p.trade_date, fmtTime(p.opened_at), p.ticker, p.strike, p.right === "C" ? "call" : "put", p.exp,
        p.entry, p.qty, p.status, r.avgExit === null ? "" : r.avgExit.toFixed(2), r.soldQty ? r.dollars.toFixed(2) : "",
        r.pct === null ? "" : r.pct.toFixed(1), p.grade || "", p.paper ? "yes" : "no", p.route, p.rule_break ? "yes" : "no", p.flags, p.note].map(esc).join(","));
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
  "🌪️ **Trade bot**: just type it like a text, any order, typos are fine. ✅ = logged, ❓ = I need one thing.",
  "`in aapl 345p 10/30 .39 x2`  (also `aapl 345 put fri @ .39`, `in .39 aapl oct30 345p 2 contracts`)",
  "`in aapl 345/340p 11/13 .79`  spreads (`bear put 345 340`, `345p 340p`, `345-340 p`)",
  "`out 1.22` / `out aapl 1.22` / `out aapl 345 10/26 put 1.22`  closes (the price is the money number)",
  "`half .80` / `trim 50% .80` / `sold half at .8`  sells half",
  "`y` confirms my guess, a number picks from a list, or just send the missing piece (`11/13`, `.45`, `c`)",
  "`fix price 1.22` / `fix strike 345` / `fix exp 11/13` / `fix qty 2`  edits the last trade and its post",
  "`undo`  removes the last thing logged   `delete 8`  removes trade #8",
  "`plan qqq puts 727-733 rejection stop 733`  tomorrow's setup",
  "`note 1h 10 SMA close target`  add your read to the latest trade",
  "`check qqq`  EARLY meter (`check qqq c` for calls)   `grade hood`  daily grade A to D",
  "`open`  open trades   `recap`  today   `log`  spreadsheet file",
  "`paper` / `paper off`   `live` / `test`   `free in ...`  send that alert to the free channel",
].join("\n");
