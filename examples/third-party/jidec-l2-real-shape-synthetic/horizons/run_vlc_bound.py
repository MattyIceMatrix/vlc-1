#!/usr/bin/env python3
"""run_vlc_bound.py: grade the SYNTHETIC trails of jidec_l2_synth.py with the VLC-1 reference checker
(conformance.py of a vlc-1 checkout, not modified on disk), three ways:

  as is      the checker as it stands, with the template's own adapter file (adapter-l2-checkpoint.json)
  bound      plus two behaviours the mapping to the real JIDEC shape needs, applied in this process only:
             (1) record binding: record_canonical hashes to claim_sha256, which the entry hash covers, so
                 fields read from the parsed record count as anchored. This run verifies the binding for
                 every entry first and stops at the first that fails; the parsed record is put under
                 "@record" and its schema under "@cls" (the marker keeps its own schema)
             (2) the end marker is not an event: it is left out of the windowed ordinal set, as it is
                 already left out of the delivered set. The live marker carries the n of the head it binds
  bound-1    (1) only, to show what (2) changes

  python3 -I run_vlc_bound.py <vlc-1 checkout> <folder written by jidec_l2_synth.py --out>

It prints one row per variant and, last, VLC_BOUND_RUN_OK <sha256 of the rows>.
番人(個人) 2026-11-28. SYNTHETIC trails only.
"""
import copy
import hashlib
import json
import os
import sys
import tempfile

ADAPTER = {
    "name": "jidec-ledger-chained-l2-v2-proposal",
    "producer": "SYNTHETIC trails in the live JIDEC export shape with nenrin-head-checkpoint-v2 (proposal, not served)",
    "record_class_field": "@cls",
    "marker_classes": ["jidec-head-v1"],
    "non_event_classes": ["nenrin-head-checkpoint-v2"],
    "integrity": {
        "mechanism": "sha256-canonical-fields",
        "hash_field": "entry_sha256",
        "prev_field": "prev_entry_sha256",
        "hash_fields": ["n", "schema", "claim_sha256", "created_at", "prev_entry_sha256", "head"],
        "root": {"kind": "constant", "value": "0" * 64},
        "primitive": "SHA-256",
        "documented": True,
        "primitive_documented": True,
        "end_marker": {"class": "jidec-head-v1", "head_field": "head", "self_bound": True},
    },
    "loss": {
        "mode": "windowed_declaration",
        "declaration_class": "nenrin-head-checkpoint-v2",
        "interval_fields": ["@record.production_count.from", "@record.production_count.to"],
        "received_field": "@record.production_count.received",
        "refused_field": "@record.production_count.refused",
        "lost_field": "@record.production_count.lost",
        "event_ordinal_field": "n",
        "ordinal_start": 1,
        "overflow_behaviour": "drop_counted",
    },
    "coverage": {"mode": "none"},
    "policy": {"mode": "none"},
    "independence": {"mode": "self_reported", "audited_process_can_write_records": True,
                     "boundary_statement": "SYNTHETIC"},
    "sources": ["SYNTHETIC: jidec_l2_synth.py"],
}

TEMPLATE = "examples/third-party/jidec-l2-checkpoint-shape-synthetic/adapter-l2-checkpoint.json"


def prepass(src, dst):
    """Verify record binding for every entry and add @record / @cls. Returns None or the first failure."""
    out = []
    for line in open(src, encoding="utf-8"):
        if not line.strip():
            continue
        o = json.loads(line)
        if "record_canonical" in o:
            rc = o["record_canonical"]
            if hashlib.sha256(rc.encode("utf-8")).hexdigest() != o.get("claim_sha256"):
                return "entry %s: record_canonical does not hash to claim_sha256" % o.get("n")
            rec = json.loads(rc)
            o["@record"], o["@cls"] = rec, rec.get("schema")
        else:
            o["@cls"] = o.get("schema")
        out.append(json.dumps(o, ensure_ascii=False, separators=(",", ":")))
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return None


def main():
    vlc, synth = sys.argv[1], sys.argv[2]
    sys.path.insert(0, vlc)
    import conformance as C
    orig_cov, orig_win = C.check_canonical_fields_adapter, C.check_l2_windowed
    head = subprocess_free_head(vlc)
    index = json.load(open(os.path.join(synth, "index.json")))
    rows = []
    with tempfile.TemporaryDirectory() as td:
        pa, pb = os.path.join(vlc, TEMPLATE), os.path.join(td, "bound.json")
        json.dump(ADAPTER, open(pb, "w"))
        for it in index:
            v = it["variant"]
            src = os.path.join(synth, v, "export.jsonl")
            row = {"variant": v}
            C.check_canonical_fields_adapter, C.check_l2_windowed = orig_cov, orig_win
            rep = C.check(src, pa, expect_head=it["marker_sha256"])
            row["as_is"] = summarize(rep)
            bound = os.path.join(td, v + ".bound.jsonl")
            why = prepass(src, bound)
            if why:
                row["bound"] = row["bound-1"] = "L0 (record binding: %s)" % why
                rows.append(row)
                continue

            def cov(recs, ad):
                ad2 = copy.deepcopy(ad)
                ad2["integrity"]["hash_fields"] = ad2["integrity"]["hash_fields"] + ["@record", "@cls"]
                return orig_cov(recs, ad2)

            def win(recs, ad, res, lo, delivered):
                markers = set(ad.get("marker_classes", []))
                return orig_win([r for r in recs if r.cls not in markers], ad, res, lo, delivered)

            C.check_canonical_fields_adapter, C.check_l2_windowed = cov, orig_win
            row["bound-1"] = summarize(C.check(bound, pb, expect_head=it["marker_sha256"]))
            C.check_canonical_fields_adapter, C.check_l2_windowed = cov, win
            row["bound"] = summarize(C.check(bound, pb, expect_head=it["marker_sha256"]))
            rows.append(row)
    C.check_canonical_fields_adapter, C.check_l2_windowed = orig_cov, orig_win
    text = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)
    sys.stdout.write("vlc-1 checkout at %s\n" % head)
    sys.stdout.write(text)
    sys.stdout.write("VLC_BOUND_RUN_OK %s\n" % hashlib.sha256(text.encode()).hexdigest())
    return 0


def summarize(rep):
    lvl = rep.get("structural_level")
    fails = sorted(k for k, v in rep["requirements"].items() if v["status"] == "FAIL" and (k.startswith("VLC-L1") or k.startswith("VLC-L2")))
    first = ""
    for k in fails:
        first = "%s %s" % (k, rep["requirements"][k].get("note", "")[:110])
        break
    tail = rep["requirements"].get("VLC-L2-5", {}).get("note", "")
    t = ""
    if lvl is not None and lvl >= 2 and "tail" in tail:
        t = " (tail %s)" % tail.split("tail (")[-1].split(")")[0]
    return "L%s%s%s" % (lvl, t, (" | " + first) if first else "")


def subprocess_free_head(vlc):
    try:
        ref = open(os.path.join(vlc, ".git", "HEAD")).read().strip()
        if ref.startswith("ref: "):
            p = os.path.join(vlc, ".git", ref[5:])
            if os.path.exists(p):
                return open(p).read().strip()[:12]
            for line in open(os.path.join(vlc, ".git", "packed-refs")):
                if line.strip().endswith(ref[5:]):
                    return line.split()[0][:12]
        return ref[:12]
    except OSError:
        return "unknown"


if __name__ == "__main__":
    sys.exit(main())
