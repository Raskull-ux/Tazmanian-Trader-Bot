import assert from "node:assert/strict";
import fs from "node:fs";
import { computeMeter, rsiExp, ema, atrWilder } from "../src/meter.js";
const fxPath = process.env.METER_FIXTURE;
// synthetic sanity checks (always run)
assert.equal(rsiExp([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]), 100);
assert.ok(Math.abs(ema([1, 1, 1, 10], 3).at(-1) - 5.5) < 1e-9);
assert.ok(Math.abs(atrWilder([{ h: 2, l: 1, c: 1.5 }, { h: 2, l: 1, c: 1.5 }]) - 1) < 1e-9);
if (fxPath && fs.existsSync(fxPath)) {
  const fx = JSON.parse(fs.readFileSync(fxPath, "utf8"));
  const m = computeMeter({ daily: fx.daily, hist5: fx.hist5, today5: fx.today5, side: "P" });
  const e = fx.expected;
  const close = (a, b, tol, what) => assert.ok(Math.abs(a - b) <= tol, `${what}: js ${a} vs python ${b}`);
  close(m.A, e.atr, 1e-6, "ATR"); close(m.r5, e.r5, 1e-6, "5m RSI"); close(m.r15, e.r15, 1e-6, "15m RSI");
  close(m.px, e.px, 1e-9, "price"); close(m.used, e.used, 1e-9, "range used");
  console.log(m.text);
}
console.log("meter tests: all passed");
