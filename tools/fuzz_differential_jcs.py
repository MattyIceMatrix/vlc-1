#!/usr/bin/env python3
"""Differential fuzzer for the RFC 8785 family (sha256-chain-jcs-nested).

    ./tools/fuzz_differential_jcs.py [N] [SEED]      (default: 300 cases, seed 0)

tools/fuzz_differential.py generates cases for sha256-chain-canonical only;
this does the same job for the jcs-nested mechanism the live checker serves
for the Runtime Record shape (adapters/halo-runtime-record.json): nested hash
member, carried predecessor link, the EXT-013 link check, and the guarded JCS
subset (floats, ints beyond 2^53-1 and non-BMP object keys are unrecomputable
by DESIGN -- both implementations must say so identically, so this fuzzer
generates them on purpose, unlike the canonical fuzzer, where float handling
is a documented divergence).

Per case: build a valid jcs-nested chain, randomly mutate, grade with
conformance.check() and with the worker core via worker/fuzz_harness.mjs,
and compare VLC-L1-1 and VLC-L1-3. The mutation this fuzzer exists for is
`link_edit_resealed`: a record whose carried prev link is rewritten AND
resealed, so the record is self-consistent and only the EXT-013 comparison
against the true predecessor can catch it -- the exact bug class the
jcs-nested-prev-link-edited vector froze.

Exit 0: all cases agree. Exit 1: disagreement -- repro journal written to
fuzz_jcs_repro_<case>.jsonl in the current directory.

Blast radius: this repo dir (repro files on failure) + a self-created temp
dir, cleaned on exit. No network, no installs.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from conformance import check as py_check, canon_jcs, sha256_hex  # noqa: E402

ADAPTER = os.path.join(REPO, "adapters", "halo-runtime-record.json")
HARNESS = os.path.join(REPO, "worker", "fuzz_harness.mjs")
ROOT = "0" * 64
CHECKS = ("VLC-L1-1", "VLC-L1-3")


def seal(body, prev):
    """The producer's sealing formula: carry the link, hash as delivered."""
    rec = json.loads(json.dumps(body))
    rec.setdefault("integrity", {})["prev_hash"] = prev
    clone = json.loads(json.dumps(rec))
    del clone["integrity"]["prev_hash"]
    clone["integrity"].pop("hash", None)
    clone["integrity"]["prev_hash"] = prev
    rec["integrity"]["hash"] = sha256_hex(canon_jcs(clone).encode("utf-8"))
    return rec


def rand_value(rng, depth=0):
    r = rng.random()
    if r < 0.30:
        return rng.choice(["ok", "", "héllo wörld ☃", "é́ combining",
                           "a" * rng.randint(1, 40)])
    if r < 0.55:
        return rng.choice([0, 1, -1, 2**31, 2**53 - 1, rng.randint(-10**6, 10**6)])
    if r < 0.65:
        return rng.choice([True, False, None])
    if r < 0.80 and depth < 2:
        return [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if depth < 2:
        return {f"k{i}": rand_value(rng, depth + 1) for i in range(rng.randint(0, 3))}
    return rng.randint(0, 99)


def gen_records(rng):
    recs, prev = [], ROOT
    for i in range(rng.randint(1, 10)):
        body = {"schema_version": "1.0", "record_id": f"rec-{i:04d}",
                "ts": f"2026-11-27T13:{i:02d}:00Z",
                "action": {"type": rng.choice(["tool_call", "message", "halt"]),
                           "tool": rng.choice(["search", "café_lookup", "exec"])},
                "outcome": {"status": rng.choice(["ok", "refused"])}}
        if rng.random() < 0.5:
            body["extra"] = rand_value(rng)
        rec = seal(body, prev)
        prev = rec["integrity"]["hash"]
        recs.append(rec)
    return recs


MUTATIONS = [
    "none", "none", "tamper_field", "tamper_hash", "link_edit_resealed",
    "link_edit_raw", "delete_interior", "duplicate", "reorder", "truncate",
    "reordered_keys", "float_value", "big_int", "astral_key", "junk_line",
    "empty", "garbage",
]


def build_case(rng):
    mut = rng.choice(MUTATIONS)
    if mut == "empty":
        return mut, ""
    if mut == "garbage":
        return mut, "not json at all\x00\xff\n{broken\n"
    recs = gen_records(rng)
    i = rng.randrange(len(recs))
    if mut == "tamper_field":
        recs[i]["outcome"] = {"status": "tampered"}
    elif mut == "tamper_hash":
        recs[i]["integrity"]["hash"] = "ab" * 32
    elif mut == "link_edit_resealed":
        # self-consistent record, wrong ancestry: only EXT-013 can see it
        body = json.loads(json.dumps(recs[i]))
        del body["integrity"]
        recs[i] = seal(body, "cd" * 32)
    elif mut == "link_edit_raw":
        recs[i]["integrity"]["prev_hash"] = "ef" * 32
    elif mut == "delete_interior" and len(recs) > 2:
        del recs[rng.randrange(1, len(recs) - 1)]
    elif mut == "duplicate":
        recs.insert(i, json.loads(json.dumps(recs[i])))
    elif mut == "reorder" and len(recs) > 1:
        j = rng.randrange(len(recs))
        recs[i], recs[j] = recs[j], recs[i]
    elif mut == "truncate":
        recs = recs[: max(1, len(recs) - rng.randint(1, 2))]
    elif mut == "reordered_keys":
        # JCS normalizes key order: this mutation must change NOTHING
        recs[i] = json.loads(json.dumps(
            {k: recs[i][k] for k in sorted(recs[i], reverse=True)}))
    elif mut == "float_value":
        recs[i]["extra"] = rng.choice([3.7, -0.0, 1e308])
    elif mut == "big_int":
        recs[i]["extra"] = rng.choice([2**53, -(2**60), 10**30])
    elif mut == "astral_key":
        recs[i]["\U0001F600key"] = "astral"
    lines = [json.dumps(r, ensure_ascii=False) for r in recs]
    if mut == "junk_line":
        lines.insert(rng.randrange(len(lines) + 1),
                     rng.choice(["", "   ", "{not json", '"just a string"']))
    return mut, "\n".join(lines) + "\n"


def py_verdict(journal, tmp):
    p = os.path.join(tmp, "j.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write(journal)
    rep = py_check(p, ADAPTER)
    return {c: rep["requirements"].get(c, {}).get("status") == "PASS" for c in CHECKS}


def js_verdict(journal):
    r = subprocess.run(["node", HARNESS, ADAPTER], input=journal.encode(),
                       capture_output=True, timeout=30)
    out = json.loads(r.stdout.decode())
    if "harness_error" in out:
        return None, out["harness_error"]
    if out.get("verdict") == "NOT GRADABLE LIVE":
        return "disclosed", None
    got = {x["check"]: bool(x["ok"]) for x in out.get("results", [])}
    return {c: got.get(c, False) for c in CHECKS}, None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rng = random.Random(seed)
    tmp = tempfile.mkdtemp(prefix="vlcfuzzjcs-")
    disagreements = 0
    by_mut = {}
    try:
        for i in range(n):
            mut, journal = build_case(rng)
            py = py_verdict(journal, tmp)
            js, err = js_verdict(journal)
            by_mut[mut] = by_mut.get(mut, 0) + 1
            if js == "disclosed":
                by_mut["(disclosed-not-gradable)"] = by_mut.get("(disclosed-not-gradable)", 0) + 1
                continue
            if err is not None or py != js:
                disagreements += 1
                repro = os.path.join(os.getcwd(), f"fuzz_jcs_repro_{i}.jsonl")
                with open(repro, "w", encoding="utf-8") as f:
                    f.write(journal)
                print(f"DISAGREE case {i} (mutation {mut}): python={py} js={js} err={err}")
                print(f"  repro journal: {repro}")
        print(f"\n{n} cases, seed {seed}: " +
              ", ".join(f"{k}×{v}" for k, v in sorted(by_mut.items())))
        if disagreements:
            print(f"FUZZ FAIL: {disagreements} disagreement(s)")
            return 1
        print("FUZZ PASS: JS worker core and Python reference agree on every "
              "jcs-nested case")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
