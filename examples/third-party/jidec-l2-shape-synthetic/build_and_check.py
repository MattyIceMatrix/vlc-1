#!/usr/bin/env python3
"""SYNTHETIC worked example: the JIDEC ledger shape, extended to L2.

Everything here is fabricated by this script. It is NOT the JIDEC ledger's
output and the maintainer has not endorsed it. It exists as a concrete
template for the L2 loss-accounting walk (vlc-1 issue #12): the smallest
extension of the jidec-chain-v1 wire shape that closes the completeness
identity, chosen so that NO EXISTING ENTRY CHANGES.

The design, in three additions (hash recipe untouched for old records,
because sha256-canonical-fields omits absent fields):

  1. every event entry gains `submission_seq` -- the producer's intake
     ordinal, assigned before anything can be dropped;
  2. a new non-event record class `jidec-loss-v1` declares losses with
     {lost, from_seq, to_seq} -- an explicit count AND interval (VLC-L2-2);
  3. the bound end marker gains `produced_count` -- the producer's
     independent figure. Read from the BOUND marker, it cannot be lowered
     after the fact to hide a drop (EXT-022 made that a hash break).

The identity the checker then closes (VLC-L2-5):
    |delivered event entries| + sum(declared losses) == produced_count

Self-check: builds three trails and asserts the checker's verdicts --
  trail-l2.jsonl             honest        -> structural L2 (attested L1)
  trail-l2-overcount.jsonl   produced_count raised by 1 -> identity open, not L2
  trail-l2-undeclared.jsonl  loss declaration deleted   -> identity open, not L2

Run:  python3 examples/third-party/jidec-l2-shape-synthetic/build_and_check.py
Blast radius: writes only into this example's own directory.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, REPO)
from conformance import check, canon, sha256_hex  # noqa: E402

ZERO = "0" * 64
ADAPTER = os.path.join(HERE, "adapter-l2-template.json")


def entry_hash(obj, hash_fields):
    body = {f: obj[f] for f in hash_fields if f in obj}
    return sha256_hex(canon(body).encode())


def build(path, produced_count, with_declaration):
    """14 submissions produced; seqs 6 and 7 lost before writing (simulated
    worker restart); 12 event entries, one loss declaration, bound marker."""
    hf = json.load(open(ADAPTER))["integrity"]["hash_fields"]
    recs, prev, n = [], ZERO, 0
    for seq in list(range(1, 6)) + list(range(8, 15)):
        n += 1
        e = {"n": n, "schema": "jidec-claim-v1",
             "claim_sha256": sha256_hex(f"synthetic claim {seq}".encode()),
             "created_at": f"2026-11-27T12:{n:02d}:00Z",
             "submission_seq": seq, "prev_entry_sha256": prev}
        e["entry_sha256"] = prev = entry_hash(e, hf)
        recs.append(e)
    if with_declaration:
        n += 1
        d = {"n": n, "schema": "jidec-loss-v1",
             "created_at": "2026-11-27T12:30:00Z",
             "lost": 2, "from_seq": 6, "to_seq": 7,
             "note": "worker restart between accept and write (synthetic)",
             "prev_entry_sha256": prev}
        d["entry_sha256"] = prev = entry_hash(d, hf)
        recs.append(d)
    m = {"n": n + 1, "schema": "jidec-head-v1", "prev_entry_sha256": prev,
         "head": prev, "produced_count": produced_count}
    m["entry_sha256"] = entry_hash(m, hf)
    recs.append(m)
    with open(path, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    return m["entry_sha256"]


def grade(path, head):
    rep = check(path, ADAPTER, expect_head=head)
    return rep.get("structural_level"), rep.get("attested_level"), rep


def main():
    honest = os.path.join(HERE, "trail-l2.jsonl")
    over = os.path.join(HERE, "trail-l2-overcount.jsonl")
    undecl = os.path.join(HERE, "trail-l2-undeclared.jsonl")

    h1 = build(honest, produced_count=14, with_declaration=True)
    h2 = build(over, produced_count=15, with_declaration=True)
    h3 = build(undecl, produced_count=14, with_declaration=False)

    s, a, rep = grade(honest, h1)
    print(f"honest:      structural L{s} attested L{a}")
    assert s >= 2, f"honest trail must reach structural L2, got L{s}: " + \
        "; ".join(f"{rid}: {r.get('note','')}" for rid, r in rep["requirements"].items()
                  if r["status"] == "FAIL")

    s2, _, rep2 = grade(over, h2)
    fails2 = {rid for rid, r in rep2["requirements"].items() if r["status"] == "FAIL"}
    print(f"overcount:   structural L{s2} (fails: {sorted(f for f in fails2 if f.startswith('VLC-L2'))})")
    assert s2 < 2 and "VLC-L2-5" in fails2, "raising produced_count must open the identity"

    s3, _, rep3 = grade(undecl, h3)
    fails3 = {rid for rid, r in rep3["requirements"].items() if r["status"] == "FAIL"}
    print(f"undeclared:  structural L{s3} (fails: {sorted(f for f in fails3 if f.startswith('VLC-L2'))})")
    assert s3 < 2 and "VLC-L2-5" in fails3, "deleting the declaration must open the identity"

    print("all assertions hold: the L2 path works on the jidec-chained shape")


if __name__ == "__main__":
    main()
