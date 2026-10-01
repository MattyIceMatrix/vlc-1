#!/usr/bin/env python3
"""Independent AER-1 core verifier (Python standard library only)."""
import base64, binascii, calendar, hashlib, json, re
from datetime import datetime

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
RFC3339_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CORE = ("id", "receipt_schema_version", "created_at", "tool", "provenance_class", "canonical_bytes", "output_hash", "verification_status")

def valid_timestamp(value):
    m = RFC3339_RE.fullmatch(value) if isinstance(value, str) else None
    if not m: return False
    year, month, day, hour, minute, second = map(int, m.groups()[:6])
    zone = m.group(7)
    if not 1 <= month <= 12 or not 1 <= day <= calendar.monthrange(year, month)[1]: return False
    if hour > 23 or minute > 59 or second > 59: return False
    if zone != "Z" and (int(zone[1:3]) > 23 or int(zone[4:]) > 59): return False
    return True

def decode_bytes(value):
    if not isinstance(value, str) or len(value) % 4 or not re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", value):
        raise ValueError("canonical_bytes is not valid base64")
    try: raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError): raise ValueError("canonical_bytes is not valid base64")
    try: raw.decode("utf-8")
    except UnicodeDecodeError: raise ValueError("canonical_bytes is not valid UTF-8")
    return raw

def verify(receipt):
    failures = []
    if not isinstance(receipt, dict): return ["receipt is not a JSON object"]
    missing = [k for k in CORE if k not in receipt]
    if missing: return [f"missing required member: {k}" for k in missing]
    if not isinstance(receipt["id"], str) or not UUID_RE.fullmatch(receipt["id"]): failures.append("id is not a lowercase UUID v4")
    if receipt["receipt_schema_version"] != "0.3": failures.append("receipt_schema_version is not 0.3")
    if not valid_timestamp(receipt["created_at"]): failures.append("created_at is not a valid RFC 3339 timestamp")
    tool = receipt["tool"]
    if not isinstance(tool, dict) or any(not isinstance(tool.get(k), str) or not tool[k] for k in ("name", "version", "scope")): failures.append("tool is not an object with name/version/scope strings")
    p = receipt["provenance_class"]
    if not (p == "OBSERVED VIA GATEWAY" or p == "LOGGED BY AGENT" or (isinstance(p, str) and re.fullmatch(r"EXECUTED BY [A-Z0-9][A-Z0-9 ._-]*", p))): failures.append("provenance_class is not a known class")
    raw = None
    try: raw = decode_bytes(receipt["canonical_bytes"])
    except ValueError as exc: failures.append(str(exc))
    if not isinstance(receipt["output_hash"], str) or not HASH_RE.fullmatch(receipt["output_hash"]): failures.append("output_hash is not sha256: plus lowercase hex")
    elif raw is not None:
        expected = "sha256:" + hashlib.sha256(raw).hexdigest()
        if receipt["output_hash"] != expected: failures.append(f"hash mismatch: expected {expected}, got {receipt['output_hash']}")
    if receipt["verification_status"] != "verified": failures.append("verification_status is not verified")
    return failures

def check_profile(receipt):
    try: payload = json.loads(decode_bytes(receipt["canonical_bytes"]))
    except (ValueError, json.JSONDecodeError, KeyError, TypeError): return ["canonical payload is not valid JSON"]
    return [] if isinstance(payload, dict) and "inputs" in payload else ["reference-producer payload omits the 'inputs' member"]

def check_anchor(receipt):
    anchor = receipt.get("anchor") if isinstance(receipt, dict) else None
    if not isinstance(anchor, dict) or set(anchor) != {"log", "leaf_hash", "anchored_at", "proof"}: return ["anchor is missing required members"]
    try: raw = decode_bytes(receipt["canonical_bytes"])
    except ValueError as exc: return [str(exc)]
    expected = "sha256:" + hashlib.sha256(raw).hexdigest()
    failures = []
    if anchor.get("leaf_hash") != expected: failures.append("anchor.leaf_hash does not match canonical_bytes")
    if not valid_timestamp(anchor.get("anchored_at")): failures.append("anchor.anchored_at is not a valid timestamp")
    if not isinstance(anchor.get("proof"), dict): failures.append("anchor.proof is not an object")
    return failures

def merkle_root(receipt_ids):
    if not receipt_ids: return hashlib.sha256(b"").hexdigest()
    level = [hashlib.sha256(x.encode()).digest() for x in receipt_ids]
    while len(level) > 1:
        if len(level) % 2: level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()

def verify_workflow(workflow):
    # Section 8.1 workflow check: steps is a non-empty list of {seq, receipt_id};
    # seq must be exactly 1..n in order (no gaps, no duplicates); no two steps
    # may share a receipt_id; the Section 8.1 Merkle root recomputed over the
    # ordered receipt_id strings must equal the workflow merkle_root member.
    # NOTE: Section 8.2 steps 1-2 need network access (fetching the receipts);
    # they stay the caller's job. Returns failure strings; [] = valid.
    failures = []
    if not isinstance(workflow, dict): return ["workflow is not a JSON object"]
    steps = workflow.get("steps")
    if not isinstance(steps, list) or not steps: return ["steps is not a non-empty list"]
    n = len(steps); seqs = []; ids = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict): failures.append(f"step {i} is not an object"); seqs.append(None); ids.append(None); continue
        q, rid = s.get("seq"), s.get("receipt_id")
        if not isinstance(q, int) or isinstance(q, bool): failures.append(f"step {i} seq is not an integer")
        if not isinstance(rid, str): failures.append(f"step {i} receipt_id is not a string")
        seqs.append(q); ids.append(rid)
    if all(isinstance(q, int) and not isinstance(q, bool) for q in seqs) and seqs != list(range(1, n + 1)):
        failures.append("seq values are not exactly 1..n in order: gap, duplicate, or out of order")
    if all(isinstance(r, str) for r in ids):
        seen = set()
        for r in ids:
            if r in seen: failures.append(f"8.2 duplicate receipt_id: {r}"); break
            seen.add(r)
    mr = workflow.get("merkle_root")
    if not isinstance(mr, str): failures.append("merkle_root is not a string")
    elif all(isinstance(r, str) for r in ids):
        expected = merkle_root(ids)
        if mr != expected: failures.append(f"merkle_root mismatch: expected {expected}, got {mr}")
    return failures

GENESIS_PREV = "0" * 64

def strict_b64(value):
    if not isinstance(value, str) or len(value) % 4 or not re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", value):
        raise ValueError("canonical_bytes is not valid base64")
    try: return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError): raise ValueError("canonical_bytes is not valid base64")

def verify_chain(timeline):
    # Pinned chain construction: entry digest = SHA-256 over the raw bytes of
    # base64-decoded canonical_bytes (strict decode, fail closed); entry 0
    # prev_digest must be exactly 64 zeros; each later entry's prev_digest must
    # equal the lowercase hex digest of the previous entry; the last entry must
    # carry close set to boolean true. Chain mechanics only: full receipt
    # validation is verify()'s job, this stops at the chain.
    failures = []
    if not isinstance(timeline, list) or not timeline: return ["timeline is not a non-empty list"]
    prev = None
    for i, e in enumerate(timeline):
        if not isinstance(e, dict): failures.append(f"entry {i} is not an object"); prev = None; continue
        pd = e.get("prev_digest")
        if i == 0:
            if pd != GENESIS_PREV: failures.append("entry 0 prev_digest is not 64 zeros")
        elif not isinstance(pd, str): failures.append(f"entry {i} prev_digest is not a string")
        elif pd != prev: failures.append(f"entry {i} prev_digest does not match digest of entry {i - 1}")
        try: raw = strict_b64(e["canonical_bytes"])
        except (ValueError, KeyError, TypeError): failures.append(f"entry {i} canonical_bytes is not valid base64"); raw = None
        prev = hashlib.sha256(raw).hexdigest() if raw is not None else None
    last = timeline[-1]
    if not isinstance(last, dict) or last.get("close") is not True: failures.append("last entry close is not boolean true")
    return failures

def chain_entry_digest_v07(entry):
    # -07 hardened digest: SHA-256 over the UTF-8 bytes of the canonical
    # JSON object {prev_digest, seq, job_id, close, id, tool,
    # provenance_class, output_hash} (keys sorted, no whitespace), where
    # output_hash = hex SHA-256 of the base64-decoded canonical_bytes.
    # seq is normalized to int so 1.0 hashes as 1 (json.dumps writes 1.0).
    raw = strict_b64(entry["canonical_bytes"])
    output_hash = hashlib.sha256(raw).hexdigest()
    seq = entry["seq"]
    if isinstance(seq, float) and seq.is_integer(): seq = int(seq)
    payload = {"prev_digest": entry["prev_digest"], "seq": seq,
               "job_id": entry["job_id"], "close": entry.get("close", False),
               "id": entry["id"], "tool": entry["tool"],
               "provenance_class": entry["provenance_class"],
               "output_hash": output_hash}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()

def verify_chain_v07(timeline):
    # -07 hardened chain mechanics: digest binds prev_digest, seq, job_id,
    # close, id, tool, provenance_class, output_hash. Entry 0 needs the
    # 64-zero genesis digest and seq 1; seq contiguous from 1; one job_id
    # per chain; close boolean, true only on the last entry; links must
    # match recomputed digests; strict base64, fail closed. Honest limit:
    # truncation with re-linking is not detectable by chain mechanics
    # alone; it needs an anchored endpoint.
    failures = []
    if not isinstance(timeline, list) or not timeline: return ["timeline is not a non-empty list"]
    job = None; prev = None
    for i, e in enumerate(timeline):
        if not isinstance(e, dict): return [f"entry {i} is not an object"]
        try: strict_b64(e["canonical_bytes"])
        except (ValueError, KeyError, TypeError): return [f"entry {i} canonical_bytes is not valid base64"]
        for m in ("id", "tool", "provenance_class", "job_id", "prev_digest"):
            if not isinstance(e.get(m), str) or not e[m]: return [f"entry {i} missing {m}"]
        seq = e.get("seq")
        if isinstance(seq, bool): return [f"entry {i} seq is not an integer"]
        if isinstance(seq, float):
            if not seq.is_integer(): return [f"entry {i} seq is not an integer"]
            e["seq"] = int(seq); seq = e["seq"]
        elif not isinstance(seq, int): return [f"entry {i} seq is not an integer"]
        if seq != i + 1: failures.append(f"entry {i} seq {seq} breaks contiguity (expected {i + 1})")
        if job is None: job = e["job_id"]
        elif e["job_id"] != job: failures.append(f"entry {i} job_id mixes jobs")
        pd = e["prev_digest"]
        if i == 0:
            if pd != GENESIS_PREV: failures.append("entry 0 prev_digest is not 64 zeros")
        elif pd != prev: failures.append(f"entry {i} prev_digest does not match digest of entry {i - 1}")
        if "close" in e and not isinstance(e["close"], bool): failures.append(f"entry {i} close is not a boolean")
        elif i < len(timeline) - 1 and e.get("close") is True: failures.append(f"entry {i} carries close:true before the last entry")
        prev = chain_entry_digest_v07(e)
    last = timeline[-1]
    if not isinstance(last, dict) or last.get("close") is not True: failures.append("last entry does not carry close: true")
    return failures
