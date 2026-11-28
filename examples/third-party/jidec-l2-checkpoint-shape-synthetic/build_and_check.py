#!/usr/bin/env python3
"""SYNTHETIC: the settled JIDEC L2 design, graded end to end.

Everything here is fabricated by this script -- not the JIDEC ledger's
output, not endorsed by its maintainer. It models the design SETTLED in
vlc-1 issue #12 (2026-11-28), replacing the earlier exploratory template
one directory over (jidec-l2-shape-synthetic, kept for the record):

  * the declaration lives INSIDE the checkpoint entry, in the same chained,
    stamped record as the head it closes;
  * full form from the first window:
        production_count: {from, to, received, refused, lost}
    with received = written_in_window + refused + lost;
  * the unit is the ledger entry; `to` is the last entry written before the
    checkpoint, `from` is the one after the previous checkpoint's `to`;
  * the day's refusal list is its own file; its sha256 rides in the same
    checkpoint (modelled here as refusals_sha256 -- the checker reads the
    counts; the hash makes the itemization auditable);
  * a witness batch is one entry (the identity's unit is the entry).

Graded with loss.mode "windowed_declaration" (1.4.6-draft), which also
gives the honest answer for the operational reality their lag find exposed:
entries written after the last checkpoint form a contiguous TAIL, reported
as awaiting declaration -- while an ordinal gap in that tail fails L2.

Self-check builds five trails and asserts the verdicts:
  trail.jsonl               honest, two windows            -> structural L2
  trail-tail.jsonl          honest + 3 entries after the
                            last checkpoint (pre-December
                            capture timing)                -> structural L2, tail reported
  trail-undercount.jsonl    a window's received lowered    -> window does not close, L1
  trail-hidden-drop.jsonl   entry silently removed inside
                            a declared window              -> window does not close, L1
  trail-tail-gap.jsonl      ordinal gap in the tail        -> undeclared loss, L1

Run:  python3 examples/third-party/jidec-l2-checkpoint-shape-synthetic/build_and_check.py
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
ADAPTER = os.path.join(HERE, "adapter-l2-checkpoint.json")


def entry_hash(obj, hash_fields):
    body = {f: obj[f] for f in hash_fields if f in obj}
    return sha256_hex(canon(body).encode())


class Builder:
    def __init__(self):
        self.hf = json.load(open(ADAPTER))["integrity"]["hash_fields"]
        self.recs, self.prev, self.n = [], ZERO, 0

    def add(self, obj):
        self.n += 1
        obj = dict(obj, n=self.n, prev_entry_sha256=self.prev)
        obj["entry_sha256"] = self.prev = entry_hash(obj, self.hf)
        self.recs.append(obj)
        return obj

    def claim(self, i):
        return self.add({"schema": "jidec-claim-v1",
                         "claim_sha256": sha256_hex(f"claim {i}".encode()),
                         "created_at": f"2026-11-28T0{i % 10}:00:00Z"})

    def checkpoint(self, frm, to, received, refused, lost):
        return self.add({"schema": "nenrin-head-checkpoint-v1",
                         "created_at": "2026-11-28T18:00:00Z",
                         "production_count": {"from": frm, "to": to,
                                              "received": received,
                                              "refused": refused, "lost": lost},
                         "refusals_sha256": sha256_hex(b"synthetic refusal list"),
                         "chain_head": self.prev})

    def marker(self):
        m = {"schema": "jidec-head-v1", "n": self.n + 1,
             "prev_entry_sha256": self.prev, "head": self.prev}
        m["entry_sha256"] = entry_hash(m, self.hf)
        self.recs.append(m)
        return m["entry_sha256"]

    def write(self, path):
        with open(path, "w") as f:
            for r in self.recs:
                f.write(json.dumps(r) + "\n")


def honest(tail_entries=0):
    b = Builder()
    for i in range(1, 6):                 # day 1: writes entries 1..5
        b.claim(i)
    b.checkpoint(1, 5, 7, 1, 1)           # 5 written + 1 refused + 1 lost = 7 received
    for i in range(7, 11):                # day 2: four claims; the day-1 checkpoint is entry 6
        b.claim(i)
    # from = the entry after the previous checkpoint's to (their rule), so the
    # window [6,10] contains the day-1 checkpoint itself: the unit is the entry
    b.checkpoint(6, 10, 6, 1, 0)          # 5 written (cp6 + 4 claims) + 1 refused = 6 received
    for i in range(1, tail_entries + 1):  # entries after the last checkpoint
        b.claim(100 + i)
    return b


def grade(path, head):
    rep = check(path, ADAPTER, expect_head=head)
    fails = {rid for rid, r in rep["requirements"].items() if r["status"] == "FAIL"}
    return rep.get("structural_level"), fails, rep


def main():
    out = lambda name: os.path.join(HERE, name)  # noqa: E731

    b = honest()
    h = b.marker()
    b.write(out("trail.jsonl"))
    s, fails, rep = grade(out("trail.jsonl"), h)
    print(f"honest:        structural L{s}")
    assert s >= 2, f"honest must reach L2; fails: {sorted(fails)}; " + \
        rep["requirements"].get("VLC-L2-5", {}).get("note", "")

    b = honest(tail_entries=3)
    h = b.marker()
    b.write(out("trail-tail.jsonl"))
    s, fails, rep = grade(out("trail-tail.jsonl"), h)
    note = rep["requirements"]["VLC-L2-5"].get("note", "")
    print(f"honest+tail:   structural L{s}  ({note.split(';')[-1].strip()[:60]}...)")
    assert s >= 2 and "tail" in note, "contiguous tail must be reported, not failed"

    b = honest()
    cp = next(r for r in b.recs if r["schema"] == "nenrin-head-checkpoint-v1")
    cp["production_count"]["received"] = 6   # lie: one fewer received
    # reseal from the edited checkpoint on
    i = b.recs.index(cp)
    prev = b.recs[i - 1]["entry_sha256"]
    for r in b.recs[i:]:
        r["prev_entry_sha256"] = prev
        r.pop("entry_sha256", None)
        r["entry_sha256"] = prev = entry_hash(r, b.hf)
    b.prev = prev
    h = b.marker()
    b.write(out("trail-undercount.jsonl"))
    s, fails, _ = grade(out("trail-undercount.jsonl"), h)
    print(f"undercount:    structural L{s}  (fails: {sorted(f for f in fails if 'L2' in f)})")
    assert s < 2 and "VLC-L2-2" in fails, "a window that does not close must fail"

    b = honest()
    victim = next(r for r in b.recs if r.get("n") == 3)
    b.recs.remove(victim)                    # silent in-window drop, chain resealed
    prev = ZERO
    for r in b.recs:
        r["prev_entry_sha256"] = prev
        r.pop("entry_sha256", None)
        r["entry_sha256"] = prev = entry_hash(r, b.hf)
    b.prev = prev
    h = b.marker()
    b.write(out("trail-hidden-drop.jsonl"))
    s, fails, _ = grade(out("trail-hidden-drop.jsonl"), h)
    print(f"hidden drop:   structural L{s}  (fails: {sorted(f for f in fails if 'L2' in f)})")
    assert s < 2, "an undeclared in-window drop must fail even with a resealed chain"

    b = honest(tail_entries=3)
    victim = b.recs[-2]                      # remove a middle tail entry, reseal
    b.recs.remove(victim)
    prev = ZERO
    for r in b.recs:
        r["prev_entry_sha256"] = prev
        r.pop("entry_sha256", None)
        r["entry_sha256"] = prev = entry_hash(r, b.hf)
    b.prev = prev
    h = b.marker()
    b.write(out("trail-tail-gap.jsonl"))
    s, fails, _ = grade(out("trail-tail-gap.jsonl"), h)
    print(f"tail gap:      structural L{s}  (fails: {sorted(f for f in fails if 'L2' in f)})")
    assert s < 2, "an ordinal gap in the undeclared tail must fail"

    print("all assertions hold: the settled checkpoint design grades end to end")


if __name__ == "__main__":
    main()
