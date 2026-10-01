#!/usr/bin/env node
"use strict";
/* AER-1 conformance runner (JavaScript port of conformance.py).
 *
 * Checks every vector in test-vectors/ against the core rules of
 * AER-1 (draft-zambo-aer1-02, Sections 3-6):
 *
 *   valid/   - every file MUST conform (schema shape + hash recomputation)
 *   invalid/ - every file MUST fail at least one check, with a reason
 *
 * Node.js standard library only (fs, path, crypto). Exit 0 when all
 * expectations hold, 1 otherwise.
 *
 * Faithful port of conformance.py v1.3.0: strict UTF-8 decode of
 * canonical_bytes (fail closed), calendar-valid RFC 3339 timestamps
 * (shape alone is not enough), a hard error when a fixture
 * directory matches zero files instead of a silent pass, and the
 * reference-producer profile check (checkReferenceProfile) with the
 * test-vectors/invalid-profile/ boundary fixtures.
 *
 * v1.4.0 additions (faithful port of conformance.py v1.4.0): offline
 * workflow verification verifyWorkflow() (Section 8.2 steps 3-4; steps 1-2
 * need network and stay the caller's job) with the MM-1
 * no-duplicate-receipt_id rule; checkMerkleVectors() mirroring the Python
 * gate, including the optional expected_workflow_verdict / rejected_by
 * vector fields; Section 7 chain validation verifyChain() with the pinned
 * prev_digest construction and the close:true suffix-truncation kill;
 * checkChainVectors() regression gate over chain-vectors.json.
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const HERE = __dirname;
const CORE = ["id", "receipt_schema_version", "created_at", "tool",
              "provenance_class", "canonical_bytes", "output_hash",
              "verification_status"];

// Python's re `$` also matches just before a single trailing "\n"; the
// (?:\n)? preserves that quirk exactly.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:\n)?$/;
const RFC3339_RE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})(?:\n)?$/;
const HASH_RE = /^sha256:[0-9a-f]{64}(?:\n)?$/;
const PROV_RE = /^(EXECUTED BY [A-Z0-9][A-Z0-9 ._-]*|OBSERVED VIA GATEWAY|LOGGED BY AGENT)(?:\n)?$/;
const B64_RE = /^[A-Za-z0-9+/]*={0,2}(?:\n)?$/;
// Strict component parse used for calendar validation (no trailing-newline
// tolerance here: Python's datetime.fromisoformat rejects it).
const TS_PARTS_RE = /^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$/;

function isLeapYear(y) {
    return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}

function daysInMonth(y, m) {
    switch (m) {
        case 2: return isLeapYear(y) ? 29 : 28;
        case 4: case 6: case 9: case 11: return 30;
        default: return 31;
    }
}

// Mirrors datetime.fromisoformat(s.replace("Z", "+00:00")) range checks:
// hour 0..23, minute 0..59, second 0..59 (no leap seconds), month 1..12,
// day valid for month/year (proleptic Gregorian), year >= 1, and the UTC
// offset strictly between -24h and +24h (offset minutes are NOT capped at
// 59 -- e.g. +00:99 is a valid 99-minute offset in CPython).
function validCalendarDateTime(s) {
    const t = s.replace("Z", "+00:00");
    const m = TS_PARTS_RE.exec(t);
    if (!m) return false;
    const year = +m[1], mon = +m[2], day = +m[3];
    const hh = +m[4], mi = +m[5], ss = +m[6];
    if (year < 1 || year > 9999) return false;
    if (mon < 1 || mon > 12) return false;
    if (day < 1 || day > daysInMonth(year, mon)) return false;
    if (hh > 23 || mi > 59 || ss > 59) return false;
    const off = m[8];
    if (off !== "Z") {
        const sign = off[0] === "-" ? -1 : 1;
        const totalMinutes = sign * (+off.slice(1, 3) * 60 + +off.slice(4, 6));
        if (!(totalMinutes > -1440 && totalMinutes < 1440)) return false;
    }
    return true;
}

function isObject(v) {
    return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isNonEmptyString(v) {
    return typeof v === "string" && v.length > 0;
}

const utf8Decoder = new TextDecoder("utf-8", { fatal: true });

function check(receipt) {
    // Return a list of failure reasons; empty means conformant.
    const failures = [];
    if (!isObject(receipt)) {
        return ["receipt is not a JSON object"];
    }
    for (const field of CORE) {
        if (!(field in receipt)) {
            failures.push("missing required member: " + field);
        }
    }
    if (failures.length) {
        return failures;
    }
    if (typeof receipt["id"] !== "string" || !UUID_RE.test(receipt["id"])) {
        failures.push("id is not a lowercase UUID");
    }
    if (!isNonEmptyString(receipt["receipt_schema_version"])) {
        failures.push("receipt_schema_version is not a non-empty string");
    }
    if (typeof receipt["created_at"] !== "string") {
        failures.push("created_at is not a string");
    } else if (!RFC3339_RE.test(receipt["created_at"])) {
        failures.push("created_at is not RFC 3339");
    } else if (!validCalendarDateTime(receipt["created_at"])) {
        // Shape alone is not enough: "2026-02-30T09:00:00.000Z" matches the
        // RFC 3339 pattern but is not a real calendar date. Fail closed.
        failures.push("created_at is not a valid calendar date/time");
    }
    const tool = receipt["tool"];
    if (!isObject(tool) ||
            !["name", "version", "scope"].every(
                (k) => typeof tool[k] === "string" && tool[k])) {
        failures.push("tool is not an object with name/version/scope strings");
    }
    if (typeof receipt["provenance_class"] !== "string" ||
            !PROV_RE.test(receipt["provenance_class"])) {
        failures.push("provenance_class is not a known class");
    }
    const cb = receipt["canonical_bytes"];
    let raw = null;
    // Python's base64.b64decode(cb, validate=True) rejects anything the
    // shape regex misses only via incorrect padding, i.e. length % 4 != 0.
    if (typeof cb !== "string" || !B64_RE.test(cb) || cb.length % 4 !== 0) {
        failures.push("canonical_bytes is not valid base64");
    } else {
        raw = Buffer.from(cb, "base64");
        // The commitment is over the exact UTF-8 byte sequence
        // (draft Sections 3-4). A decodable base64 payload that is not
        // valid UTF-8 (e.g. b"\xff") fails closed here.
        try {
            utf8Decoder.decode(raw);
        } catch (e) {
            failures.push("canonical_bytes is not valid UTF-8");
            raw = null;
        }
    }
    const oh = receipt["output_hash"];
    if (typeof oh !== "string" || !HASH_RE.test(oh)) {
        failures.push("output_hash is not sha256: + lowercase hex digest");
    } else if (raw !== null) {
        const want = "sha256:" + crypto.createHash("sha256").update(raw).digest("hex");
        if (oh !== want) {
            failures.push("output_hash does not match sha256(canonical_bytes)");
        }
    }
    if (receipt["verification_status"] !== "verified") {
        failures.push("verification_status is not verified");
    }
    return failures;
}

// Reference-producer profile check. Returns failure reasons; [] = pass.
//
// The reference producer commits to canonical payloads shaped as a JSON
// object carrying the 'inputs' member (alongside 'tool'/'outputs'). A
// receipt whose payload omits 'inputs' is still core-conformant and MUST be
// accepted by interop verifiers, but it is NOT reference-producer
// conformant. Fail closed at every decode step. Regression rule for the
// missing-inputs finding (independent review, 2026-09-27).
function checkReferenceProfile(receipt) {
    if (!isObject(receipt)) {
        return ["receipt is not a JSON object"];
    }
    const cb = receipt["canonical_bytes"];
    if (typeof cb !== "string") {
        return ["canonical_bytes is not a string"];
    }
    // Mirror Python's base64.b64decode(cb, validate=True): the shape regex
    // misses only incorrect padding, i.e. length % 4 !== 0.
    if (!B64_RE.test(cb) || cb.length % 4 !== 0) {
        return ["canonical_bytes is not valid base64"];
    }
    const raw = Buffer.from(cb, "base64");
    try {
        utf8Decoder.decode(raw);
    } catch (e) {
        return ["canonical_bytes is not valid UTF-8"];
    }
    let payload;
    try {
        payload = JSON.parse(raw.toString("utf8"));
    } catch (e) {
        return ["canonical payload is not JSON"];
    }
    if (!isObject(payload)) {
        return ["canonical payload is not a JSON object"];
    }
    if (!("inputs" in payload)) {
        return ["reference-producer payload omits the 'inputs' member"];
    }
    return [];
}

function checkDisinterestedTier(receipt) {
    const failures = [];
    const anchor = isObject(receipt) ? receipt.anchor : null;
    if (!isObject(anchor)) return ["anchor is not an object"];
    if (Object.keys(anchor).sort().join(",") !== "anchored_at,leaf_hash,log,proof") {
        failures.push("anchor has members other than log/leaf_hash/anchored_at/proof");
    }
    if (!isNonEmptyString(anchor.log)) failures.push("anchor.log is not a non-empty string");
    const leaf = anchor.leaf_hash;
    if (typeof leaf !== "string" || !HASH_RE.test(leaf)) {
        failures.push("anchor.leaf_hash is not sha256: + lowercase hex digest");
    } else {
        const cb = receipt.canonical_bytes;
        let raw = null;
        if (typeof cb !== "string" || !B64_RE.test(cb) || cb.length % 4 !== 0) {
            failures.push("canonical_bytes is not valid base64");
        } else {
            raw = Buffer.from(cb, "base64");
            try { utf8Decoder.decode(raw); } catch (e) {
                failures.push("canonical_bytes is not valid UTF-8 base64");
                raw = null;
            }
        }
        if (raw !== null) {
            const want = "sha256:" + crypto.createHash("sha256").update(raw).digest("hex");
            if (leaf !== want) failures.push("anchor.leaf_hash does not match canonical_bytes");
        }
    }
    const anchoredAt = anchor.anchored_at;
    if (typeof anchoredAt !== "string" || !RFC3339_RE.test(anchoredAt)) {
        failures.push("anchor.anchored_at is not RFC 3339");
    } else if (!validCalendarDateTime(anchoredAt)) {
        failures.push("anchor.anchored_at is not a valid calendar date/time");
    }
    if (!isObject(anchor.proof)) failures.push("anchor.proof is not an object");
    return failures;
}

// Section 8.1 normative construction: leaf = SHA-256 over the UTF-8
// bytes of receipt_id; internal node = SHA-256 over raw 32-byte left ||
// raw 32-byte right; odd trailing node duplicated.
function merkleRootCanonical(receiptIds) {
    if (!receiptIds.length) {
        return crypto.createHash("sha256").update(Buffer.alloc(0)).digest("hex");
    }
    let level = receiptIds.map((rid) =>
        crypto.createHash("sha256").update(rid, "utf8").digest());
    while (level.length > 1) {
        if (level.length % 2) level.push(level[level.length - 1]);
        const next = [];
        for (let i = 0; i < level.length; i += 2) {
            next.push(crypto.createHash("sha256")
                .update(Buffer.concat([level[i], level[i + 1]])).digest());
        }
        level = next;
    }
    return level[0].toString("hex");
}

// Section 8.2 steps 3-4: offline workflow verification. Returns a list of
// failure reasons; empty means valid.
//
// Steps 1-2 (fetch each step's receipt over the network and confirm each
// receipt exists and is addressed) need network access and STAY THE
// CALLER'S JOB: this function verifies only the offline mechanics, in
// order: workflow is an object; steps is a non-empty list; every step
// carries an integer seq and a string receipt_id; seq values are exactly
// 1..n in order with no gaps and no duplicate seq; NO two steps share the
// same receipt_id value (the MM-1 rule); the workflow's merkle_root equals
// the recomputed Section 8.1 root over the ordered receipt_id strings.
function verifyWorkflow(w) {
    if (!isObject(w)) {
        return ["workflow is not a JSON object"];
    }
    const steps = w.steps;
    if (!Array.isArray(steps) || !steps.length) {
        return ["workflow steps is not a non-empty list"];
    }
    const failures = [];
    for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        if (!isObject(step)) {
            failures.push("step " + (i + 1) + " is not an object");
            continue;
        }
        if (typeof step.seq !== "number" || !Number.isInteger(step.seq)) {
            failures.push("step " + (i + 1) + " seq is not an integer");
        }
        if (typeof step.receipt_id !== "string") {
            failures.push("step " + (i + 1) + " receipt_id is not a string");
        }
    }
    if (failures.length) {
        return failures;
    }
    const n = steps.length;
    for (let i = 0; i < n; i++) {
        if (steps[i].seq !== i + 1) {
            failures.push("step seq values are not 1.." + n + " in order " +
                "(index " + i + " carries seq " + steps[i].seq + ")");
            break;
        }
    }
    const seen = new Set();
    for (const step of steps) {
        const rid = step.receipt_id;
        if (seen.has(rid)) {
            failures.push("duplicate receipt_id: " + rid);
            break;
        }
        seen.add(rid);
    }
    const root = merkleRootCanonical(steps.map((s) => s.receipt_id));
    if (typeof w.merkle_root !== "string" || w.merkle_root !== root) {
        failures.push("merkle_root does not match the recomputed " +
            "Section 8.1 root");
    }
    return failures;
}

// Regression gate for the Section 8.1 Merkle construction, locked to
// merkle-vectors.json. Mirrors check_merkle_vectors() faithfully,
// including the legacy-construction vectors and the optional
// expected_workflow_verdict / rejected_by vector fields. Returns a list of
// problem strings (empty = green).
function checkMerkleVectors() {
    const problems = [];
    const p = path.join(HERE, "merkle-vectors.json");
    let corpus;
    try {
        corpus = JSON.parse(fs.readFileSync(p, "utf8"));
    } catch (e) {
        return ["merkle-vectors.json is missing (no silent pass)"];
    }
    const vectors = corpus.vectors || [];
    if (!vectors.length) {
        return ["merkle-vectors.json contains no vectors (no silent pass)"];
    }
    for (const v of vectors) {
        const name = v.name || "?";
        if ("receipt_ids" in v) {
            const got = merkleRootCanonical(v.receipt_ids);
            const ok = got === v.expected_root;
            console.log("[merkle]  " + name + ": " + (ok ? "PASS" : "FAIL") +
                (ok ? "" : " (got " + got + ")"));
            if (!ok) {
                problems.push("merkle vector " + name + ": expected " +
                    v.expected_root + ", got " + got);
            }
        } else if ("leaves" in v) {
            // Legacy-construction vector: recompute from the documented
            // preimages and require the historical root, never the canonical.
            let lvl = v.leaves.slice().sort((a, b) => a.seq - b.seq)
                .map((l) => crypto.createHash("sha256").update(l.preimage, "utf8").digest());
            while (lvl.length > 1) {
                if (lvl.length % 2) lvl.push(lvl[lvl.length - 1]);
                const next = [];
                for (let i = 0; i < lvl.length; i += 2) {
                    next.push(crypto.createHash("sha256")
                        .update(Buffer.concat([lvl[i], lvl[i + 1]])).digest());
                }
                lvl = next;
            }
            const got = lvl.length ? lvl[0].toString("hex")
                : crypto.createHash("sha256").update(Buffer.alloc(0)).digest("hex");
            const ok = got === v.expected_root && got !== v.must_not_equal;
            console.log("[merkle]  " + name + ": " + (ok ? "PASS" : "FAIL") +
                (ok ? "" : " (got " + got + ")"));
            if (!ok) {
                problems.push("merkle vector " + name + ": legacy root mismatch (got " + got + ")");
            }
        }
        if (v.must_not_equal && "receipt_ids" in v) {
            if (v.expected_root === v.must_not_equal) {
                problems.push("merkle vector " + name + ": root must differ from " +
                    "the canonical/legacy counterpart");
            }
        }
        // Workflow-verdict extension: a vector may carry
        // expected_workflow_verdict ("valid" or "invalid"). Build the
        // workflow exactly as specified and require the verifyWorkflow()
        // checks to agree with the expected verdict. The root-recompute
        // check above STILL runs: a duplicate vector's root MUST recompute
        // to expected_root even though its workflow verdict is invalid
        // (the root matches but the workflow is rejected, which is the
        // point of the MM-1 rule).
        const verdictField = v.expected_workflow_verdict;
        if (verdictField !== undefined && verdictField !== null) {
            if (!("receipt_ids" in v)) {
                problems.push("merkle vector " + name + ": " +
                    "expected_workflow_verdict needs receipt_ids (no silent pass)");
                console.log("[merkle-workflow] " + name + ": FAIL (no receipt_ids)");
                continue;
            }
            const wf = {
                steps: v.receipt_ids.map((rid, i) => ({ seq: i + 1, receipt_id: rid })),
                merkle_root: v.expected_root,
            };
            const wfFails = verifyWorkflow(wf);
            const verdict = wfFails.length ? "invalid" : "valid";
            let wok = verdict === verdictField;
            if (wok && verdict === "invalid") {
                const rb = v.rejected_by;
                if (!(typeof rb === "string" && wfFails.some((f) => f.includes(rb)))) {
                    wok = false;
                }
            }
            console.log("[merkle-workflow] " + name + ": " + (wok ? "PASS" : "FAIL") +
                (wok ? "" : " (verdict " + verdict + ")"));
            if (!wok) {
                problems.push("merkle vector " + name + ": expected workflow " +
                    "verdict " + verdictField + ", got " + verdict);
            }
        }
    }
    return problems;
}

// Section 7 chain mechanics. Returns failure reasons; [] = valid.
//
// Pinned construction, implemented exactly: entry digest = SHA-256 over
// the raw bytes obtained by base64-decoding the entry's canonical_bytes
// member (strict decode, fail closed on bad base64); entry 0's prev_digest
// MUST be exactly 64 zero characters; each later entry's prev_digest MUST
// be a string equal to the lowercase hex digest of the previous entry
// (mismatch names the entry index); the LAST entry MUST carry close: true
// (boolean true), anything else is a failure (this is the
// suffix-truncation kill); an empty timeline is a failure.
//
// Chain mechanics only: entries are NOT required to be full valid
// receipts here. Per-entry receipt verification (schema, hashes) is the
// caller's job, not this function's.
function verifyChain(timeline) {
    if (!Array.isArray(timeline) || !timeline.length) {
        return ["timeline is not a non-empty list"];
    }
    const failures = [];
    let prev = null;
    for (let i = 0; i < timeline.length; i++) {
        const entry = timeline[i];
        if (!isObject(entry)) {
            failures.push("entry " + i + " is not an object");
            break;
        }
        const cb = entry.canonical_bytes;
        // Strict base64 decode, fail closed. Mirrors Python's
        // base64.b64decode(cb, validate=True): the shape regex misses only
        // incorrect padding, i.e. length % 4 !== 0.
        if (typeof cb !== "string" || !B64_RE.test(cb) || cb.length % 4 !== 0) {
            failures.push("entry " + i + " canonical_bytes is not valid base64");
            break;
        }
        const raw = Buffer.from(cb, "base64");
        const digest = crypto.createHash("sha256").update(raw).digest("hex");
        const pd = entry.prev_digest;
        if (i === 0) {
            if (typeof pd !== "string" || pd !== "0".repeat(64)) {
                failures.push("entry 0 prev_digest is not 64 zero characters");
            }
        } else if (typeof pd !== "string" || pd !== prev) {
            failures.push("entry " + i + " prev_digest does not match the digest " +
                "of entry " + (i - 1));
        }
        prev = digest;
    }
    // The suffix-truncation kill: the chain is not closed without it.
    const last = timeline[timeline.length - 1];
    if (isObject(last) && last.close !== true) {
        failures.push("last entry does not carry close: true");
    }
    return failures;
}

// Regression gate for the Section 7 chain construction, locked to
// chain-vectors.json. Mirrors check_chain_vectors() faithfully. Returns a
// list of problem strings (empty = green). Fail closed: missing file,
// empty vector list, or an unknown expected_verdict are problems, never
// silent passes.
function checkChainVectors() {
    const problems = [];
    const p = path.join(HERE, "chain-vectors.json");
    let corpus;
    try {
        corpus = JSON.parse(fs.readFileSync(p, "utf8"));
    } catch (e) {
        return ["chain-vectors.json is missing (no silent pass)"];
    }
    const vectors = corpus.vectors || [];
    if (!vectors.length) {
        return ["chain-vectors.json contains no vectors (no silent pass)"];
    }
    for (const v of vectors) {
        const name = v.name || "?";
        const expected = v.expected_verdict;
        if (expected !== "valid" && expected !== "invalid") {
            problems.push("chain vector " + name + ": unknown expected_verdict " +
                JSON.stringify(expected) + " (no silent pass)");
            console.log("[chain]  " + name + ": FAIL (unknown expected_verdict)");
            continue;
        }
        // The corpus names the timeline member "timeline". Accept "entries"
        // as a fallback alias. Fail closed: neither key present yields
        // null/undefined, which verifyChain rejects, so a "valid" vector
        // can never silently pass on a missing member.
        let tl = v.timeline;
        if (tl === undefined || tl === null) tl = v.entries;
        const fails = verifyChain(tl);
        const ok = (!fails.length) === (expected === "valid");
        console.log("[chain]  " + name + ": " + (ok ? "PASS" : "FAIL") +
            (ok ? "" : " (" + fails.join("; ") + ")"));
        if (!ok) {
            problems.push("chain vector " + name + ": expected " + expected +
                ", got " + (fails.length ? "invalid" : "valid"));
        }
    }
    return problems;
}
// -07 hardened entry digest. Returns lowercase hex SHA-256.
//
// digest_i = SHA-256 over the UTF-8 bytes of the canonical JSON object
// {prev_digest, seq, job_id, close, id, tool, provenance_class,
// output_hash} with keys sorted by Unicode code point and no whitespace,
// where output_hash = lowercase hex SHA-256 of the base64-decoded
// canonical_bytes. A missing close member digests as false. Throws on
// bad base64 (fail closed).
function jsonAsciiV07(s){return s.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u0080-\uD7FF\uE000-\uFFFF]/g,function(m){var o="",i;for(i=0;i<m.length;i++){o+="\\u"+m.charCodeAt(i).toString(16).padStart(4,"0")}return o})}
function chainEntryDigestV07(entry) {
    const raw = Buffer.from(entry.canonical_bytes, "base64");
    const outputHash = crypto.createHash("sha256").update(raw).digest("hex");
    // Keys inserted in sorted order; JSON.stringify emits string keys in
    // insertion order. Values are strings, integers, and booleans only.
    // Normalize integer-valued floats (1.0) to int (1) for digest stability,
    // mirroring the Python implementation.
    const seqVal = entry.seq;
    const seqNorm = (typeof seqVal === "number" && Number.isFinite(seqVal) && Math.floor(seqVal) === seqVal) ? Math.floor(seqVal) : seqVal;
    const payload = {
        close: entry.close === undefined ? false : entry.close,
        id: entry.id,
        job_id: entry.job_id,
        output_hash: outputHash,
        prev_digest: entry.prev_digest,
        provenance_class: entry.provenance_class,
        seq: seqNorm,
        tool: entry.tool,
    };
    const blob = Buffer.from(jsonAsciiV07(JSON.stringify(payload)), "utf8");
    return crypto.createHash("sha256").update(blob).digest("hex");
}

// Section 7 chain mechanics, -07 hardened construction. Returns failure
// reasons; [] = valid. Mirrors verify_chain_v07() in conformance.py
// exactly: the digest binds prev_digest, seq, job_id, close, id, tool,
// provenance_class, and output_hash; entry 0 needs the 64-zero genesis
// digest and seq 1; seq contiguous from 1; one job_id per chain; close is
// boolean, true only on the last entry; links must match recomputed
// digests; strict base64, fail closed. Same honest limit as the Python
// twin: truncation with re-linking needs an anchored endpoint.
function verifyChainV07(timeline) {
    if (!Array.isArray(timeline) || !timeline.length) {
        return ["timeline is not a non-empty list"];
    }
    const failures = [];
    let job = null;
    let prev = null;
    for (let i = 0; i < timeline.length; i++) {
        const entry = timeline[i];
        if (!isObject(entry)) {
            return ["entry " + i + " is not an object"];
        }
        const cb = entry.canonical_bytes;
        // Strict base64 decode, fail closed. Mirrors Python's
        // base64.b64decode(cb, validate=True) the way the -06 JS
        // verifier does: shape regex plus a length % 4 guard. No
        // re-encode round-trip: Python accepts non-canonical trailing
        // bits, so a round-trip would make JS stricter than Python.
        if (typeof cb !== "string" || !B64_RE.test(cb) || cb.length % 4 !== 0) {
            return ["entry " + i + " canonical_bytes is not valid base64"];
        }
        const raw = Buffer.from(cb, "base64");
        for (const m of ["id", "tool", "provenance_class", "job_id", "prev_digest"]) {
            if (typeof entry[m] !== "string" || !entry[m].length) {
                return ["entry " + i + " missing " + m];
            }
        }
        const seq = entry.seq;
        if (typeof seq !== "number" || !Number.isInteger(seq) && !(Number.isFinite(seq) && Math.floor(seq) === seq)) {
            return ["entry " + i + " seq is not an integer"];
        }
        const seqInt = Math.floor(seq);
        if (seqInt !== i + 1) {
            failures.push("entry " + i + " seq " + seqInt +
                " breaks contiguity (expected " + (i + 1) + ")");
        }
        if (job === null) {
            job = entry.job_id;
        } else if (entry.job_id !== job) {
            failures.push("entry " + i + " job_id mixes jobs");
        }
        const pd = entry.prev_digest;
        if (i === 0) {
            if (pd !== "0".repeat(64)) {
                failures.push("entry 0 prev_digest is not 64 zero characters");
            }
        } else if (pd !== prev) {
            failures.push("entry " + i + " prev_digest does not match the digest " +
                "of entry " + (i - 1));
        }
        if ("close" in entry && typeof entry.close !== "boolean") {
            failures.push("entry " + i + " close is not a boolean");
        } else if (i < timeline.length - 1 && entry.close === true) {
            failures.push("entry " + i + " carries close:true before the last entry");
        }
        prev = chainEntryDigestV07(entry);
    }
    const last = timeline[timeline.length - 1];
    if (!isObject(last) || last.close !== true) {
        failures.push("last entry does not carry close: true");
    }
    return failures;
}

// Regression gate for the -07 hardened Section 7 chain construction,
// locked to chain-vectors-v07.json. Mirrors check_chain_vectors_v07()
// faithfully. Fail closed: missing file, empty vector list, or an
// unknown expected_verdict are problems, never silent passes.
function checkChainVectorsV07() {
    const problems = [];
    const p = path.join(HERE, "chain-vectors-v07.json");
    let corpus;
    try {
        corpus = JSON.parse(fs.readFileSync(p, "utf8"));
    } catch (e) {
        return ["chain-vectors-v07.json is missing (no silent pass)"];
    }
    const vectors = corpus.vectors || [];
    if (!vectors.length) {
        return ["chain-vectors-v07.json contains no vectors (no silent pass)"];
    }
    for (const v of vectors) {
        const name = v.name || "?";
        const expected = v.expected_verdict;
        if (expected !== "valid" && expected !== "invalid") {
            problems.push("chain-v07 vector " + name + ": unknown expected_verdict " +
                JSON.stringify(expected) + " (no silent pass)");
            console.log("[chain-v07] " + name + ": FAIL (unknown expected_verdict)");
            continue;
        }
        let tl = v.timeline;
        if (tl === undefined || tl === null) tl = v.entries;
        const fails = verifyChainV07(tl);
        const ok = (!fails.length) === (expected === "valid");
        console.log("[chain-v07] " + name + ": " + (ok ? "PASS" : "FAIL") +
            (ok ? "" : " (" + fails.join("; ") + ")"));
        if (!ok) {
            problems.push("chain-v07 vector " + name + ": expected " + expected +
                ", got " + (fails.length ? "invalid" : "valid"));
        }
    }
    return problems;
}
function globJson(dir) {    let names;
    try {
        names = fs.readdirSync(dir);
    } catch (e) {
        return [];
    }
    // Like Python's glob("*.json"): case-sensitive, no dotfiles.
    return names
        .filter((n) => n.endsWith(".json") && !n.startsWith("."))
        .sort()
        .map((n) => path.join(dir, n));
}

function main() {
    const problems = [];
    const validPaths = globJson(path.join(HERE, "test-vectors", "valid"));
    const invalidPaths = globJson(path.join(HERE, "test-vectors", "invalid"));
    const profileInvalidPaths = globJson(path.join(HERE, "test-vectors", "invalid-profile"));
    const anchoredPaths = globJson(path.join(HERE, "test-vectors", "anchored"));
    // An empty fixture set must never silently pass: a runner that checks
    // nothing and reports OK is worse than a runner that errors.
    if (!validPaths.length) {
        problems.push("no fixtures in test-vectors/valid (empty glob)");
    }
    if (!invalidPaths.length) {
        problems.push("no fixtures in test-vectors/invalid (empty glob)");
    }
    if (!profileInvalidPaths.length) {
        problems.push("no fixtures in test-vectors/invalid-profile (empty glob)");
    }
    if (!anchoredPaths.length) {
        problems.push("no fixtures in test-vectors/anchored (empty glob)");
    }
    for (const p of validPaths) {
        const receipt = JSON.parse(fs.readFileSync(p, "utf8"));
        const fails = check(receipt);
        const name = path.basename(p);
        const status = fails.length ? "FAIL" : "PASS";
        console.log("[valid]   " + name + ": " + status +
            (fails.length ? " (" + fails.join("; ") + ")" : ""));
        if (fails.length) {
            problems.push(name + " should conform but does not");
        }
    }
    for (const p of invalidPaths) {
        const receipt = JSON.parse(fs.readFileSync(p, "utf8"));
        const fails = check(receipt);
        const name = path.basename(p);
        const status = fails.length ? "PASS" : "FAIL";
        console.log("[invalid] " + name + ": " + status +
            (fails.length ? " (rejected: " + fails[0] + ")" : " (accepted!)"));
        if (!fails.length) {
            problems.push(name + " should be rejected but was accepted");
        }
    }
    // Profile boundary vectors: core-valid by design (the boundary is real),
    // but MUST fail the reference-producer profile check.
    for (const p of profileInvalidPaths) {
        const receipt = JSON.parse(fs.readFileSync(p, "utf8"));
        const name = path.basename(p);
        const coreFails = check(receipt);
        const profFails = checkReferenceProfile(receipt);
        if (coreFails.length) {
            problems.push(name + " should be core-valid but fails core: " + coreFails[0]);
            console.log("[profile-invalid] " + name + ": FAIL (unexpected core failure: " + coreFails[0] + ")");
        } else if (!profFails.length) {
            problems.push(name + " should be profile-rejected but was accepted");
            console.log("[profile-invalid] " + name + ": FAIL (profile accepted!)");
        } else {
            console.log("[profile-invalid] " + name + ": PASS (core accepted, profile rejected: " + profFails[0] + ")");
        }
    }
    for (const p of anchoredPaths) {
        const receipt = JSON.parse(fs.readFileSync(p, "utf8"));
        const name = path.basename(p);
        const coreFails = check(receipt);
        const tierFails = checkDisinterestedTier(receipt);
        const expectedPass = name === "anchored-valid.json";
        const passed = !coreFails.length && (expectedPass ? !tierFails.length : tierFails.length > 0);
        console.log("[anchored] " + name + ": " + (passed ? "PASS" : "FAIL") +
            (tierFails.length ? " (tier: " + tierFails[0] + ")" : ""));
        if (coreFails.length) problems.push(name + " should be core-valid but fails core");
        if (expectedPass && tierFails.length) problems.push(name + " should pass disinterested tier");
        if (!expectedPass && !tierFails.length) problems.push(name + " should fail disinterested tier");
    }
    problems.push(...checkMerkleVectors());
    problems.push(...checkChainVectors());
    problems.push(...checkChainVectorsV07());
    console.log();
    if (problems.length) {
        console.log("CONFORMANCE FAILED:");
        for (const pr of problems) {
            console.log(" -", pr);
        }
        return 1;
    }
    console.log("CONFORMANCE OK: all vectors behave as expected.");
    return 0;
}

process.exitCode = main();