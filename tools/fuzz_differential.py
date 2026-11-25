#!/usr/bin/env python3
"""Differential fuzzer: the live worker's JS core vs the Python reference.

    ./tools/fuzz_differential.py [N] [SEED]      (default: 300 cases, seed 0)

The scary bug class for a conformance checker with two implementations is a
journal they GRADE DIFFERENTLY -- above all one the reference fails and the
live endpoint passes, which would be a false conformance claim on our own
product. The fixed parity matrix (worker/parity.test.mjs, 18 assertions)
freezes known cases; this generates new ones forever.

Per case: build a journal (a valid canonical chain via the spec's own rule,
then randomly mutated -- tampered hashes, deleted/duplicated/reordered
records, truncation, unbound END markers, non-integer counts, junk lines,
unicode, huge ints), grade it with conformance.check() and with the worker
core through worker/fuzz_harness.mjs (node), and compare the three ported
requirements: VLC-L1-1, VLC-L1-3, VLC-L2-5.

Floats are deliberately never generated: JSON float canonicalization is a
DOCUMENTED divergence (the live page carries the caveat).

Exit 0: all cases agree. Exit 1: disagreement -- the reproducing journal is
written to fuzz_repro_<case>.jsonl in the current directory.

Blast radius: this repo dir (repro files on failure) + a self-created temp
dir, cleaned on exit. No network, no installs.
"""
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from conformance import check as py_check  # noqa: E402

ADAPTER = os.path.join(REPO, "adapters", "generic-appjsonl.json")
HARNESS = os.path.join(REPO, "worker", "fuzz_harness.mjs")
ROOT = "0" * 64
CHECKS = ("VLC-L1-1", "VLC-L1-3", "VLC-L2-5")


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def chain(bodies):
    """Bind a list of record bodies into a valid canonical chain."""
    prev, out = ROOT, []
    for body in bodies:
        h = hashlib.sha256((prev + canon(body)).encode()).hexdigest()
        rec = dict(body)
        rec["hash"] = h
        out.append(rec)
        prev = h
    return out, prev


def rand_value(rng, depth=0):
    r = rng.random()
    if r < 0.3:
        return rng.choice(["allow", "deny", "", "héllo wörld ☃", "a" * rng.randint(1, 40)])
    if r < 0.6:
        return rng.choice([0, 1, -1, 2**31, 2**63, rng.randint(-10**6, 10**6)])
    if r < 0.7:
        return rng.choice([True, False, None])
    if r < 0.85 and depth < 2:
        return [rand_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    if depth < 2:
        return {f"k{i}": rand_value(rng, depth + 1) for i in range(rng.randint(0, 3))}
    return rng.randint(0, 99)


def gen_bodies(rng):
    """Random but internally consistent journal bodies (EPOCH_START..END)."""
    bodies = [{"class": "EPOCH_START", "producer": "fuzz/1.0"}]
    n_events = rng.randint(0, 12)
    lost_total, seq = 0, 0
    for _ in range(n_events):
        ev = {"class": "inference", "seq": seq, "route": "/v1/chat",
              "tokens_in": rng.randint(1, 5000)}
        if rng.random() < 0.4:
            ev["extra"] = rand_value(rng)
        bodies.append(ev)
        seq += 1
        if rng.random() < 0.2:
            lost = rng.randint(1, 9)
            bodies.append({"class": "DROP", "lost": lost, "from_seq": seq,
                           "to_seq": seq + lost - 1, "cause": "queue full"})
            seq += lost
            lost_total += lost
    end = {"class": "END", "records": n_events, "lost_total": lost_total}
    bodies.append(end)
    return bodies


MUTATIONS = [
    "none", "tamper_hash", "tamper_field", "delete_record", "duplicate_record",
    "reorder", "truncate_end", "unbound_end", "wrong_counts", "float_free_junk_line",
    "empty", "garbage", "huge_counts", "noninteger_counts", "no_epoch",
]


def build_case(rng):
    mut = rng.choice(MUTATIONS)
    if mut == "empty":
        return mut, ""
    if mut == "garbage":
        return mut, "".join(rng.choice("{}[]\",:x01éに\n") for _ in range(rng.randint(1, 200)))
    bodies = gen_bodies(rng)
    if mut == "wrong_counts":
        bodies[-1]["records"] = bodies[-1]["records"] + rng.choice([-2, -1, 1, 3])
    if mut == "huge_counts":
        bodies[-1]["records"] = 2**62
    if mut == "noninteger_counts":
        bodies[-1]["records"] = rng.choice(["7", True, None, [1]])
    if mut == "no_epoch":
        bodies = bodies[1:]
    recs, head = chain(bodies)
    # END self-binds: head field must name the PREVIOUS record's hash
    if len(recs) >= 2:
        end_body = {k: v for k, v in recs[-1].items() if k != "hash"}
        end_body["head"] = recs[-2]["hash"] if mut != "unbound_end" else "ab" * 32
        prev = recs[-2]["hash"]
        h = hashlib.sha256((prev + canon(end_body)).encode()).hexdigest()
        end_body["hash"] = h
        recs[-1] = end_body
    lines = [json.dumps(r, sort_keys=True) for r in recs]
    if mut == "tamper_hash" and len(lines) > 2:
        i = rng.randrange(1, len(lines) - 1)
        lines[i] = lines[i].replace('"hash": "a', '"hash": "b').replace('"hash": "0', '"hash": "1') \
            if '"hash": "a' in lines[i] or '"hash": "0' in lines[i] else lines[i][:-2] + '"}'[:2]
    if mut == "tamper_field" and len(lines) > 2:
        i = rng.randrange(1, len(lines) - 1)
        lines[i] = lines[i].replace('"route": "/v1/chat"', '"route": "/v1/TAMPERED"')
    if mut == "delete_record" and len(lines) > 3:
        del lines[rng.randrange(1, len(lines) - 1)]
    if mut == "duplicate_record" and len(lines) > 2:
        i = rng.randrange(1, len(lines) - 1)
        lines.insert(i, lines[i])
    if mut == "reorder" and len(lines) > 3:
        i = rng.randrange(1, len(lines) - 2)
        lines[i], lines[i + 1] = lines[i + 1], lines[i]
    if mut == "truncate_end":
        lines = lines[:-1]
    if mut == "float_free_junk_line" and lines:
        lines.insert(rng.randrange(len(lines)), rng.choice(
            ["not json at all", "{\"class\":", "[1,2,3]", "null", "{\"no_class\":1}"]))
    return mut, "\n".join(lines) + ("\n" if lines else "")


def py_verdict(journal, tmp):
    p = os.path.join(tmp, "j.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        f.write(journal)
    rep = py_check(p, ADAPTER)
    # hierarchical reference: a requirement not evaluated (lower level failed)
    # is absent from the report -- same as the parity matrix, absent means not
    # demonstrated, i.e. False
    return {c: rep["requirements"].get(c, {}).get("status") == "PASS" for c in CHECKS}


def js_verdict(journal):
    r = subprocess.run(["node", HARNESS, ADAPTER], input=journal.encode(),
                       capture_output=True, timeout=30)
    out = json.loads(r.stdout.decode())
    if "harness_error" in out:
        return None, out["harness_error"]
    if out.get("verdict") == "NOT GRADABLE LIVE":
        # the live subset DISCLOSED it cannot grade (e.g. integers beyond
        # 2^53) and refused rather than guessed -- a documented scope limit,
        # not a disagreement; the reference remains the authority
        return "disclosed", None
    got = {x["check"]: bool(x["ok"]) for x in out.get("results", [])}
    return {c: got.get(c, False) for c in CHECKS}, None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rng = random.Random(seed)
    tmp = tempfile.mkdtemp(prefix="vlcfuzz-")
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
                repro = os.path.join(os.getcwd(), f"fuzz_repro_{i}.jsonl")
                with open(repro, "w", encoding="utf-8") as f:
                    f.write(journal)
                print(f"DISAGREE case {i} (mutation {mut}): python={py} js={js} err={err}")
                print(f"  repro journal: {repro}")
        print(f"\n{n} cases, seed {seed}: " +
              ", ".join(f"{k}×{v}" for k, v in sorted(by_mut.items())))
        if disagreements:
            print(f"FUZZ FAIL: {disagreements} disagreement(s)")
            return 1
        print("FUZZ PASS: JS worker core and Python reference agree on every case")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
