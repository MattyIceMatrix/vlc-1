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
export function canon(obj) {
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canon).join(",") + "]";
  return "{" + Object.keys(obj).sort().map(k => JSON.stringify(k) + ":" + canon(obj[k])).join(",") + "}";
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
  const i = raw.lastIndexOf(hexhash);
  return i < 0 ? null : raw.slice(0, i);
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
    catch { return { verdict: "UNREADABLE", results: [{ check: "parse", ok: false, note: `line ${i + 1} is not JSON` }] }; }
    if (hasFloat(obj)) floats = true;
    recs.push({ obj, raw, hash: dig(obj, hf) == null ? null : String(dig(obj, hf)), cls: String(dig(obj, cf) ?? "") });
  }
  if (!recs.length) return { verdict: "EMPTY", results: [] };

  // ---- VLC-L1-1: every record chains from the declared root -------------
  let prev = await chainRoot(recs, ad);
  let broken = -1;
  for (const [i, r] of recs.entries()) {
    const want = await recHash(prev, r, ad);
    if (want == null || r.hash !== want) { broken = i; break; }
    prev = r.hash;
  }
  // Record numbering follows the reference checker: records are indexed from 0
  // in file order (conformance.py enumerates lines from 0).
  if (broken >= 0) fail("VLC-L1-1", `binding broken at record ${broken}`);
  else ok("VLC-L1-1", `${recs.length} records chain from the declared root`);

  // ---- VLC-L1-3: the end marker carries the chain head -------------------
  const em = ad.integrity.end_marker ?? {};
  const end = [...recs].reverse().find(r => r.cls === em.class) ?? null;
  const headBeforeEnd = async () => {
    let p = await chainRoot(recs, ad);
    for (const r of recs) { if (r === end) break; const w = await recHash(p, r, ad); if (w == null || r.hash !== w) return null; p = r.hash; }
    return p;
  };
  if (!end) fail("VLC-L1-3", "no end marker record found");
  else {
    let headField = em.head_field ?? "head";
    let claimed = dig(end.obj, headField);
    if (claimed == null && em.head_field_fallback) { headField = em.head_field_fallback; claimed = dig(end.obj, headField); }
    const expected = em.self_bound === false || headField === em.head_field_fallback ? await headBeforeEnd() : await headBeforeEnd();
    if (claimed == null) fail("VLC-L1-3", "end marker carries no head value");
    else if (String(claimed) !== expected && String(claimed) !== prev) fail("VLC-L1-3", "end marker head does not match the recomputed binding");
    else ok("VLC-L1-3");
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
    const l1ok = res.find(x => x.check === "VLC-L1-1")?.ok && res.find(x => x.check === "VLC-L1-3")?.ok;
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
    else if (!l1ok) fail("VLC-L2-5", "the end marker is not bound by the chain, so the produced count is not established");
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
