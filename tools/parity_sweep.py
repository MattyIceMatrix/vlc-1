#!/usr/bin/env python3
"""Parity sweep: every served (journal x adapter) pair, plus every applicable
Annex A mutation, graded by BOTH checkers and compared per requirement.

    ./tools/parity_sweep.py

Where the fixed matrix (worker/parity.test.mjs) freezes 18 known assertions
and the fuzzer (fuzz_differential.py) generates random generic-adapter
journals, this sweep covers the REAL journals in the repository under every
adapter the live endpoint serves -- including the reference checker's own
mutation machinery (conformance.mutate), so each mechanism's tamper-detection
paths are compared too, not just the happy path.

Compared requirements: VLC-L1-1, VLC-L1-3, VLC-L2-5 (absent in the reference
report = not demonstrated = False, as in the fixed matrix). A live grade of
NOT GRADABLE LIVE counts as disclosed, never as agreement or disagreement.

Exit 0: full agreement. Exit 1: any disagreement (each printed).

Blast radius: reads the repo; writes only a self-created temp dir, cleaned up.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from conformance import check as py_check, mutate, UsageError, LogError, AdapterError  # noqa: E402

HARNESS = os.path.join(REPO, "worker", "fuzz_harness.mjs")
CHECKS = ("VLC-L1-1", "VLC-L1-3", "VLC-L2-5")

# exactly the set the live endpoint serves (worker/index.mjs ADAPTERS)
SERVED = ["generic-appjsonl", "generic-appjsonl-policy", "observer", "observer-legacy",
          "halo-runtime-record"]

MUTATIONS = ["flip-byte", "drop-interior", "truncate-tail"]

JOURNAL_DIRS = ["examples", os.path.join("examples", "reference-impl"),
                os.path.join("examples", "third-party", "halo-record-synthetic")]


def journals():
    for d in JOURNAL_DIRS:
        p = os.path.join(REPO, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if f.endswith(".jsonl"):
                yield os.path.join(p, f)


def py_verdict(path, adapter_path):
    rep = py_check(path, adapter_path)
    return {c: rep["requirements"].get(c, {}).get("status") == "PASS" for c in CHECKS}


def js_verdict(path, adapter_path):
    with open(path, "rb") as f:
        r = subprocess.run(["node", HARNESS, adapter_path], stdin=f, capture_output=True, timeout=60)
    out = json.loads(r.stdout.decode())
    if "harness_error" in out:
        return None
    if out.get("verdict") == "NOT GRADABLE LIVE":
        return "disclosed"
    got = {x["check"]: bool(x["ok"]) for x in out.get("results", [])}
    return {c: got.get(c, False) for c in CHECKS}


def main():
    tmp = tempfile.mkdtemp(prefix="vlc-sweep-")
    pairs = disagreements = disclosed = 0
    try:
        for jpath in journals():
            with open(jpath, encoding="utf-8", errors="replace") as f:
                base_lines = [l.rstrip("\n") for l in f if l.strip()]
            for name in SERVED:
                apath = os.path.join(REPO, "adapters", name + ".json")
                ad = json.load(open(apath))
                for mut in [None] + MUTATIONS:
                    if mut is None:
                        case_path = jpath
                    else:
                        try:
                            lines = mutate(base_lines, mut, ad)
                        except (UsageError, LogError, AdapterError):
                            continue
                        case_path = os.path.join(tmp, "case.jsonl")
                        with open(case_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(lines) + "\n")
                    pairs += 1
                    py = py_verdict(case_path, apath)
                    js = js_verdict(case_path, apath)
                    if js == "disclosed":
                        disclosed += 1
                        continue
                    if js is None or py != js:
                        disagreements += 1
                        print(f"DISAGREE {os.path.relpath(jpath, REPO)} x {name}"
                              f"{' x ' + mut if mut else ''}: python={py} js={js}")
        print(f"\n{pairs} pairs swept ({disclosed} disclosed-not-gradable)")
        if disagreements:
            print(f"SWEEP FAIL: {disagreements} disagreement(s)")
            return 1
        print("SWEEP PASS: live worker core agrees with the reference on every served pair")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
