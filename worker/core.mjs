// The live subset of the VLC-1 reference checker (conformance.py), ported
// function-for-function for the `sha256-chain-canonical` and
// `sha256-chain-prefix` mechanisms. Grades VLC-L1-1, VLC-L1-3 and VLC-L2-5.
// Levels 3-5 and the other mechanisms need the reference checker in this
// repository -- this endpoint says so rather than pretending.
// 2026-11-25, added alongside the static page; nothing existing changed.

const te = new TextEncoder();

export async function sha256Hex(data) {
  const buf = typeof data === "string" ? te.encode(data) : data;
  const d = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, "0")).join("");
}

// Python json.dumps(obj, sort_keys=True, separators=(",", ":")) parity.
// Integers and strings round-trip identically; a non-integer number may not
// (Python writes 1.0, JS writes 1), so the caller flags any float it sees.
// Python json.dumps(ensure_ascii=True) escapes every code unit >= 0x7F as
// \uXXXX (DEL included; astral chars as two surrogate escapes). JSON.stringify
// leaves them raw, so without this a journal with one accented character
// hashes differently here than in the reference checker and the chain
// falsely "breaks" (found by tools/fuzz_differential.py, 2026-11-25).
function asciiJson(s) {
  return JSON.stringify(s).replace(/[\u007f-￿]/g,
    c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
}

export function canon(obj) {
  if (typeof obj === "string") return asciiJson(obj);
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canon).join(",") + "]";
  return "{" + Object.keys(obj).sort().map(k => asciiJson(k) + ":" + canon(obj[k])).join(",") + "}";
}

export function dig(rec, path) {
  if (path == null) return null;
  let cur = rec;
  for (const part of String(path).split(".")) {
    if (cur !== null && typeof cur === "object" && part in cur) cur = cur[part];
    else return null;
  }
  return cur;
}

function hexToBytes(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return out;
}

export async function chainRoot(recs, ad) {
  const r = ad.integrity.root ?? {};
  const k = r.kind ?? "zero";
  if (k === "zero") return "0".repeat(64);
  if (k === "constant") return r.value;
  if (k === "field_of_first_record") {
    const v = dig(recs[0].obj, r.field);
    if (v == null) return null;
    if (r.transform === "sha256") return sha256Hex(String(v));
    return String(v);
  }
  throw new Error(`unknown integrity.root.kind ${k}`);
}

function stripHashSuffix(raw, hexhash) {
  // Reference semantics exactly (conformance.py strip_hash_suffix): the
  // chained text is the record minus its whole trailing hash MEMBER --
  // comma, key, value and the closing brace stay out of the hash input.
  // The earlier port cut at the hash VALUE, leaving `,"h":"` in the text,
  // which broke every prefix-chain grade (caught by the observer-adapter
  // parity spot check, 2026-11-25). hexhash is hex, so no regex escaping.
  const m = raw.match(new RegExp(',\\s*"[A-Za-z0-9_]+"\\s*:\\s*"' + hexhash + '"\\s*\\}\\s*$'));
  return m ? raw.slice(0, m.index) : null;
}

export async function recHash(prevHex, r, ad) {
  const mech = ad.integrity.mechanism;
  const hf = ad.integrity.hash_field;
  if (mech === "sha256-chain-prefix") {
    if (!r.hash) return null;
    const text = stripHashSuffix(r.raw, r.hash);
    if (text == null) return null;
    const prev = hexToBytes(prevHex);
    const body = te.encode(text);
    const joined = new Uint8Array(prev.length + body.length);
    joined.set(prev); joined.set(body, prev.length);
    return sha256Hex(joined);
  }
  if (mech === "sha256-chain-canonical") {
    const body = {};
    for (const k of Object.keys(r.obj)) if (k !== hf) body[k] = r.obj[k];
    return sha256Hex(prevHex + canon(body));
  }
  throw new Error(`mechanism ${mech} needs the reference checker`);
}

function hasFloat(x) {
  if (typeof x === "number") return !Number.isInteger(x);
  if (Array.isArray(x)) return x.some(hasFloat);
  if (x && typeof x === "object") return Object.values(x).some(hasFloat);
  return false;
}

export async function check(journalText, ad) {
  const res = [];
  const ok = (id, note) => res.push({ check: id, ok: true, note: note ?? "" });
  const fail = (id, note) => res.push({ check: id, ok: false, note });

  const lines = journalText.split("\n").filter(l => l.trim().length);
  const hf = ad.integrity.hash_field;
  const cf = ad.record_class_field ?? "class";
  const recs = [];
  let floats = false;
  for (const [i, raw] of lines.entries()) {
    let obj;
    try { obj = JSON.parse(raw); }
    catch { obj = undefined; }
    // A line that parses to null, an array, a number or a string is valid
    // JSON but not a record; the reference grades such a journal L0 ("not a
    // log"), it never crashes on it (fuzzer-found, 2026-11-25).
    if (obj === undefined || obj === null || typeof obj !== "object" || Array.isArray(obj)) {
      return { verdict: "UNREADABLE", records: i, head: null,
               results: [{ check: "parse", ok: false, note: `line ${i} is not a JSON object record (lines numbered from 0, like the reference checker's records)` }],
               caveats: [] };
    }
    if (hasFloat(obj)) floats = true;
    // Integers beyond 2^53 lose precision in JSON.parse, so the recomputed
    // canonical form would differ from the producer's bytes and every grade
    // after that would be wrong (found by tools/fuzz_differential.py,
    // 2026-11-25; nanosecond timestamps are exactly this class). The live
    // subset discloses instead of guessing; the reference checker (Python
    // arbitrary-precision ints) grades these fine.
    for (const m of raw.matchAll(/(?<=[\s{\[,:])-?\d{16,}(?=[\s,}\]]|$)/g)) {
      if (String(Number(m[0])) !== String(BigInt(m[0]))) {
        return { verdict: "NOT GRADABLE LIVE", records: i, head: null,
                 results: [{ check: "precision", ok: false,
                   note: `record ${i} carries an integer beyond 2^53 (${m[0].slice(0, 25)}…); JavaScript cannot hold it exactly, so this endpoint will not grade the journal rather than grade it wrongly` }],
                 caveats: ["Run the reference checker (conformance.py, arbitrary-precision) for this journal."] };
      }
    }
    recs.push({ obj, raw, hash: dig(obj, hf) == null ? null : String(dig(obj, hf)), cls: String(dig(obj, cf) ?? "") });
  }
  if (!recs.length) return { verdict: "EMPTY", records: 0, head: null,
    results: [{ check: "input", ok: false, note: "the journal is empty - paste JSONL records or load a demo journal" }],
    caveats: [] };

  // ---- VLC-L1-1 and VLC-L1-3: the chain walk, reference semantics ---------
  // Ported structurally from conformance.py check_l1 (2026-11-25, after the
  // observer-adapter parity check exposed the old walk):
  //  * root kind field_of_first_record: record 0 IS the root statement -- its
  //    own hash must EQUAL the derived root, and the walk starts at record 1;
  //  * only the LAST record can be the end marker (an end-class record in the
  //    middle is just a record);
  //  * the end marker is walked separately: its head CLAIM is compared with
  //    the head of what precedes it, then its OWN binding is recomputed --
  //    which can still fail VLC-L1-1 after a clean body walk (EXT-022);
  //  * a broken chain returns before VLC-L1-3 is ever evaluated.
  // Record numbering follows the reference: file order, from 0.
  const rootHex = await chainRoot(recs, ad);
  const em = ad.integrity.end_marker ?? null;
  let endBound = false;
  let end = null;       // only meaningful when the LAST record carries the class
  let prev = rootHex;   // the recomputed head as the walk advances
  let l1Done = false;   // true once L1-1/L1-3 verdicts are emitted

  if (rootHex == null) {
    fail("VLC-L1-1", "chain root not derivable from the delivered set");
    fail("VLC-L1-3", "not evaluated: no chain root");
    l1Done = true;
  }
  const skipFirst = (ad.integrity.root?.kind === "field_of_first_record");
  if (!l1Done && skipFirst && recs[0].hash && recs[0].hash !== rootHex) {
    fail("VLC-L1-1", "root record hash does not equal the derived root");
    fail("VLC-L1-3", "not evaluated: the chain binding is broken at record 0, before the end marker could be checked");
    l1Done = true;
  }
  let endClassMismatch = false;
  if (!l1Done && em) {
    const last = recs[recs.length - 1];
    if (last.cls === em.class) end = last; else endClassMismatch = true;
  }
  if (!l1Done) {
    const start = skipFirst ? 1 : 0;
    const stop = end ? recs.length - 1 : recs.length; // end marker walked separately
    for (let i = start; i < stop; i++) {
      const r = recs[i];
      const want = await recHash(prev, r, ad);
      if (want == null) {
        fail("VLC-L1-1", `record ${i} carries no recomputable binding`);
        fail("VLC-L1-3", `not evaluated: the chain binding is broken at record ${i}, before the end marker could be checked`);
        l1Done = true; break;
      }
      if (r.hash !== want) {
        fail("VLC-L1-1", `binding broken at record ${i}`);
        fail("VLC-L1-3", `not evaluated: the chain binding is broken at record ${i}, before the end marker could be checked`);
        l1Done = true; break;
      }
      prev = r.hash;
    }
  }
  if (!l1Done) {
    if (!em) {
      ok("VLC-L1-1", `${recs.length} records chain from the declared root`);
      fail("VLC-L1-3", "the adapter declares no end marker");
    } else if (endClassMismatch) {
      ok("VLC-L1-1", `${recs.length} records chain from the declared root`);
      fail("VLC-L1-3", `last record class is ${recs[recs.length - 1].cls}, expected ${em.class}: truncation undetectable`);
    } else {
      // head claim is judged against the head of what PRECEDES the marker
      let headField = em.head_field ?? "head";
      let claimed = dig(end.obj, headField);
      if (claimed == null && em.head_field_fallback) { headField = em.head_field_fallback; claimed = dig(end.obj, headField); }
      const headOk = claimed != null && String(claimed) === prev;
      // then the marker's own binding (EXT-022): recomputed only when it
      // carries a hash; a mismatch is a chain failure, not a head failure
      if (em.self_bound !== false && end.hash) {
        const h = await recHash(prev, end, ad);
        if (h != null && h !== end.hash) {
          fail("VLC-L1-1", "end marker binding broken");
          fail("VLC-L1-3", "not evaluated: the end marker's own binding is broken");
          l1Done = true;
        } else if (h != null) { endBound = true; prev = end.hash; }
      }
      if (!l1Done) {
        ok("VLC-L1-1", `${recs.length} records chain from the declared root`);
        if (claimed == null) fail("VLC-L1-3", "end marker carries no head value");
        else if (!headOk) fail("VLC-L1-3", "end marker head does not match the recomputed binding");
        else if (endBound) ok("VLC-L1-3", "end marker is bound by the chain and names the recomputed head");
        else fail("VLC-L1-3", "not established: the end marker names the recomputed head but carries no recomputable binding of its own; records dropped from the tail are undetectable on the log alone");
      }
    }
  }

  // ---- VLC-L2-5: delivered + declared-lost == produced --------------------
  // Upstream semantics (conformance.py check_l2): a loss declaration and a
  // coverage declaration are not EVENT records, so non_event_classes are out
  // of the delivered count (double-count fix, reported by pipavlo82,
  // 2026-09-21); and a produced count read from an end marker the chain does
  // not bind is NOT established (EXT-022) -- it could be rewritten to hide
  // exactly the records the identity exists to count. Counts must be
  // non-negative JSON integers (EXT-023).
  const lo = ad.loss;
  if (!lo || lo.mode === "none") {
    fail("VLC-L2-5", "no completeness identity is computable");
  } else {
    const markers = new Set(ad.marker_classes ?? []);
    const nonEvent = new Set(ad.non_event_classes ?? []);
    const delivered = recs.filter(r => !markers.has(r.cls) && !nonEvent.has(r.cls));
    const intOrNull = v => (typeof v === "number" && Number.isInteger(v) && v >= 0) ? v : null;
    let declared = 0, badCount = false;
    for (const r of recs.filter(x => x.cls === lo.declaration_class)) {
      const v = intOrNull(dig(r.obj, lo.count_field));
      if (v == null) { badCount = true; break; }
      declared += v;
    }
    // EXT-022, upstream rule exactly: the produced count is established iff
    // the end marker's OWN binding verifies in the chain (conformance.py
    // ctx.end_bound). A bound END whose head CLAIM names the wrong value
    // fails VLC-L1-3 but its counts are still chain-protected, so VLC-L2-5
    // still evaluates. (Fuzzer-found divergence, 2026-11-25: the earlier
    // gate wrongly required L1-3 too.)
    // endBound comes from the chain walk above (reference ctx.end_bound)
    let produced = null;
    if (end && lo.produced?.kind === "sum_of_end_marker_fields" && !badCount) {
      let sum = 0, allInt = true;
      for (const f of lo.produced.fields) {
        const v = intOrNull(dig(end.obj, f));
        if (v == null) { allInt = false; break; }
        sum += v;
      }
      if (allInt) produced = sum;
    }
    if (badCount) fail("VLC-L2-5", "a count field is not a non-negative JSON integer");
    else if (produced == null) fail("VLC-L2-5", "no produced count is available from the end marker");
    else if (!endBound) fail("VLC-L2-5", "the end marker is not bound by the chain, so the produced count is not established");
    else if (delivered.length + declared !== produced)
      fail("VLC-L2-5", `identity does not close: ${delivered.length} delivered + ${declared} declared != ${produced} produced`);
    else ok("VLC-L2-5", `${delivered.length} delivered + ${declared} declared lost == ${produced} produced`);
  }

  const allOk = res.every(r => r.ok);
  return {
    verdict: allOk ? "L1/L2 SUBSET PASS" : "FAIL",
    results: res,
    records: recs.length,
    head: prev,
    caveats: [
      "This endpoint grades VLC-L1-1, VLC-L1-3 and VLC-L2-5 for the canonical-chain and prefix-chain mechanisms only.",
      "Levels 3-5, the other mechanisms and the full 25-adapter set need the reference checker: conformance.py in the repository.",
      ...(floats ? ["A record contains a non-integer number; canonical-JSON parity with the reference checker is not guaranteed for floats."] : []),
    ],
  };
}
