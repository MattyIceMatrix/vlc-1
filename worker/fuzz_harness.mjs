// Stdin -> the live worker core's verdict, as JSON on stdout. 2026-11-25.
// Used by tools/fuzz_differential.py to compare the JS port against the
// Python reference on the same journal. Blast radius: reads stdin and the
// adapter path given as argv[2]; writes stdout only.
import { readFileSync } from "node:fs";
import { check } from "./core.mjs";

const adapterPath = process.argv[2];
if (!adapterPath) { console.error("usage: node fuzz_harness.mjs <adapter.json> < journal.jsonl"); process.exit(2); }
const ad = JSON.parse(readFileSync(adapterPath, "utf8"));
const journal = readFileSync(0, "utf8");
try {
  const out = await check(journal, ad);
  console.log(JSON.stringify(out));
} catch (e) {
  console.log(JSON.stringify({ harness_error: String(e?.message ?? e) }));
}
