#!/usr/bin/env python3
"""Cross-test kit for draft-sharif-agent-audit-trail-06 (AAT).

    python3 crosstest/aat/harness.py

Builds AAT sessions that satisfy every MUST of sections 3.1, 6.1, 6.3, 8.1
and 8.3 of the -06 draft, then probes what the rules do and do not
establish. Same discipline as the AER-1 cross-test (THIRD-PARTY.md): the
draft's own text is the oracle; every claim below is a runnable assertion.

Probes:
  P1  numeric interop: the same record hashed by two reasonable RFC 8785
      implementations (ECMAScript JSON.stringify via node, and the common
      Python json.dumps(sort_keys=...) approximation) -- JSON number forms
      (1.0, -0.0, ints past 2^53) produce DIFFERENT prev_hash values.
  P2  close-record binding: the close record's own content is covered by
      neither the chain (nothing hashes the last record) nor session_hash
      (which concatenates prev_hash(1..N), i.e. records 0..N-1) -- so the
      SHOULD-level record_count in the close can be altered after the fact
      while every MUST still verifies. (The same class VLC-1 filed as
      EXT-022 against its own first end-marker design.)
  P3  completeness: delete an interior record and reseal the chain and
      session_hash -- with the optional fields absent (sequence_number,
      record_count, heartbeats, nonce are all optional/SHOULD), the
      9-record session passes every MUST exactly as the 10-record one did.
  P4  verifier MUSTs hold on the honest session (control: our faithful
      verifier accepts what the draft accepts).

Requires node (for exact JCS via JSON.stringify). Stdlib otherwise.
Blast radius: this directory only (writes session files beside itself).
"""
import hashlib
import json
import os
import subprocess
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))


def jcs_node(obj):
    """Exact RFC 8785 for the JSON subset JSON.stringify serializes:
    ECMAScript's serializer IS the JCS number formatter."""
    r = subprocess.run(
        ["node", "-e",
         "const c=(o)=>{if(o===null||typeof o!=='object')return JSON.stringify(o);"
         "if(Array.isArray(o))return '['+o.map(c).join(',')+']';"
         "return '{'+Object.keys(o).sort().map(k=>JSON.stringify(k)+':'+c(o[k])).join(',')+'}'};"
         "process.stdout.write(c(JSON.parse(require('fs').readFileSync(0,'utf8'))))"],
        input=json.dumps(obj).encode(), capture_output=True, check=True)
    return r.stdout


def jcs_pythonish(obj):
    """What a typical Python implementer writes for 'JCS': sorted keys,
    tight separators, ensure_ascii off. Correct for ints and strings,
    WRONG for 1.0 (emits '1.0' where JCS emits '1') and -0.0."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rec(session, i, prev, action_type="tool_call", extra=None):
    r = {"record_id": str(uuid.UUID(int=i + 1)), "timestamp": f"2026-11-28T06:{i:02d}:00+00:00",
         "agent_id": "urn:example:agent:crosstest", "agent_version": "1.0.0",
         "session_id": session, "action_type": action_type,
         "action_detail": extra or {"tool": "search", "args_fingerprint": sha(str(i).encode())},
         "outcome": "success", "trust_level": "L2",
         "parent_record_id": None if prev is None else prev["record_id"],
         "prev_hash": None if prev is None else sha(jcs_node(prev)),
         "record_phase": "post_execution"}
    return r


def build_session(n_actions, canon=jcs_node):
    sid = str(uuid.UUID(int=999))
    recs = []
    g = rec(sid, 0, None, "lifecycle", {"event": "session_start"})
    g["record_phase"] = "concurrent"
    recs.append(g)
    for i in range(1, n_actions + 1):
        recs.append(rec(sid, i, recs[-1]))
    chain_hashes = [bytes.fromhex(r["prev_hash"]) for r in recs[1:]]
    close = rec(sid, n_actions + 1, recs[-1], "lifecycle",
                {"event": "session_end",
                 "session_hash": sha(b"".join(chain_hashes + [bytes.fromhex(sha(jcs_node(recs[-1])))]))})
    close["action_detail"]["record_count"] = len(recs) + 1
    recs.append(close)
    return recs


def verify_musts(recs):
    """A faithful verifier of the draft's MUSTs: genesis shape, chain,
    close presence and session_hash."""
    g = recs[0]
    if g["prev_hash"] is not None or g["parent_record_id"] is not None:
        return "genesis not anchored to null"
    for a, b in zip(recs, recs[1:]):
        if b["prev_hash"] != sha(jcs_node(a)):
            return f"chain break at {b['record_id']}"
        if b["parent_record_id"] != a["record_id"]:
            return f"parent link break at {b['record_id']}"
    last = recs[-1]
    if last.get("action_type") != "lifecycle" or \
            last["action_detail"].get("event") != "session_end":
        return "no close record: completeness inconclusive (6.3 step 10)"
    chain_hashes = [bytes.fromhex(r["prev_hash"]) for r in recs[1:]]
    want = sha(b"".join(chain_hashes))
    if last["action_detail"].get("session_hash") != want:
        return "session_hash mismatch"
    return None


def reseal(recs):
    """Recompute every prev_hash, parent link and the session_hash."""
    for i in range(1, len(recs)):
        recs[i]["prev_hash"] = sha(jcs_node(recs[i - 1]))
        recs[i]["parent_record_id"] = recs[i - 1]["record_id"]
    chain_hashes = [bytes.fromhex(r["prev_hash"]) for r in recs[1:]]
    recs[-1]["action_detail"]["session_hash"] = sha(b"".join(chain_hashes))
    # session_hash changed the close's content, but nothing hashes the close
    return recs


def main():
    # P4 control: honest session passes every MUST
    honest = build_session(8)
    assert verify_musts(honest) is None, verify_musts(honest)
    with open(os.path.join(HERE, "session-honest.jsonl"), "w") as f:
        for r in honest:
            f.write(json.dumps(r) + "\n")
    print("P4 control:   honest 10-record session passes every MUST")

    # P1: numeric interop divergence
    probe = dict(honest[1])
    probe["action_detail"] = {"tool": "calc", "value": 1.0}
    h_node, h_py = sha(jcs_node(probe)), sha(jcs_pythonish(probe))
    assert h_node != h_py
    print(f"P1 divergence: value 1.0 -> node JCS {h_node[:12]}… vs pythonish {h_py[:12]}…")
    probe["action_detail"] = {"tool": "calc", "value": -0.0}
    assert sha(jcs_node(probe)) != sha(jcs_pythonish(probe))
    probe["action_detail"] = {"tool": "calc", "value": 2**53 + 1}
    n1, n2 = jcs_node(probe), jcs_pythonish(probe)
    print(f"P1 divergence: -0.0 diverges; 2^53+1 -> node emits "
          f"{b'9007199254740992' in n1} (rounded), python keeps "
          f"{b'9007199254740993' in n2} -- same record, two hashes")

    # P2: the close record's own content is unbound (EXT-022 class)
    tampered = json.loads(json.dumps(honest))
    tampered[-1]["action_detail"]["record_count"] = 3   # a lie, after the fact
    assert verify_musts(tampered) is None, "every MUST still verifies"
    print("P2 unbound:   record_count in the close altered 10 -> 3; every MUST still passes")

    # P3: interior deletion + reseal; all optional completeness aids absent
    cut = json.loads(json.dumps(honest))
    del cut[4]
    cut = reseal(cut)
    cut[-1]["action_detail"]["record_count"] = len(cut)
    assert verify_musts(cut) is None, verify_musts(cut)
    with open(os.path.join(HERE, "session-cut-resealed.jsonl"), "w") as f:
        for r in cut:
            f.write(json.dumps(r) + "\n")
    print("P3 silent cut: interior record deleted, chain and session_hash resealed; "
          "every MUST passes on 9 records as on 10")
    print("\nall probes hold -- see FINDINGS draft for the write-up")


if __name__ == "__main__":
    main()
