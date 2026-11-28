#!/usr/bin/env python3
"""SYNTHETIC: the JIDEC ledger's real export shape, graded natively (1.4.7-draft).

The fourteen trails under trails/ were built by The HORIZONs Co., Ltd. (the
JIDEC ledger's operator) with their own builder, and sent for vlc-1 PR #12 on
2026-11-28 under the MIT licence. Everything in them is synthetic: test keys
from fixed seeds, no output of the JIDEC ledger. They are kept here byte for
byte; trails/index.json carries each export's sha256, checked below first.

This script is ours. It imports nothing from horizons/ (their builder,
verifier and wrapper are kept for reference and are not run here). It grades
each trail with conformance.py and adapter-l2-record-bound.json, using only
the checker's native 1.4.7-draft features:

  * record_binding  -- sha256 of record_canonical, as delivered, must equal
                       claim_sha256; then the record is read under @record
  * signatures      -- key statement signed by the pinned operator key,
                       checkpoint signed by a ledger key named before it
  * loss.head_n_field / head_hash_field -- the head a checkpoint seals is
                       entry `to` of the window it declares

and asserts each verdict, and the requirement it fails at, against the
operator's own expectation and their independent verifier's table on PR #12.

One variant is asserted DIFFERENT from the operator's expectation, on purpose:
refusal_list_short (a refusal list one line short) grades L2 here, because the
list is a separate file and its sha256 is all the export carries. The
operator's own table says the same: L1 only with the lists supplied.

Run:  python3 examples/third-party/jidec-l2-real-shape-synthetic/check_real_shape.py
Blast radius: reads this directory; writes only to a private temporary directory.
"""
import copy
import hashlib
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
import conformance as C  # noqa: E402

ADAPTER = os.path.join(HERE, "adapter-l2-record-bound.json")
TRAILS = os.path.join(HERE, "trails")

# variant -> (structural level, requirement it fails at, or None)
WANT = {
    "honest": (2, None),
    "declared_loss": (2, None),
    "undercount": (1, "VLC-L2-2"),
    "hidden_drop": (1, "VLC-L2-2"),
    "tail_gap": (1, "VLC-L2-2"),
    "unbound_edit": (0, "VLC-L1-1"),
    "sig_stripped": (1, "VLC-L2-3"),
    "wrong_key": (1, "VLC-L2-3"),
    "statement_not_operator": (1, "VLC-L2-3"),
    "head_mismatch": (1, "VLC-L2-2"),
    "head_hash_mismatch": (1, "VLC-L2-2"),
    "window_overlap": (1, "VLC-L2-2"),
    "window_gap": (1, "VLC-L2-2"),
    "refusal_list_short": (2, None),      # by design: the list is outside the export
}


def main():
    n_ok = 0

    def t(name, cond):
        nonlocal n_ok
        if not cond:
            print("FAIL " + name)
            sys.exit(1)
        n_ok += 1

    with open(os.path.join(TRAILS, "index.json")) as f:
        index = json.load(f)
    with open(os.path.join(TRAILS, "operator_key.json")) as f:
        op = json.load(f)["operator_public_key"]
    t("fourteen variants, each with an expectation", sorted(WANT) == sorted(i["variant"] for i in index))

    for it in index:
        v = it["variant"]
        p = os.path.join(TRAILS, v, "export.jsonl")
        with open(p, "rb") as f:
            t(f"{v}: export is byte for byte the operator's",
              hashlib.sha256(f.read()).hexdigest() == it["export_sha256"])
        rep = C.check(p, ADAPTER, expect_head=it["marker_sha256"], operator_key=op)
        lv, at = WANT[v]
        t(f"{v}: structural L{lv} (got L{rep['structural_level']})", rep["structural_level"] == lv)
        if at:
            t(f"{v}: fails at {at}", rep["requirements"][at]["status"] == "FAIL")
        if v != "refusal_list_short":
            t(f"{v}: agrees with the operator's expectation", "L%d" % lv == it["expect"])

    honest = os.path.join(TRAILS, "honest", "export.jsonl")
    head = index[0]["marker_sha256"]

    # without the pinned operator key, the signatures cannot be the producer's
    rep = C.check(honest, ADAPTER, expect_head=head)
    t("no pinned operator key: VLC-L2-3 fails and says why",
      rep["structural_level"] == 1 and "no operator key" in rep["requirements"]["VLC-L2-3"]["note"])

    # a different pinned key: the statement names another operator
    rep = C.check(honest, ADAPTER, expect_head=head, operator_key="11" * 32)
    t("a different pinned key: the key statement is refused", rep["structural_level"] == 1)

    with open(ADAPTER) as f:
        ad = json.load(f)
    with tempfile.TemporaryDirectory() as td:
        def run(adapter, log=honest, key=op):
            ap = os.path.join(td, "a.json")
            with open(ap, "w") as f:
                json.dump(adapter, f)
            return C.check(log, ap, expect_head=head, operator_key=key)

        # coverage guard: @record.* is anchored only while the digest is hashed
        a2 = copy.deepcopy(ad)
        a2["integrity"]["hash_fields"].remove("claim_sha256")
        rep = run(a2)
        t("digest not hashed: @record fields are unanchored, L1 refused",
          rep["structural_level"] == 0 and "unanchored" in rep["requirements"]["VLC-L1-1"]["note"])

        # without record_binding the @record paths are unanchored too
        a3 = copy.deepcopy(ad)
        del a3["record_binding"]
        del a3["signatures"]
        rep = run(a3)
        t("no record_binding: @record fields are unanchored", rep["structural_level"] == 0)

        # a line that carries an "@record" of its own is refused, not read
        lines = open(honest, encoding="utf-8").read().splitlines()
        m = json.loads(lines[-1])
        m["@record"] = {"schema": "nenrin-head-checkpoint-v2"}
        lines[-1] = json.dumps(m)
        sm = os.path.join(td, "smuggled.jsonl")
        with open(sm, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        rep = run(ad, log=sm)
        t("a smuggled @record member is refused",
          rep["structural_level"] == 0 and "reserved" in rep["requirements"]["VLC-L1-1"]["note"])

        # bytes re-canonicalized (key order changed), digest kept: binding fails
        lines = open(honest, encoding="utf-8").read().splitlines()
        o = json.loads(lines[6])
        o["record_canonical"] = json.dumps(json.loads(o["record_canonical"]), sort_keys=True,
                                           separators=(",", ":"))
        lines[6] = json.dumps(o)
        rc = os.path.join(td, "recanon.jsonl")
        with open(rc, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        rep = run(ad, log=rc)
        t("record bytes re-canonicalized: the binding is by the bytes as delivered",
          rep["structural_level"] == 0)

    print(f"all {n_ok} assertions hold: the JIDEC real export shape grades natively "
          f"(record binding, signature hop, head cross-check)")


if __name__ == "__main__":
    main()
