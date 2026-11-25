// Parity: the live subset must agree with conformance.py on every example
// journal for the three checks it grades. Run: node worker/parity.test.mjs
import { check } from "./core.mjs";
import { readFileSync } from "node:fs";

const ad = JSON.parse(readFileSync("adapters/generic-appjsonl.json", "utf8"));
const expect = JSON.parse(readFileSync("worker/parity-expected.json", "utf8"));
let bad = 0;
for (const [file, want] of Object.entries(expect)) {
  const r = await check(readFileSync(`examples/${file}`, "utf8"), ad);
  for (const [id, wantOk] of Object.entries(want)) {
    const got = r.results.find(x => x.check === id)?.ok ?? null;
    const okStr = got === wantOk ? "agree" : "DISAGREE";
    if (got !== wantOk) bad++;
    console.log(`${file} ${id}: reference=${wantOk} live=${got} ${okStr}`);
  }
}
console.log(bad === 0 ? "PARITY PASS" : `PARITY FAIL (${bad})`);
process.exit(bad === 0 ? 0 : 1);
