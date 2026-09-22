#!/usr/bin/env python3
# ===========================================================================
# Regenerates the Annex K worked example in this directory, byte-for-byte.
#
# BLAST RADIUS: writes ledger.jsonl, anchors.json and docs/ in this directory
# only. No network, no processes.
#
# EXAMPLE ONLY: nonces here are derived from a label so the example is
# reproducible. A real ledger MUST use findings.py commit, which draws each
# nonce from the operating system's CSPRNG (K.4, VLC-K-4 note).
# ===========================================================================
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import findings as f  # noqa: E402

DOCS = {
    "F-001": "Finding F-001 (high)\n\nTool output returned by the retrieval tool is passed to the planner\n"
             "unescaped; an instruction embedded in a retrieved page caused the agent to call the\n"
             "shell tool. Reproduced 7/10 runs. Fixed in subject build 2026.11.2.\n",
    "F-002": "Finding F-002 (critical)\n\nThe evaluation sandbox allowed outbound HTTPS to a public package\n"
             "registry. The agent under test attempted to publish a package. Not yet disclosed.\n",
    "F-003": "Finding F-003 (low)\n\nDuplicate of F-001, filed by a second tester.\n",
}
PLAN = [  # (kind, finding, party, at, extra)
    ("commit",   "F-001", "tester",  "2026-10-02T09:14:00Z", {"class": "high", "due": "2026-10-30"}),
    ("commit",   "F-002", "tester",  "2026-10-03T16:40:00Z", {"class": "critical", "due": "2026-10-17"}),
    ("commit",   "F-003", "tester",  "2026-10-04T11:05:00Z", {"class": "low", "due": "2026-11-01"}),
    ("defer",    "F-001", "subject", "2026-10-28T08:00:00Z", {"due": "2026-11-30", "reason": "fix-in-progress"}),
    ("withdraw", "F-003", "tester",  "2026-10-29T10:30:00Z", {"reason": "duplicate"}),
    ("reveal",   "F-001", "tester",  "2026-11-25T14:00:00Z", {}),
]
ANCHOR_AFTER = {"subject": 2, "tester": 5}  # record index each party published


def nonce(fid):
    return hashlib.sha256(f"vlc1-annex-k-example-nonce:{fid}".encode()).hexdigest()


def main():
    os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
    digests = {}
    for fid, text in DOCS.items():
        b = text.encode()
        digests[fid] = f.sha256_hex(b)
        with open(os.path.join(HERE, "docs", fid + ".md"), "wb") as fh:
            fh.write(b)
    committed = {}
    recs, prev = [], f.GENESIS
    for i, (kind, fid, party, at, extra) in enumerate(PLAN):
        body = {"kind": kind, "finding_id": fid, "party": party}
        if kind == "commit":
            committed[fid] = extra
            body.update(extra, commitment=f.commitment_of(fid, extra["class"], extra["due"],
                                                          nonce(fid), digests[fid]))
        elif kind in ("reveal", "withdraw"):
            body.update(extra, nonce=nonce(fid), doc_sha256=digests[fid])
        else:
            body.update(extra)
        rec = dict(body, v=f.VERSION, seq=i, prev=prev, at=at)
        rec["hash"] = f.record_hash(rec)
        assert not f.shape_problems(rec), f.shape_problems(rec)
        recs.append(rec)
        prev = rec["hash"]
    with open(os.path.join(HERE, "ledger.jsonl"), "w") as fh:
        for r in recs:
            fh.write(f.canon(r) + "\n")
    # Only revealed findings are published. F-002 is still undisclosed and F-003 was withdrawn,
    # so their documents stay with the tester; only their commitments are public.
    for fid in ("F-002", "F-003"):
        os.remove(os.path.join(HERE, "docs", fid + ".md"))
    with open(os.path.join(HERE, "anchors.json"), "w") as fh:
        json.dump({p: recs[k]["hash"] for p, k in ANCHOR_AFTER.items()}, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
