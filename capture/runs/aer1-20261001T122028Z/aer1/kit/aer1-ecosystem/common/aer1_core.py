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
    if not isinstance(receipt["id"], str) or not UUID_RE.fullmatch(receipt["id"]): failures.append("id is not a UUID v4")
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
