#!/usr/bin/env python3
"""Differential fuzzer for the prefix-chain family (sha256-chain-prefix).

    ./tools/fuzz_differential_prefix.py [N] [SEED]    (default: 300 cases, seed 0)

Completes the generative-fuzz coverage of the live checker's served mechanism
families: fuzz_differential.py covers sha256-chain-canonical,
fuzz_differential_jcs.py covers sha256-chain-jcs-nested, and this covers
sha256-chain-prefix (the observer shape: hash over the RAW LINE PREFIX, so
whitespace and key order are load-bearing, the root is derived from the first
record's own field, and the bound HEAD marker closes the chain).

Mechanism-specific mutations this exists for:
  * whitespace_insert  -- one added space changes the hash; both graders must fail
  * hash_not_last      -- the hash member not at the end of the line: the
                          chained text is unrecoverable, not merely tampered
  * root_mismatch      -- record 0's own hash differs from the derived root
  * stale_head_claim   -- the bound marker names a head of a shorter chain

Per case: build a valid prefix chain, mutate, grade with conformance.check()
and the worker core via worker/fuzz_harness.mjs, compare VLC-L1-1, VLC-L1-3.

Exit 0: all cases agree. Exit 1: disagreement -- repro journal written to
fuzz_prefix_repro_<case>.jsonl in the current directory.

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

ADAPTER = os.path.join(REPO, "adapters", "observer.json")
HARNESS = os.path.join(REPO, "worker", "fuzz_harness.mjs")
CHECKS = ("VLC-L1-1", "VLC-L1-3")


def seal_line(body_json_text, prev_bytes):
    """h = sha256(prev || text-before-the-hash-member); the member goes last."""
    text = body_json_text[:-1]  # strip the closing brace; the suffix re-adds it
    h = hashlib.sha256(prev_bytes + text.encode()).hexdigest()
    return text + ',"h":"' + h + '"}', h


def gen_lines(rng):
    pd = f"policy-{rng.randint(0, 999999)}"
    root = hashlib.sha256(pd.encode()).digest()
    # record 0 IS the root statement: its own hash must equal the derived root
    b0 = json.dumps({"class": "EPOCH_START", "policy_digest": pd,
                     "producer": "fuzzpfx/1.0"}, ensure_ascii=False)
    lines = [b0[:-1] + ',"h":"' + root.hex() + '"}']
    prev = root
    for i in range(rng.randint(0, 9)):
        body = {"class": "decision", "seq": i,
                "verdict": rng.choice(["allow", "deny", "héllo ☃"]),
                "rule": "r" * rng.randint(1, 20)}
        line, h = seal_line(json.dumps(body, ensure_ascii=False), prev)
        lines.append(line)
        prev = bytes.fromhex(h)
    mline, _ = seal_line(json.dumps({"class": "HEAD", "head": prev.hex()},
                                    ensure_ascii=False), prev)
    lines.append(mline)
    return lines


MUTATIONS = [
    "none", "none", "tamper_field", "tamper_hash", "whitespace_insert",
    "hash_not_last", "root_mismatch", "stale_head_claim", "delete_interior",
    "duplicate", "reorder", "truncate", "unbound_end", "junk_line",
    "big_int", "empty", "garbage",
]


def build_case(rng):
    mut = rng.choice(MUTATIONS)
    if mut == "empty":
        return mut, ""
    if mut == "garbage":
        return mut, "]]not json[[\n\x01\n"
    lines = gen_lines(rng)
    i = rng.randrange(len(lines))
    if mut == "tamper_field":
        lines[i] = lines[i].replace('"class":', '"klass":', 1)
    elif mut == "tamper_hash":
        j = lines[i].rindex('"h":"') + 5
        lines[i] = lines[i][:j] + "ab" * 32 + lines[i][j + 64:]
    elif mut == "whitespace_insert":
        lines[i] = lines[i].replace(":", ": ", 1)
    elif mut == "hash_not_last":
        obj = json.loads(lines[i])
        h = obj.pop("h")
        out = {"h": h}
        out.update(obj)
        lines[i] = json.dumps(out, ensure_ascii=False)
    elif mut == "root_mismatch":
        obj = json.loads(lines[0])
        obj["policy_digest"] = "someone-elses-policy"
        pre = json.dumps({k: v for k, v in obj.items() if k != "h"},
                         ensure_ascii=False)
        lines[0] = pre[:-1] + ',"h":"' + obj["h"] + '"}'
    elif mut == "stale_head_claim" and len(lines) > 2:
        # reseal the marker over a head one record early: its own binding
        # holds, the claim does not
        prev_h = json.loads(lines[-2])["h"]
        early_h = json.loads(lines[-3])["h"] if len(lines) > 2 else prev_h
        mline, _ = seal_line(json.dumps({"class": "HEAD", "head": early_h},
                                        ensure_ascii=False),
                             bytes.fromhex(prev_h))
        lines[-1] = mline
    elif mut == "delete_interior" and len(lines) > 3:
        del lines[rng.randrange(1, len(lines) - 1)]
    elif mut == "duplicate":
        lines.insert(i, lines[i])
    elif mut == "reorder" and len(lines) > 1:
        j = rng.randrange(len(lines))
        lines[i], lines[j] = lines[j], lines[i]
    elif mut == "truncate":
        lines = lines[: max(1, len(lines) - rng.randint(1, 2))]
    elif mut == "unbound_end":
        j = lines[-1].rindex('"h":"') + 5
        lines[-1] = lines[-1][:j] + "cd" * 32 + lines[-1][j + 64:]
    elif mut == "big_int":
        body = {"class": "decision", "seq": 10**20, "verdict": "allow"}
        line, _ = seal_line(json.dumps(body, ensure_ascii=False),
                            bytes.fromhex(json.loads(lines[-2])["h"])
                            if len(lines) > 1 else b"\x00" * 32)
        lines.insert(len(lines) - 1, line)
    if mut == "junk_line":
        lines.insert(rng.randrange(len(lines) + 1),
                     rng.choice(["", "   ", "{not json", '"a string"']))
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
    tmp = tempfile.mkdtemp(prefix="vlcfuzzpfx-")
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
                repro = os.path.join(os.getcwd(), f"fuzz_prefix_repro_{i}.jsonl")
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
              "prefix-chain case")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
