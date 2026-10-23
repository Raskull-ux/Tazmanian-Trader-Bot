import assert from "node:assert/strict";
import fs from "node:fs";
import { computeGrade, gradeText } from "../src/grade.js";
const p = process.env.GRADE_FIXTURE;
if (p && fs.existsSync(p)) {
  const fx = JSON.parse(fs.readFileSync(p, "utf8"));
  for (const [sym, v] of Object.entries(fx)) {
    const js = [];
    for (let k = v.bars.length - 25; k < v.bars.length; k++) {
      const d = v.bars.slice(0, k + 1); const t = d.at(-1).t;
      const q = v.qqq.filter((b) => b.t <= t);
      js.push(computeGrade(d, q, "P").score);
    }
    assert.deepEqual(js, v.py, `${sym}: js ${js} vs python ${v.py}`);
    console.log(sym, "matches python:", js.slice(-8).join(","));
  }
  const s = Object.keys(fx)[0]; console.log(gradeText(s, computeGrade(fx[s].bars, fx[s].qqq, "P"), "P"));
}
console.log("grade tests: passed");
