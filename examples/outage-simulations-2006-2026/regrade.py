#!/usr/bin/env python3
"""Re-verify the outage-simulation findings yourself. Standard library only.

    python3 examples/outage-simulations-2021-2026/regrade.py

For each of the 14 simulated incidents this grades, with the reference
checker in this repository:
  - the legacy plain log           -> expected L0
  - its forged variant             -> expected L0, indistinguishable
  - the instrumented export        -> expected structural L4 / attested L4
  - the attacked trail             -> expected to collapse below L4
using the committed trails and the public adapter. Exit code 0 means every
expectation held on your machine."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, ROOT)
from conformance import check

ADAPTER = os.path.join(ROOT, "adapters", "octa-gateway-export.json")
LEGACY_ADAPTER = os.path.join(HERE, "legacy-adapter.json")
bad = 0
for s in json.load(open(os.path.join(HERE, "scenarios.json"))):
    sid = s["id"]
    l = check(os.path.join(HERE, "trails", "legacy", sid + ".jsonl"), LEGACY_ADAPTER)
    f = check(os.path.join(HERE, "trails", "legacy", sid + "-forged.jsonl"), LEGACY_ADAPTER)
    meta = json.load(open(os.path.join(HERE, "trails", "instrumented", sid, "meta.json")))
    m = meta["marker"]
    o = check(os.path.join(HERE, "trails", "instrumented", sid, "audit.jsonl"), ADAPTER,
              expect_root=m["genesis"], expect_head=m["head"])
    a = check(os.path.join(HERE, "trails", "instrumented", sid, "attacked.jsonl"), ADAPTER,
              expect_root=m["genesis"], expect_head=m["head"])
    ok = (l["structural_level"] == 0 and f["structural_level"] == l["structural_level"]
          and o["structural_level"] == 4 and o["attested_level"] == 4
          and a["structural_level"] < o["structural_level"])
    print(f"{'ok ' if ok else 'BAD'} {sid}: legacy L{l['structural_level']} "
          f"(forged L{f['structural_level']}, indistinguishable) | instrumented "
          f"structural L{o['structural_level']} / attested L{o['attested_level']} | "
          f"attack -> L{a['structural_level']}")
    bad += 0 if ok else 1
print(("all expectations held" if not bad else f"{bad} scenario(s) diverged"))
sys.exit(1 if bad else 0)
