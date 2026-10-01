#!/usr/bin/env python3
"""AER-1 conformance runner.

Checks every vector in test-vectors/ against the core rules of
AER-1 (draft-zambo-aer1-02, Sections 3-6):

  valid/   - every file MUST conform (schema shape + hash recomputation)
  invalid/ - every file MUST fail at least one check, with a reason

Standard library only. Exit 0 when all expectations hold, 1 otherwise.

v1.2.0: strict UTF-8 decode of canonical_bytes (fail closed), calendar-valid
RFC 3339 timestamps (shape alone is not enough), and a hard error when a
fixture directory matches zero files instead of a silent pass.

v1.3.0: reference-producer profile. check_reference_profile() pins the
payload convention of the reference producer (canonical payload is a JSON
object carrying the 'inputs' member). This is a PRODUCER CONVENTION, not an
interop requirement: core verifiers MUST NOT require it. Vectors under
test-vectors/invalid-profile/ MUST pass the core check and MUST fail the
profile check, proving the boundary fails closed.

v1.4.0: offline workflow verification verify_workflow() (Section 8.2 steps
3-4; steps 1-2 need network and stay the caller's job), including the MM-1
no-duplicate-receipt_id rule. check_merkle_vectors() honors the optional
expected_workflow_verdict / rejected_by vector fields. Section 7 chain
validation verify_chain() with the pinned prev_digest construction and the
close:true suffix-truncation kill, plus the check_chain_vectors()
regression gate over chain-vectors.json.

-07 (draft): hardened chain construction chain_entry_digest_v07() /
verify_chain_v07() binding prev_digest, seq, job_id, close, id, tool,
provenance_class, and output_hash, gated by check_chain_vectors_v07()
over chain-vectors-v07.json. The -06 verify_chain() is kept unchanged
for historical chains; -06 chains do not verify under -07 rules.
"""
import base64
import binascii
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = ["id", "receipt_schema_version", "created_at", "tool",
        "provenance_class", "canonical_bytes", "output_hash",
        "verification_status"]
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                     r"[0-9a-f]{4}-[0-9a-f]{12}$")
RFC3339_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:"
                         r"[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PROV_RE = re.compile(r"^(EXECUTED BY [A-Z0-9][A-Z0-9 ._-]*|"
                     r"OBSERVED VIA GATEWAY|LOGGED BY AGENT)$")
B64_RE = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")


def check(receipt):
    """Return a list of failure reasons; empty means conformant."""
    failures = []
    if not isinstance(receipt, dict):
        return ["receipt is not a JSON object"]
    for field in CORE:
        if field not in receipt:
            failures.append(f"missing required member: {field}")
    if failures:
        return failures
    if not isinstance(receipt["id"], str) or not UUID_RE.match(receipt["id"]):
        failures.append("id is not a lowercase UUID")
    if (not isinstance(receipt["receipt_schema_version"], str)
            or not receipt["receipt_schema_version"]):
        failures.append("receipt_schema_version is not a non-empty string")
    if not isinstance(receipt["created_at"], str):
        failures.append("created_at is not a string")
    elif not RFC3339_RE.match(receipt["created_at"]):
        failures.append("created_at is not RFC 3339")
    else:
        # Shape alone is not enough: "2026-02-30T09:00:00.000Z" matches the
        # RFC 3339 pattern but is not a real calendar date. Fail closed.
        try:
            datetime.fromisoformat(
                receipt["created_at"].replace("Z", "+00:00"))
        except ValueError:
            failures.append("created_at is not a valid calendar date/time")
    tool = receipt["tool"]
    if not isinstance(tool, dict) or not all(
            isinstance(tool.get(k), str) and tool[k]
            for k in ("name", "version", "scope")):
        failures.append("tool is not an object with name/version/scope strings")
    if (not isinstance(receipt["provenance_class"], str)
            or not PROV_RE.match(receipt["provenance_class"])):
        failures.append("provenance_class is not a known class")
    cb = receipt["canonical_bytes"]
    raw = None
    if not isinstance(cb, str) or not B64_RE.match(cb):
        failures.append("canonical_bytes is not valid base64")
    else:
        try:
            raw = base64.b64decode(cb, validate=True)
        except (binascii.Error, ValueError):
            failures.append("canonical_bytes is not valid base64")
        else:
            # The commitment is over the exact UTF-8 byte sequence
            # (draft Sections 3-4). A decodable base64 payload that is not
            # valid UTF-8 (e.g. b"\xff") fails closed here.
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                failures.append("canonical_bytes is not valid UTF-8")
                raw = None
    oh = receipt["output_hash"]
    if not isinstance(oh, str) or not HASH_RE.match(oh):
        failures.append("output_hash is not sha256: + lowercase hex digest")
    elif raw is not None:
        want = "sha256:" + hashlib.sha256(raw).hexdigest()
        if oh != want:
            failures.append("output_hash does not match sha256(canonical_bytes)")
    if receipt["verification_status"] != "verified":
        failures.append("verification_status is not verified")
    return failures


def check_reference_profile(receipt):
    """Reference-producer profile check. Returns failure reasons; [] = pass.

    The reference producer commits to canonical payloads shaped as a JSON
    object carrying the 'inputs' member (alongside 'tool'/'outputs'). A
    receipt whose payload omits 'inputs' is still core-conformant and MUST be
    accepted by interop verifiers, but it is NOT reference-producer
    conformant. Fail closed at every decode step. Regression rule for the
    missing-inputs finding (independent review, 2026-09-27).
    """
    if not isinstance(receipt, dict):
        return ["receipt is not a JSON object"]
    cb = receipt.get("canonical_bytes")
    if not isinstance(cb, str):
        return ["canonical_bytes is not a string"]
    try:
        raw = base64.b64decode(cb, validate=True)
    except (binascii.Error, ValueError):
        return ["canonical_bytes is not valid base64"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ["canonical_bytes is not valid UTF-8"]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ["canonical payload is not JSON"]
    if not isinstance(payload, dict):
        return ["canonical payload is not a JSON object"]
    if "inputs" not in payload:
        return ["reference-producer payload omits the 'inputs' member"]
    return []


def check_disinterested_tier(receipt):
    """Check the optional transparency-log anchor profile."""
    failures = []
    anchor = receipt.get("anchor") if isinstance(receipt, dict) else None
    if not isinstance(anchor, dict):
        return ["anchor is not an object"]
    if set(anchor) != {"log", "leaf_hash", "anchored_at", "proof"}:
        failures.append("anchor has members other than log/leaf_hash/anchored_at/proof")
    if not isinstance(anchor.get("log"), str) or not anchor["log"]:
        failures.append("anchor.log is not a non-empty string")
    leaf = anchor.get("leaf_hash")
    if not isinstance(leaf, str) or not HASH_RE.match(leaf):
        failures.append("anchor.leaf_hash is not sha256: + lowercase hex digest")
    else:
        cb = receipt.get("canonical_bytes")
        raw = None
        if not isinstance(cb, str) or not B64_RE.match(cb):
            failures.append("canonical_bytes is not valid base64")
        else:
            try:
                raw = base64.b64decode(cb, validate=True)
                raw.decode("utf-8")
            except (binascii.Error, ValueError, UnicodeDecodeError):
                failures.append("canonical_bytes is not valid UTF-8 base64")
        if raw is not None:
            want = "sha256:" + hashlib.sha256(raw).hexdigest()
            if leaf != want:
                failures.append("anchor.leaf_hash does not match canonical_bytes")
    anchored_at = anchor.get("anchored_at")
    if not isinstance(anchored_at, str) or not RFC3339_RE.match(anchored_at):
        failures.append("anchor.anchored_at is not RFC 3339")
    else:
        try:
            datetime.fromisoformat(anchored_at.replace("Z", "+00:00"))
        except ValueError:
            failures.append("anchor.anchored_at is not a valid calendar date/time")
    if not isinstance(anchor.get("proof"), dict):
        failures.append("anchor.proof is not an object")
    return failures


def _merkle_root_canonical(receipt_ids):
    """Section 8.1 normative construction: leaf = SHA-256 over the UTF-8
    bytes of receipt_id; internal node = SHA-256 over raw 32-byte left ||
    raw 32-byte right; odd trailing node duplicated."""
    if not receipt_ids:
        return hashlib.sha256(b"").hexdigest()
    level = [hashlib.sha256(rid.encode("utf-8")).digest()
             for rid in receipt_ids]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                for i in range(0, len(level), 2)]
    return level[0].hex()


def verify_workflow(workflow):
    """Section 8.2 steps 3-4: offline workflow verification.

    Returns a list of failure reasons; empty means valid.

    Steps 1-2 (fetch each step's receipt over the network and confirm each
    receipt exists and is addressed) need network access and STAY THE
    CALLER'S JOB: this function verifies only the offline mechanics, in
    order: workflow is an object; steps is a non-empty list; every step
    carries an integer seq and a string receipt_id; seq values are exactly
    1..n in order with no gaps and no duplicate seq; NO two steps share the
    same receipt_id value (the MM-1 rule); the workflow's merkle_root
    equals the recomputed Section 8.1 root over the ordered receipt_id
    strings.
    """
    if not isinstance(workflow, dict):
        return ["workflow is not a JSON object"]
    steps = workflow.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["workflow steps is not a non-empty list"]
    failures = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            failures.append(f"step {i + 1} is not an object")
            continue
        seq = step.get("seq")
        if isinstance(seq, bool) or not (
            isinstance(seq, int)
            or (isinstance(seq, float) and seq.is_integer())
        ):
            failures.append(f"step {i + 1} seq is not an integer")
        rid = step.get("receipt_id")
        if not isinstance(rid, str):
            failures.append(f"step {i + 1} receipt_id is not a string")
    if failures:
        return failures
    n = len(steps)
    for i, step in enumerate(steps):
        if step["seq"] != i + 1:
            failures.append(f"step seq values are not 1..{n} in order "
                            f"(index {i} carries seq {step['seq']})")
            break
    seen = set()
    for step in steps:
        rid = step["receipt_id"]
        if rid in seen:
            failures.append(f"duplicate receipt_id: {rid}")
            break
        seen.add(rid)
    root = _merkle_root_canonical([step["receipt_id"] for step in steps])
    mr = workflow.get("merkle_root")
    if not isinstance(mr, str) or mr != root:
        failures.append("merkle_root does not match the recomputed "
                        "Section 8.1 root")
    return failures


def check_merkle_vectors():
    """Regression gate for the Section 8.1 Merkle construction, locked to
    merkle-vectors.json. Returns a list of problem strings (empty = green)."""
    problems = []
    path = HERE / "merkle-vectors.json"
    if not path.exists():
        return ["merkle-vectors.json is missing (no silent pass)"]
    corpus = json.loads(path.read_text())
    vectors = corpus.get("vectors", [])
    if not vectors:
        return ["merkle-vectors.json contains no vectors (no silent pass)"]
    for v in vectors:
        name = v.get("name", "?")
        if "receipt_ids" in v:
            got = _merkle_root_canonical(v["receipt_ids"])
            ok = got == v["expected_root"]
            print(f"[merkle]  {name}: {'PASS' if ok else 'FAIL'}"
                  + ("" if ok else f" (got {got})"))
            if not ok:
                problems.append(f"merkle vector {name}: expected "
                                f"{v['expected_root']}, got {got}")
        elif "leaves" in v:
            # Legacy-construction vector: recompute from the documented
            # preimages and require the historical root, never the canonical.
            leaves = [hashlib.sha256(l["preimage"].encode("utf-8")).digest()
                      for l in sorted(v["leaves"], key=lambda x: x["seq"])]
            lvl = list(leaves)
            while len(lvl) > 1:
                if len(lvl) % 2:
                    lvl.append(lvl[-1])
                lvl = [hashlib.sha256(lvl[i] + lvl[i + 1]).digest()
                       for i in range(0, len(lvl), 2)]
            got = lvl[0].hex() if lvl else hashlib.sha256(b"").hexdigest()
            ok = (got == v["expected_root"]
                  and got != v.get("must_not_equal"))
            print(f"[merkle]  {name}: {'PASS' if ok else 'FAIL'}"
                  + ("" if ok else f" (got {got})"))
            if not ok:
                problems.append(f"merkle vector {name}: legacy root mismatch "
                                f"(got {got})")
        if v.get("must_not_equal") and "receipt_ids" in v:
            if v["expected_root"] == v["must_not_equal"]:
                problems.append(f"merkle vector {name}: root must differ from "
                                f"the canonical/legacy counterpart")
        # Workflow-verdict extension: a vector may carry
        # expected_workflow_verdict ("valid" or "invalid"). Build the
        # workflow exactly as specified and require the verify_workflow()
        # checks to agree with the expected verdict. The root-recompute
        # check above STILL runs: a duplicate vector's root MUST recompute
        # to expected_root even though its workflow verdict is invalid
        # (the root matches but the workflow is rejected, which is the
        # point of the MM-1 rule).
        verdict_field = v.get("expected_workflow_verdict")
        if verdict_field is not None:
            if "receipt_ids" not in v:
                problems.append(f"merkle vector {name}: "
                                f"expected_workflow_verdict needs receipt_ids "
                                f"(no silent pass)")
                print(f"[merkle-workflow] {name}: FAIL (no receipt_ids)")
                continue
            wf = {"steps": [{"seq": i + 1, "receipt_id": rid}
                            for i, rid in enumerate(v["receipt_ids"])],
                  "merkle_root": v["expected_root"]}
            wf_fails = verify_workflow(wf)
            verdict = "valid" if not wf_fails else "invalid"
            ok = verdict == verdict_field
            if ok and verdict == "invalid":
                rb = v.get("rejected_by")
                if not (isinstance(rb, str)
                        and any(rb in f for f in wf_fails)):
                    ok = False
            print(f"[merkle-workflow] {name}: {'PASS' if ok else 'FAIL'}"
                  + ("" if ok else f" (verdict {verdict})"))
            if not ok:
                problems.append(f"merkle vector {name}: expected workflow "
                                f"verdict {verdict_field}, got {verdict}")
    return problems


def verify_chain(timeline):
    """Section 7 chain mechanics. Returns failure reasons; [] = valid.

    Pinned construction, implemented exactly: entry digest = SHA-256 over
    the raw bytes obtained by base64-decoding the entry's canonical_bytes
    member (strict decode, fail closed on bad base64); entry 0's
    prev_digest MUST be exactly 64 zero characters; each later entry's
    prev_digest MUST be a string equal to the lowercase hex digest of the
    previous entry (mismatch names the entry index); the LAST entry MUST
    carry close: true (boolean true), anything else is a failure (this is
    the suffix-truncation kill); an empty timeline is a failure.

    Chain mechanics only: entries are NOT required to be full valid
    receipts here. Per-entry receipt verification (schema, hashes) is the
    caller's job, not this function's.
    """
    if not isinstance(timeline, list) or not timeline:
        return ["timeline is not a non-empty list"]
    failures = []
    prev = None
    for i, entry in enumerate(timeline):
        if not isinstance(entry, dict):
            failures.append(f"entry {i} is not an object")
            break
        cb = entry.get("canonical_bytes")
        if not isinstance(cb, str) or not B64_RE.match(cb):
            failures.append(f"entry {i} canonical_bytes is not valid base64")
            break
        try:
            raw = base64.b64decode(cb, validate=True)
        except (binascii.Error, ValueError):
            failures.append(f"entry {i} canonical_bytes is not valid base64")
            break
        digest = hashlib.sha256(raw).hexdigest()
        pd = entry.get("prev_digest")
        if i == 0:
            if not isinstance(pd, str) or pd != "0" * 64:
                failures.append("entry 0 prev_digest is not 64 zero characters")
        elif not isinstance(pd, str) or pd != prev:
            failures.append(f"entry {i} prev_digest does not match the digest "
                            f"of entry {i - 1}")
        prev = digest
    # The suffix-truncation kill: the chain is not closed without it.
    last = timeline[-1]
    if isinstance(last, dict) and last.get("close") is not True:
        failures.append("last entry does not carry close: true")
    return failures


def chain_entry_digest_v07(entry):
    """Section 7 (-07) entry digest. Returns lowercase hex SHA-256.

    digest_i = SHA-256 over the UTF-8 bytes of the canonical JSON object
    {prev_digest, seq, job_id, close, id, tool, provenance_class,
    output_hash} with keys sorted by Unicode code point and no
    whitespace, where output_hash = lowercase hex SHA-256 of the
    base64-decoded canonical_bytes. A missing close member digests as
    false. Raises ValueError on bad base64 (fail closed).
    """
    raw = base64.b64decode(entry["canonical_bytes"], validate=True)
    output_hash = hashlib.sha256(raw).hexdigest()
    seq = entry["seq"]
    if isinstance(seq, float) and seq.is_integer():
        seq = int(seq)
    payload = {
        "prev_digest": entry["prev_digest"],
        "seq": seq,
        "job_id": entry["job_id"],
        "close": entry.get("close", False),
        "id": entry["id"],
        "tool": entry["tool"],
        "provenance_class": entry["provenance_class"],
        "output_hash": output_hash,
    }
    blob = json.dumps(payload, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def verify_chain_v07(timeline):
    """Section 7 chain mechanics, -07 hardened construction. Returns
    failure reasons; [] = valid.

    Hardened construction, implemented exactly: the entry digest binds
    prev_digest, seq, job_id, close, id, tool, provenance_class, and
    output_hash (SHA-256 hex of the base64-decoded canonical_bytes), so
    relabeling an entry's metadata, moving close:true, or splicing
    entries across jobs breaks the links. Entry 0's prev_digest MUST be
    exactly 64 zero characters AND seq MUST be 1; seq MUST be contiguous
    from 1; every entry MUST carry the same job_id; close MUST be a
    boolean and MUST be true only on the last entry; each entry's
    prev_digest MUST equal the recomputed digest of the previous entry;
    canonical_bytes MUST be strict-valid base64 (fail closed).

    Honest limit, stated not hidden: a prefix or suffix of a valid chain
    re-linked end to end IS a valid chain, so truncation of either end by
    an attacker who rebuilds the links is NOT detectable by chain
    mechanics alone. Truncation resistance needs an anchored endpoint
    (witness/timestamp the head, or bind the step list or count in the
    workflow manifest). Chain mechanics only: entries are NOT required
    to be full valid receipts here.
    """
    if not isinstance(timeline, list) or not timeline:
        return ["timeline is not a non-empty list"]
    failures = []
    job = None
    prev = None
    for i, entry in enumerate(timeline):
        if not isinstance(entry, dict):
            return ["entry %d is not an object" % i]
        cb = entry.get("canonical_bytes")
        if not isinstance(cb, str) or not B64_RE.match(cb):
            return ["entry %d canonical_bytes is not valid base64" % i]
        try:
            base64.b64decode(cb, validate=True)
        except (binascii.Error, ValueError):
            return ["entry %d canonical_bytes is not valid base64" % i]
        for m in ("id", "tool", "provenance_class", "job_id", "prev_digest"):
            if not isinstance(entry.get(m), str) or not entry[m]:
                return ["entry %d missing %s" % (i, m)]
        seq = entry.get("seq")
        if isinstance(seq, bool) or not (
            isinstance(seq, int)
            or (isinstance(seq, float) and seq.is_integer())
        ):
            return ["entry %d seq is not an integer" % i]
        seq = int(seq)
        if seq != i + 1:
            failures.append("entry %d seq %d breaks contiguity (expected %d)"
                            % (i, seq, i + 1))
        if job is None:
            job = entry["job_id"]
        elif entry["job_id"] != job:
            failures.append("entry %d job_id mixes jobs" % i)
        pd = entry["prev_digest"]
        if i == 0:
            if pd != "0" * 64:
                failures.append("entry 0 prev_digest is not 64 zero "
                                "characters")
        elif pd != prev:
            failures.append("entry %d prev_digest does not match the digest "
                            "of entry %d" % (i, i - 1))
        if "close" in entry and not isinstance(entry["close"], bool):
            failures.append("entry %d close is not a boolean" % i)
        elif i < len(timeline) - 1 and entry.get("close") is True:
            failures.append("entry %d carries close:true before the last "
                            "entry" % i)
        prev = chain_entry_digest_v07(entry)
    last = timeline[-1]
    if not isinstance(last, dict) or last.get("close") is not True:
        failures.append("last entry does not carry close: true")
    return failures


def check_chain_vectors():
    """Regression gate for the Section 7 chain construction, locked to
    chain-vectors.json. Returns a list of problem strings (empty = green).
    Fail closed: missing file, empty vector list, or an unknown
    expected_verdict are problems, never silent passes."""
    problems = []
    path = HERE / "chain-vectors.json"
    if not path.exists():
        return ["chain-vectors.json is missing (no silent pass)"]
    corpus = json.loads(path.read_text())
    vectors = corpus.get("vectors", [])
    if not vectors:
        return ["chain-vectors.json contains no vectors (no silent pass)"]
    for v in vectors:
        name = v.get("name", "?")
        expected = v.get("expected_verdict")
        if expected not in ("valid", "invalid"):
            problems.append(f"chain vector {name}: unknown expected_verdict "
                            f"{expected!r} (no silent pass)")
            print(f"[chain]  {name}: FAIL (unknown expected_verdict)")
            continue
        # The corpus names the timeline member "timeline". Accept "entries"
        # as a fallback alias. Fail closed: neither key present yields
        # None, which verify_chain rejects, so a "valid" vector can
        # never silently pass on a missing member.
        tl = v.get("timeline")
        if tl is None:
            tl = v.get("entries")
        fails = verify_chain(tl)
        ok = (not fails) == (expected == "valid")
        print(f"[chain]  {name}: {'PASS' if ok else 'FAIL'}"
              + ("" if ok else f" ({'; '.join(fails)})"))
        if not ok:
            problems.append(f"chain vector {name}: expected {expected}, got "
                            f"{'valid' if not fails else 'invalid'}")
    return problems


def check_chain_vectors_v07():
    """Regression gate for the -07 hardened Section 7 chain construction,
    locked to chain-vectors-v07.json. Mirrors check_chain_vectors() but
    runs verify_chain_v07(). Fail closed: missing file, empty vector
    list, or an unknown expected_verdict are problems, never silent
    passes."""
    problems = []
    path = HERE / "chain-vectors-v07.json"
    if not path.exists():
        return ["chain-vectors-v07.json is missing (no silent pass)"]
    corpus = json.loads(path.read_text())
    vectors = corpus.get("vectors", [])
    if not vectors:
        return ["chain-vectors-v07.json contains no vectors (no silent pass)"]
    for v in vectors:
        name = v.get("name", "?")
        expected = v.get("expected_verdict")
        if expected not in ("valid", "invalid"):
            problems.append(f"chain-v07 vector {name}: unknown "
                            f"expected_verdict {expected!r} (no silent pass)")
            print(f"[chain-v07] {name}: FAIL (unknown expected_verdict)")
            continue
        tl = v.get("timeline")
        if tl is None:
            tl = v.get("entries")
        fails = verify_chain_v07(tl)
        ok = (not fails) == (expected == "valid")
        print(f"[chain-v07] {name}: {'PASS' if ok else 'FAIL'}"
              + ("" if ok else f" ({'; '.join(fails)})"))
        if not ok:
            problems.append(f"chain-v07 vector {name}: expected {expected}, "
                            f"got {'valid' if not fails else 'invalid'}")
    return problems


def main():
    problems = []
    valid_paths = sorted((HERE / "test-vectors" / "valid").glob("*.json"))
    invalid_paths = sorted((HERE / "test-vectors" / "invalid").glob("*.json"))
    profile_invalid_paths = sorted(
        (HERE / "test-vectors" / "invalid-profile").glob("*.json"))
    anchored_paths = sorted((HERE / "test-vectors" / "anchored").glob("*.json"))
    # An empty fixture set must never silently pass: a runner that checks
    # nothing and reports OK is worse than a runner that errors.
    if not valid_paths:
        problems.append("no fixtures in test-vectors/valid (empty glob)")
    if not invalid_paths:
        problems.append("no fixtures in test-vectors/invalid (empty glob)")
    if not profile_invalid_paths:
        problems.append("no fixtures in test-vectors/invalid-profile (empty glob)")
    if not anchored_paths:
        problems.append("no fixtures in test-vectors/anchored (empty glob)")
    for path in valid_paths:
        receipt = json.loads(path.read_text())
        fails = check(receipt)
        status = "PASS" if not fails else "FAIL"
        print(f"[valid]   {path.name}: {status}"
              + ("" if not fails else f" ({'; '.join(fails)})"))
        if fails:
            problems.append(f"{path.name} should conform but does not")
    for path in invalid_paths:
        receipt = json.loads(path.read_text())
        fails = check(receipt)
        status = "PASS" if fails else "FAIL"
        print(f"[invalid] {path.name}: {status}"
              + (f" (rejected: {fails[0]})" if fails else " (accepted!)"))
        if not fails:
            problems.append(f"{path.name} should be rejected but was accepted")
    # Profile boundary vectors: core-valid by design (the boundary is real),
    # but MUST fail the reference-producer profile check.
    for path in profile_invalid_paths:
        receipt = json.loads(path.read_text())
        core_fails = check(receipt)
        prof_fails = check_reference_profile(receipt)
        if core_fails:
            problems.append(
                f"{path.name} should be core-valid but fails core: "
                f"{core_fails[0]}")
            print(f"[profile-invalid] {path.name}: FAIL "
                  f"(unexpected core failure: {core_fails[0]})")
        elif not prof_fails:
            problems.append(f"{path.name} should be profile-rejected "
                            f"but was accepted")
            print(f"[profile-invalid] {path.name}: FAIL (profile accepted!)")
        else:
            print(f"[profile-invalid] {path.name}: PASS "
                  f"(core accepted, profile rejected: {prof_fails[0]})")
    for path in anchored_paths:
        receipt = json.loads(path.read_text())
        core_fails = check(receipt)
        tier_fails = check_disinterested_tier(receipt)
        expected_pass = path.name == "anchored-valid.json"
        passed = not core_fails and (not tier_fails if expected_pass else bool(tier_fails))
        status = "PASS" if passed else "FAIL"
        detail = ("" if not tier_fails else f" (tier: {tier_fails[0]})")
        print(f"[anchored] {path.name}: {status}{detail}")
        if core_fails:
            problems.append(f"{path.name} should be core-valid but fails core")
        if expected_pass and tier_fails:
            problems.append(f"{path.name} should pass disinterested tier")
        if not expected_pass and not tier_fails:
            problems.append(f"{path.name} should fail disinterested tier")
    problems.extend(check_merkle_vectors())
    problems.extend(check_chain_vectors())
    problems.extend(check_chain_vectors_v07())
    print()
    if problems:
        print("CONFORMANCE FAILED:")
        for p in problems:
            print(" -", p)
        return 1
    print("CONFORMANCE OK: all vectors behave as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())