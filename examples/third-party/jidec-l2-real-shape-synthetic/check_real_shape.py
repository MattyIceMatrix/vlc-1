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

    # v1.1 (2026-11-28): the operator's second signed set, built after
    # 1.4.9-draft. Every checkpoint carries refused_complete_since; six new
    # variants (partial first window, the field misplaced three ways, a
    # Markdown note bound but not read, and that note edited). The fourteen
    # v1 variants keep their names and expectations. Kept byte for byte in
    # trails-v1_1/; the operator's builder and verifier sit in
    # horizons-v1_1/ and are never run here.
    want11 = dict(WANT)
    want11.update({
        "partial_first": (2, None),          # refusals declared from entry 3
        "complete_since_later_window": (1, "VLC-L2-2"),
        "complete_since_out_of_range": (1, "VLC-L2-2"),
        "complete_since_below_from": (1, "VLC-L2-2"),
        "plain_note": (2, None),             # bound by its hash, not read (EXT-034)
        "plain_note_edited": (0, "VLC-L1-1"),
    })
    t11 = os.path.join(HERE, "trails-v1_1")
    with open(os.path.join(t11, "index.json")) as f:
        index11 = json.load(f)
    with open(os.path.join(t11, "operator_key.json")) as f:
        op11 = json.load(f)["operator_public_key"]
    t("v1.1: twenty variants, each with an expectation",
      sorted(want11) == sorted(i["variant"] for i in index11))
    for it in index11:
        v = it["variant"]
        p = os.path.join(t11, v, "export.jsonl")
        with open(p, "rb") as f:
            t(f"v1.1 {v}: export is byte for byte the operator's",
              hashlib.sha256(f.read()).hexdigest() == it["export_sha256"])
        rep = C.check(p, ADAPTER, expect_head=it["marker_sha256"], operator_key=op11)
        lv, at = want11[v]
        t(f"v1.1 {v}: structural L{lv} (got L{rep['structural_level']})",
          rep["structural_level"] == lv)
        if at:
            t(f"v1.1 {v}: fails at {at}", rep["requirements"][at]["status"] == "FAIL")
        if v != "refusal_list_short":
            t(f"v1.1 {v}: agrees with the operator's expectation", "L%d" % lv == it["expect"])
        if v == "partial_first":
            t("v1.1 partial_first: the boundary is stated, from entry 3",
              "refusals in scope from ordinal 3: 1..2 make no refusal claim"
              in rep["requirements"]["VLC-L2-5"]["note"])
        if v.startswith("complete_since_"):
            note = rep["requirements"]["VLC-L2-2"]["note"]
            t(f"v1.1 {v}: fails on the field itself, with no follow-on gap",
              "refusals complete since" in note and "gap in the declared span" not in note)

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

        # EXT-034: the live ledger binds plain-text records too (entry 399, a
        # Markdown note, schema v0-plain). Entry 20 of the honest trail sits in
        # the undeclared tail, so its record can be swapped and only entry 20
        # and the end marker re-chained, by the operator's own recipe (sorted,
        # compact JSON over n, schema, claim_sha256, created_at,
        # prev_entry_sha256; the marker over n, schema, prev_entry_sha256,
        # head). The recipe is checked first against the honest bytes.
        def canon(d):
            return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

        def sha(s):
            return hashlib.sha256(s.encode("utf-8")).hexdigest()

        ENTRY = ("n", "schema", "claim_sha256", "created_at", "prev_entry_sha256")
        MARK = ("n", "schema", "prev_entry_sha256", "head")
        base = [json.loads(x) for x in open(honest, encoding="utf-8").read().splitlines()]
        t("the operator's entry recipe reproduces every honest hash",
          all(sha(canon({k: o[k] for k in (MARK if o["schema"] == "jidec-head-v1" else ENTRY)}))
              == o["entry_sha256"] for o in base))

        def tail_variant(name, record, schema="v0-plain", claim=None):
            L = copy.deepcopy(base)
            e, m = L[-2], L[-1]
            e["schema"], e["record_canonical"] = schema, record
            e.pop("record_sig", None)
            e["claim_sha256"] = claim or sha(record)
            e["entry_sha256"] = sha(canon({k: e[k] for k in ENTRY}))
            m["head"] = m["prev_entry_sha256"] = e["entry_sha256"]
            m["entry_sha256"] = sha(canon({k: m[k] for k in MARK}))
            p = os.path.join(td, name + ".jsonl")
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(o, ensure_ascii=False, separators=(",", ":"))
                                  for o in L) + "\n")
            return p, m["entry_sha256"]

        def run_h(adapter, log, h):
            ap = os.path.join(td, "a.json")
            with open(ap, "w") as f:
                json.dump(adapter, f)
            return C.check(log, ap, expect_head=h, operator_key=op)

        md = "# souba-split-count-tool-v7\n\nA plain note, not JSON. SYNTHETIC.\n"
        mdp, mdh = tail_variant("markdown", md)
        rep = run_h(ad, mdp, mdh)
        t("a Markdown record, bound, bind_only: structural L2, tail unchanged",
          rep["structural_level"] == 2)

        a4 = copy.deepcopy(ad)
        del a4["record_binding"]["non_object"]
        rep = run_h(a4, mdp, mdh)
        t("the same trail without non_object reproduces the operator's report (L0, not JSON)",
          rep["structural_level"] == 0
          and "not parseable as JSON" in rep["requirements"]["VLC-L1-1"]["note"])

        L = [json.loads(x) for x in open(mdp, encoding="utf-8").read().splitlines()]
        L[-2]["record_canonical"] = md.replace("plain note", "plain n0te")
        ed = os.path.join(td, "markdown-edited.jsonl")
        with open(ed, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(o, ensure_ascii=False) for o in L) + "\n")
        rep = run_h(ad, ed, mdh)
        t("a Markdown record edited, digest kept: the byte check still runs, L0",
          rep["structural_level"] == 0 and "record binding" in rep["requirements"]["VLC-L1-1"]["note"])

        arp, arh = tail_variant("json-array", '["not", "an", "object"]')
        t("a JSON record that is not an object, bind_only: L2",
          run_h(ad, arp, arh)["structural_level"] == 2)

        dup, duph = tail_variant("duplicate-names", '{"schema":"x","schema":"y"}')
        rep = run_h(ad, dup, duph)
        t("ambiguous JSON (duplicate names) is still refused under bind_only",
          rep["structural_level"] == 0 and "duplicate member name" in rep["requirements"]["VLC-L1-1"]["note"])

        cp, cph = tail_variant("unlifted-as-declaration", md, schema="nenrin-head-checkpoint-v2")
        t("an unlifted line classed as the declaration class does not grade L2",
          run_h(ad, cp, cph)["structural_level"] < 2)

        # 1.4.9-draft: refused_complete_since, as the operator
        # named it on PR #12 -- the n from which every refusal in a window is
        # counted. Built by editing the checkpoints' records and re-chaining
        # the whole trail with the operator's recipe; each checkpoint's sealed
        # head (entry and marker hash) is recomputed from the rebuilt prefix.
        # Record bytes change, so the checkpoints' signatures no longer hold:
        # these controls grade with the signatures block removed. The hop is
        # covered by the fourteen trails above; the operator's next synthetic
        # set carries this field signed and becomes the frozen control.
        def rebuild(name, edit):
            L = copy.deepcopy(base)
            hashes = {}
            for o in L:
                if o["schema"] == "jidec-head-v1":
                    o["head"] = o["prev_entry_sha256"] = prev
                    o["entry_sha256"] = sha(canon({k: o[k] for k in MARK}))
                    continue
                o["prev_entry_sha256"] = prev if o["n"] > 1 else "0" * 64
                rec = json.loads(o["record_canonical"])
                if rec.get("schema") == "nenrin-head-checkpoint-v2":
                    h = rec["ledger_head"]
                    h["entry_sha256"] = hashes[h["n"]]
                    h["marker_sha256"] = sha(canon({"n": h["n"], "schema": "jidec-head-v1",
                                                    "prev_entry_sha256": hashes[h["n"]],
                                                    "head": hashes[h["n"]]}))
                    edit(rec)
                    o.pop("record_sig", None)
                o["record_canonical"] = json.dumps(rec, separators=(",", ":"), ensure_ascii=False)
                o["claim_sha256"] = sha(o["record_canonical"])
                o["entry_sha256"] = sha(canon({k: o[k] for k in ENTRY}))
                hashes[o["n"]] = prev = o["entry_sha256"]
            p = os.path.join(td, name + ".jsonl")
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(o, ensure_ascii=False, separators=(",", ":"))
                                  for o in L) + "\n")
            return p, L[-1]["entry_sha256"]

        same, sameh = rebuild("rebuild-identity", lambda rec: None)
        t("the rebuild with no edit reproduces every honest entry hash",
          [json.loads(x)["entry_sha256"] for x in open(same, encoding="utf-8")]
          == [o["entry_sha256"] for o in base])

        ns = copy.deepcopy(ad)
        del ns["signatures"]

        def since(values):
            def edit(rec):
                frm = rec["production_count"]["from"]
                if frm in values:
                    rec["refused_complete_since"] = values[frm]
            return edit

        def grade(name, values):
            p, h = rebuild(name, since(values))
            return run_h(ns, p, h)

        rep = grade("since-first-partial", {1: 4, 7: 7, 13: 13})
        t("first window counting refusals from 4: structural L2, boundary stated",
          rep["structural_level"] == 2
          and "refusals in scope from ordinal 4: 1..3 make no refusal claim"
          in rep["requirements"]["VLC-L2-5"]["note"])
        rep = grade("since-every-from", {1: 1, 7: 7, 13: 13})
        t("every window counting from its own start: L2, no boundary note",
          rep["structural_level"] == 2 and "make no refusal claim" not in rep["requirements"]["VLC-L2-5"]["note"])
        t("first window counting from to + 1 (no refusals counted yet): L2",
          grade("since-first-empty", {1: 7})["structural_level"] == 2)
        t("absent field reads as the window's start (the 1.4.8-draft meaning): L2",
          grade("since-absent", {})["structural_level"] == 2)
        for nm, vals, why in (("since-past-end", {1: 8}, "past to + 1"),
                              ("since-before-start", {1: 0}, "before from"),
                              ("since-later-window", {1: 1, 7: 9}, "a later window not at its from"),
                              ("since-not-integer", {1: "4"}, "not an integer")):
            rep = grade(nm, vals)
            t(f"refused_complete_since {why}: fails VLC-L2-2",
              rep["structural_level"] == 1 and rep["requirements"]["VLC-L2-2"]["status"] == "FAIL")
        bad = copy.deepcopy(ns)
        del bad["loss"]["refused_field"]
        ap = os.path.join(td, "bad-adapter.json")
        with open(ap, "w") as f:
            json.dump(bad, f)
        try:
            C.check(same, ap, expect_head=sameh)
            refused = False
        except C.AdapterError as e:
            refused = "qualifies refused_field" in str(e)
        t("the field without refused_field in scope is an adapter error", refused)

    print(f"all {n_ok} assertions hold: the JIDEC real export shape grades natively "
          f"(record binding, signature hop, head cross-check)")


if __name__ == "__main__":
    main()
